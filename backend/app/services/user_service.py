"""User service for user management operations."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import auth_manager
from app.models.user import User, UserRole, ParentStudentRelation
from app.schemas.user import UserCreate, UserUpdate, UserResponse


class UserService:
    """Service class for user operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if email already exists
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError("邮箱已被注册")
        
        # Validate password strength
        is_valid, message = auth_manager.validate_password_strength(user_data.password)
        if not is_valid:
            raise ValueError(message)
        
        # Hash password
        password_hash = auth_manager.get_password_hash(user_data.password)
        
        # Create user
        user = User(
            email=user_data.email,
            password_hash=password_hash,
            name=user_data.name,
            role=user_data.role,
            school=user_data.school,
            grade=user_data.grade,
            is_active=True,
            is_verified=False
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.get_user_by_email(email)
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not auth_manager.verify_password(password, user.password_hash):
            return None
        
        # Update last login time
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        return user
    
    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> Optional[User]:
        """Update user information."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        # Update fields
        update_data = user_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def change_password(
        self,
        user_id: UUID,
        old_password: str,
        new_password: str
    ) -> bool:
        """Change user password."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Verify old password
        if not auth_manager.verify_password(old_password, user.password_hash):
            return False
        
        # Validate new password strength
        is_valid, message = auth_manager.validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(message)
        
        # Update password
        user.password_hash = auth_manager.get_password_hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        return True
    
    async def reset_password(self, user_id: UUID, new_password: str) -> bool:
        """Reset user password (for password reset flow)."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Validate new password strength
        is_valid, message = auth_manager.validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(message)
        
        # Update password
        user.password_hash = auth_manager.get_password_hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        return True
    
    async def deactivate_user(self, user_id: UUID) -> bool:
        """Deactivate user account."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        return True
    
    async def activate_user(self, user_id: UUID) -> bool:
        """Activate user account."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = True
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        return True
    
    async def verify_user_email(self, user_id: UUID) -> bool:
        """Verify user email."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_verified = True
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        return True
    
    async def get_users_by_role(self, role: UserRole) -> List[User]:
        """Get all users by role."""
        result = await self.db.execute(
            select(User).where(
                and_(User.role == role, User.is_active == True)
            )
        )
        return list(result.scalars().all())
    
    async def link_parent_student(
        self,
        parent_id: UUID,
        student_id: UUID,
        relation_type: str = "parent"
    ) -> bool:
        """Link parent and student."""
        # Verify parent and student exist and have correct roles
        parent = await self.get_user_by_id(parent_id)
        student = await self.get_user_by_id(student_id)
        
        if not parent or not student:
            return False
        
        if parent.role != UserRole.PARENT or student.role != UserRole.STUDENT:
            return False
        
        # Check if relation already exists
        existing_relation = await self.db.execute(
            select(ParentStudentRelation).where(
                and_(
                    ParentStudentRelation.parent_id == parent_id,
                    ParentStudentRelation.student_id == student_id
                )
            )
        )
        
        if existing_relation.scalar_one_or_none():
            return False  # Relation already exists
        
        # Create relation
        relation = ParentStudentRelation(
            parent_id=parent_id,
            student_id=student_id,
            relation_type=relation_type
        )
        
        self.db.add(relation)
        await self.db.commit()
        
        return True
    
    async def unlink_parent_student(self, parent_id: UUID, student_id: UUID) -> bool:
        """Unlink parent and student."""
        result = await self.db.execute(
            select(ParentStudentRelation).where(
                and_(
                    ParentStudentRelation.parent_id == parent_id,
                    ParentStudentRelation.student_id == student_id
                )
            )
        )
        
        relation = result.scalar_one_or_none()
        if not relation:
            return False
        
        await self.db.delete(relation)
        await self.db.commit()
        
        return True
    
    async def get_parent_children(self, parent_id: UUID) -> List[User]:
        """Get all children of a parent."""
        result = await self.db.execute(
            select(User)
            .join(ParentStudentRelation, User.id == ParentStudentRelation.student_id)
            .where(ParentStudentRelation.parent_id == parent_id)
            .options(selectinload(User.class_memberships))
        )
        return list(result.scalars().all())
    
    async def get_student_parents(self, student_id: UUID) -> List[User]:
        """Get all parents of a student."""
        result = await self.db.execute(
            select(User)
            .join(ParentStudentRelation, User.id == ParentStudentRelation.parent_id)
            .where(ParentStudentRelation.student_id == student_id)
        )
        return list(result.scalars().all())
    
    async def is_parent_of_student(self, parent_id: UUID, student_id: UUID) -> bool:
        """Check if user is parent of student."""
        result = await self.db.execute(
            select(ParentStudentRelation).where(
                and_(
                    ParentStudentRelation.parent_id == parent_id,
                    ParentStudentRelation.student_id == student_id
                )
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def is_teacher_of_student(self, teacher_id: UUID, student_id: UUID) -> bool:
        """Check if teacher teaches student (through classes)."""
        from app.models.class_model import Class, ClassStudent
        
        result = await self.db.execute(
            select(ClassStudent)
            .join(Class, ClassStudent.class_id == Class.id)
            .where(
                and_(
                    Class.teacher_id == teacher_id,
                    ClassStudent.student_id == student_id,
                    ClassStudent.is_active == True
                )
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def get_teacher_students(self, teacher_id: UUID) -> List[User]:
        """Get all students taught by a teacher."""
        from app.models.class_model import Class, ClassStudent
        
        result = await self.db.execute(
            select(User)
            .join(ClassStudent, User.id == ClassStudent.student_id)
            .join(Class, ClassStudent.class_id == Class.id)
            .where(
                and_(
                    Class.teacher_id == teacher_id,
                    ClassStudent.is_active == True,
                    User.is_active == True
                )
            )
            .distinct()
        )
        return list(result.scalars().all())
    
    async def get_student_teachers(self, student_id: UUID) -> List[User]:
        """Get all teachers of a student."""
        from app.models.class_model import Class, ClassStudent
        
        result = await self.db.execute(
            select(User)
            .join(Class, User.id == Class.teacher_id)
            .join(ClassStudent, Class.id == ClassStudent.class_id)
            .where(
                and_(
                    ClassStudent.student_id == student_id,
                    ClassStudent.is_active == True,
                    User.is_active == True
                )
            )
            .distinct()
        )
        return list(result.scalars().all())
    
    async def get_parent_student_relations(self, parent_id: UUID) -> List[ParentStudentRelation]:
        """Get all parent-student relations for a parent."""
        result = await self.db.execute(
            select(ParentStudentRelation)
            .options(
                selectinload(ParentStudentRelation.parent),
                selectinload(ParentStudentRelation.student)
            )
            .where(ParentStudentRelation.parent_id == parent_id)
        )
        return list(result.scalars().all())
    
    async def get_student_parent_relations(self, student_id: UUID) -> List[ParentStudentRelation]:
        """Get all parent-student relations for a student."""
        result = await self.db.execute(
            select(ParentStudentRelation)
            .options(
                selectinload(ParentStudentRelation.parent),
                selectinload(ParentStudentRelation.student)
            )
            .where(ParentStudentRelation.student_id == student_id)
        )
        return list(result.scalars().all())
    
    async def validate_parent_student_link(
        self,
        parent_id: UUID,
        student_id: UUID
    ) -> tuple[bool, str]:
        """Validate if parent-student link is allowed."""
        # Check if users exist
        parent = await self.get_user_by_id(parent_id)
        student = await self.get_user_by_id(student_id)
        
        if not parent:
            return False, "家长用户不存在"
        
        if not student:
            return False, "学生用户不存在"
        
        # Check roles
        if parent.role != UserRole.PARENT:
            return False, "用户不是家长角色"
        
        if student.role != UserRole.STUDENT:
            return False, "用户不是学生角色"
        
        # Check if both users are active
        if not parent.is_active:
            return False, "家长账户未激活"
        
        if not student.is_active:
            return False, "学生账户未激活"
        
        # Check if relation already exists
        existing_relation = await self.db.execute(
            select(ParentStudentRelation).where(
                and_(
                    ParentStudentRelation.parent_id == parent_id,
                    ParentStudentRelation.student_id == student_id
                )
            )
        )
        
        if existing_relation.scalar_one_or_none():
            return False, "关联关系已存在"
        
        return True, "验证通过"
    
    async def get_user_relationships_summary(self, user_id: UUID) -> dict:
        """Get a summary of user relationships."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return {}
        
        summary = {
            "user_id": user_id,
            "role": user.role.value,
            "relationships": {}
        }
        
        if user.role == UserRole.PARENT:
            children = await self.get_parent_children(user_id)
            summary["relationships"]["children"] = [
                {"id": child.id, "name": child.name, "email": child.email}
                for child in children
            ]
        
        elif user.role == UserRole.STUDENT:
            parents = await self.get_student_parents(user_id)
            teachers = await self.get_student_teachers(user_id)
            
            summary["relationships"]["parents"] = [
                {"id": parent.id, "name": parent.name, "email": parent.email}
                for parent in parents
            ]
            summary["relationships"]["teachers"] = [
                {"id": teacher.id, "name": teacher.name, "email": teacher.email}
                for teacher in teachers
            ]
        
        elif user.role == UserRole.TEACHER:
            students = await self.get_teacher_students(user_id)
            summary["relationships"]["students"] = [
                {"id": student.id, "name": student.name, "email": student.email}
                for student in students
            ]
        
        return summary
    
    async def search_users(
        self,
        query: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        school: Optional[str] = None,
        grade: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> tuple[List[User], int]:
        """Search users with advanced filtering and pagination."""
        stmt = select(User)
        count_stmt = select(User.id)
        
        # Apply filters
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
            count_stmt = count_stmt.where(User.is_active == is_active)
        
        if role:
            stmt = stmt.where(User.role == role)
            count_stmt = count_stmt.where(User.role == role)
        
        if is_verified is not None:
            stmt = stmt.where(User.is_verified == is_verified)
            count_stmt = count_stmt.where(User.is_verified == is_verified)
        
        if school:
            stmt = stmt.where(User.school.ilike(f"%{school}%"))
            count_stmt = count_stmt.where(User.school.ilike(f"%{school}%"))
        
        if grade:
            stmt = stmt.where(User.grade.ilike(f"%{grade}%"))
            count_stmt = count_stmt.where(User.grade.ilike(f"%{grade}%"))
        
        if query:
            search_filter = (
                User.name.ilike(f"%{query}%") | 
                User.email.ilike(f"%{query}%") |
                User.school.ilike(f"%{query}%")
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)
        
        # Get total count
        count_result = await self.db.execute(count_stmt)
        total = len(list(count_result.scalars().all()))
        
        # Apply pagination
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)
        
        # Order by created_at desc
        stmt = stmt.order_by(User.created_at.desc())
        
        result = await self.db.execute(stmt)
        users = list(result.scalars().all())
        
        return users, total
    
    async def get_user_statistics(self) -> dict:
        """Get user statistics."""
        from sqlalchemy import func
        
        # Total users
        total_result = await self.db.execute(select(func.count(User.id)))
        total_users = total_result.scalar() or 0
        
        # Active users
        active_result = await self.db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        active_users = active_result.scalar() or 0
        
        # Verified users
        verified_result = await self.db.execute(
            select(func.count(User.id)).where(User.is_verified == True)
        )
        verified_users = verified_result.scalar() or 0
        
        # Users by role
        role_stats = {}
        for role in UserRole:
            role_result = await self.db.execute(
                select(func.count(User.id)).where(User.role == role)
            )
            role_stats[role.value] = role_result.scalar() or 0
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "verified_users": verified_users,
            "unverified_users": total_users - verified_users,
            "students": role_stats.get("student", 0),
            "teachers": role_stats.get("teacher", 0),
            "parents": role_stats.get("parent", 0)
        }
    
    async def bulk_update_user_status(
        self,
        user_ids: List[UUID],
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None
    ) -> int:
        """Bulk update user status."""
        if not user_ids:
            return 0
        
        stmt = select(User).where(User.id.in_(user_ids))
        result = await self.db.execute(stmt)
        users = list(result.scalars().all())
        
        updated_count = 0
        for user in users:
            if is_active is not None:
                user.is_active = is_active
            if is_verified is not None:
                user.is_verified = is_verified
            user.updated_at = datetime.now(timezone.utc)
            updated_count += 1
        
        await self.db.commit()
        return updated_count