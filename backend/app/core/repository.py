"""Base repository class for database operations."""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository class with common CRUD operations."""
    
    def __init__(self, model: Type[ModelType]):
        """Initialize repository with model class."""
        self.model = model
    
    async def get(
        self,
        db: AsyncSession,
        id: Union[UUID, str, int],
        load_relationships: Optional[List[str]] = None,
    ) -> Optional[ModelType]:
        """Get a single record by ID."""
        query = select(self.model).where(self.model.id == id)
        
        # Load relationships if specified
        if load_relationships:
            for relationship in load_relationships:
                query = query.options(selectinload(getattr(self.model, relationship)))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        load_relationships: Optional[List[str]] = None,
    ) -> List[ModelType]:
        """Get multiple records with pagination and filtering."""
        query = select(self.model)
        
        # Apply filters
        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(self.model, field):
                    if isinstance(value, list):
                        conditions.append(getattr(self.model, field).in_(value))
                    else:
                        conditions.append(getattr(self.model, field) == value)
            
            if conditions:
                query = query.where(and_(*conditions))
        
        # Apply ordering
        if order_by:
            if order_by.startswith("-"):
                # Descending order
                field = order_by[1:]
                if hasattr(self.model, field):
                    query = query.order_by(getattr(self.model, field).desc())
            else:
                # Ascending order
                if hasattr(self.model, order_by):
                    query = query.order_by(getattr(self.model, order_by))
        
        # Load relationships if specified
        if load_relationships:
            for relationship in load_relationships:
                if hasattr(self.model, relationship):
                    query = query.options(selectinload(getattr(self.model, relationship)))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: Union[CreateSchemaType, Dict[str, Any]],
        commit: bool = True,
    ) -> ModelType:
        """Create a new record."""
        if isinstance(obj_in, dict):
            create_data = obj_in
        else:
            create_data = obj_in.model_dump(exclude_unset=True)
        
        db_obj = self.model(**create_data)
        db.add(db_obj)
        
        if commit:
            await db.commit()
            await db.refresh(db_obj)
        
        return db_obj
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
        commit: bool = True,
    ) -> ModelType:
        """Update an existing record."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        if commit:
            await db.commit()
            await db.refresh(db_obj)
        
        return db_obj
    
    async def delete(
        self,
        db: AsyncSession,
        *,
        id: Union[UUID, str, int],
        commit: bool = True,
    ) -> bool:
        """Delete a record by ID."""
        query = delete(self.model).where(self.model.id == id)
        result = await db.execute(query)
        
        if commit:
            await db.commit()
        
        return result.rowcount > 0
    
    async def count(
        self,
        db: AsyncSession,
        *,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Count records with optional filtering."""
        query = select(func.count(self.model.id))
        
        # Apply filters
        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(self.model, field):
                    if isinstance(value, list):
                        conditions.append(getattr(self.model, field).in_(value))
                    else:
                        conditions.append(getattr(self.model, field) == value)
            
            if conditions:
                query = query.where(and_(*conditions))
        
        result = await db.execute(query)
        return result.scalar()
    
    async def exists(
        self,
        db: AsyncSession,
        *,
        filters: Dict[str, Any],
    ) -> bool:
        """Check if record exists with given filters."""
        conditions = []
        for field, value in filters.items():
            if hasattr(self.model, field):
                conditions.append(getattr(self.model, field) == value)
        
        if not conditions:
            return False
        
        query = select(self.model.id).where(and_(*conditions)).limit(1)
        result = await db.execute(query)
        return result.scalar() is not None
    
    async def get_by_field(
        self,
        db: AsyncSession,
        *,
        field: str,
        value: Any,
        load_relationships: Optional[List[str]] = None,
    ) -> Optional[ModelType]:
        """Get a single record by field value."""
        if not hasattr(self.model, field):
            return None
        
        query = select(self.model).where(getattr(self.model, field) == value)
        
        # Load relationships if specified
        if load_relationships:
            for relationship in load_relationships:
                if hasattr(self.model, relationship):
                    query = query.options(selectinload(getattr(self.model, relationship)))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def search(
        self,
        db: AsyncSession,
        *,
        search_term: str,
        search_fields: List[str],
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ModelType]:
        """Search records by text in specified fields."""
        # Build search conditions
        search_conditions = []
        for field in search_fields:
            if hasattr(self.model, field):
                field_attr = getattr(self.model, field)
                search_conditions.append(field_attr.ilike(f"%{search_term}%"))
        
        if not search_conditions:
            return []
        
        query = select(self.model).where(or_(*search_conditions))
        
        # Apply additional filters
        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(self.model, field):
                    if isinstance(value, list):
                        conditions.append(getattr(self.model, field).in_(value))
                    else:
                        conditions.append(getattr(self.model, field) == value)
            
            if conditions:
                query = query.where(and_(*conditions))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def bulk_create(
        self,
        db: AsyncSession,
        *,
        objs_in: List[Union[CreateSchemaType, Dict[str, Any]]],
        commit: bool = True,
    ) -> List[ModelType]:
        """Create multiple records in bulk."""
        db_objs = []
        
        for obj_in in objs_in:
            if isinstance(obj_in, dict):
                create_data = obj_in
            else:
                create_data = obj_in.model_dump(exclude_unset=True)
            
            db_obj = self.model(**create_data)
            db_objs.append(db_obj)
        
        db.add_all(db_objs)
        
        if commit:
            await db.commit()
            for db_obj in db_objs:
                await db.refresh(db_obj)
        
        return db_objs
    
    async def bulk_update(
        self,
        db: AsyncSession,
        *,
        updates: List[Dict[str, Any]],
        commit: bool = True,
    ) -> int:
        """Update multiple records in bulk."""
        if not updates:
            return 0
        
        # Each update dict should contain 'id' and the fields to update
        updated_count = 0
        
        for update_data in updates:
            if "id" not in update_data:
                continue
            
            record_id = update_data.pop("id")
            
            if update_data:  # Only update if there are fields to update
                query = (
                    update(self.model)
                    .where(self.model.id == record_id)
                    .values(**update_data)
                )
                result = await db.execute(query)
                updated_count += result.rowcount
        
        if commit:
            await db.commit()
        
        return updated_count