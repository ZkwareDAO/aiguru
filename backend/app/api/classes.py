"""Class management API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import (
    ClassNotFoundError,
    DuplicateClassCodeError,
    InsufficientPermissionError,
    StudentAlreadyInClassError,
    StudentNotInClassError,
    ValidationError
)
from app.models.user import User, UserRole
from app.schemas.class_schema import (
    ClassCreate,
    ClassResponse,
    ClassStats,
    ClassUpdate,
    ClassCodeResponse,
    ClassListResponse,
    ClassStudentCreate,
    ClassStudentJoin,
    ClassStudentResponse,
    ClassStudentWithInfo
)
from app.services.class_service import ClassService

router = APIRouter(prefix="/classes", tags=["classes"])


@router.post("/", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
async def create_class(
    class_data: ClassCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new class. Only teachers can create classes."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create classes"
        )
    
    try:
        class_service = ClassService(db)
        new_class = await class_service.create_class(current_user.id, class_data)
        
        # Convert to response model
        return ClassResponse(
            id=new_class.id,
            name=new_class.name,
            description=new_class.description,
            school=new_class.school,
            grade=new_class.grade,
            subject=new_class.subject,
            class_code=new_class.class_code,
            teacher_id=new_class.teacher_id,
            is_active=new_class.is_active,
            created_at=new_class.created_at,
            updated_at=new_class.updated_at,
            student_count=0
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DuplicateClassCodeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(
    class_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get class information by ID."""
    try:
        class_service = ClassService(db)
        class_obj = await class_service.get_class_by_id(class_id, current_user.id)
        
        return ClassResponse(
            id=class_obj.id,
            name=class_obj.name,
            description=class_obj.description,
            school=class_obj.school,
            grade=class_obj.grade,
            subject=class_obj.subject,
            class_code=class_obj.class_code,
            teacher_id=class_obj.teacher_id,
            is_active=class_obj.is_active,
            created_at=class_obj.created_at,
            updated_at=class_obj.updated_at,
            student_count=class_obj.student_count
        )
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.put("/{class_id}", response_model=ClassResponse)
async def update_class(
    class_id: UUID,
    update_data: ClassUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update class information. Only the class teacher can update."""
    try:
        class_service = ClassService(db)
        updated_class = await class_service.update_class(class_id, current_user.id, update_data)
        
        return ClassResponse(
            id=updated_class.id,
            name=updated_class.name,
            description=updated_class.description,
            school=updated_class.school,
            grade=updated_class.grade,
            subject=updated_class.subject,
            class_code=updated_class.class_code,
            teacher_id=updated_class.teacher_id,
            is_active=updated_class.is_active,
            created_at=updated_class.created_at,
            updated_at=updated_class.updated_at,
            student_count=updated_class.student_count
        )
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class(
    class_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete (deactivate) a class. Only the class teacher can delete."""
    try:
        class_service = ClassService(db)
        await class_service.delete_class(class_id, current_user.id)
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/", response_model=List[ClassResponse])
async def get_user_classes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get classes for the current user (taught classes for teachers, enrolled classes for students)."""
    try:
        class_service = ClassService(db)
        
        if current_user.role == UserRole.TEACHER:
            classes = await class_service.get_teacher_classes(current_user.id)
        elif current_user.role == UserRole.STUDENT:
            classes = await class_service.get_student_classes(current_user.id)
        else:
            # Parents will be handled later
            classes = []
        
        return [
            ClassResponse(
                id=class_obj.id,
                name=class_obj.name,
                description=class_obj.description,
                school=class_obj.school,
                grade=class_obj.grade,
                subject=class_obj.subject,
                class_code=class_obj.class_code,
                teacher_id=class_obj.teacher_id,
                is_active=class_obj.is_active,
                created_at=class_obj.created_at,
                updated_at=class_obj.updated_at,
                student_count=class_obj.student_count
            )
            for class_obj in classes
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{class_id}/regenerate-code", response_model=ClassCodeResponse)
async def regenerate_class_code(
    class_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Regenerate class code. Only the class teacher can regenerate."""
    try:
        class_service = ClassService(db)
        new_code = await class_service.regenerate_class_code(class_id, current_user.id)
        
        return ClassCodeResponse(class_code=new_code)
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{class_id}/stats", response_model=ClassStats)
async def get_class_stats(
    class_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get class statistics."""
    try:
        class_service = ClassService(db)
        stats = await class_service.get_class_stats(class_id, current_user.id)
        return stats
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# Student Management Endpoints

@router.post("/{class_id}/students", response_model=ClassStudentResponse, status_code=status.HTTP_201_CREATED)
async def add_student_to_class(
    class_id: UUID,
    student_data: ClassStudentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a student to a class. Only teachers can add students."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can add students to classes"
        )
    
    try:
        class_service = ClassService(db)
        membership = await class_service.add_student_to_class(
            class_id, student_data.student_id, current_user.id
        )
        
        return ClassStudentResponse(
            id=membership.id,
            class_id=membership.class_id,
            student_id=membership.student_id,
            is_active=membership.is_active,
            joined_at=membership.joined_at,
            left_at=membership.left_at
        )
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (ValidationError, StudentAlreadyInClassError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/join", response_model=ClassStudentResponse, status_code=status.HTTP_201_CREATED)
async def join_class_by_code(
    join_data: ClassStudentJoin,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Student joins a class using class code."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can join classes"
        )
    
    try:
        class_service = ClassService(db)
        membership = await class_service.join_class_by_code(
            current_user.id, join_data.class_code
        )
        
        return ClassStudentResponse(
            id=membership.id,
            class_id=membership.class_id,
            student_id=membership.student_id,
            is_active=membership.is_active,
            joined_at=membership.joined_at,
            left_at=membership.left_at
        )
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, StudentAlreadyInClassError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{class_id}/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_student_from_class(
    class_id: UUID,
    student_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a student from a class. Only teachers can remove students."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can remove students from classes"
        )
    
    try:
        class_service = ClassService(db)
        await class_service.remove_student_from_class(class_id, student_id, current_user.id)
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except StudentNotInClassError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{class_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_class(
    class_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Student leaves a class."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can leave classes"
        )
    
    try:
        class_service = ClassService(db)
        await class_service.leave_class(class_id, current_user.id)
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except StudentNotInClassError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{class_id}/students", response_model=List[ClassStudentWithInfo])
async def get_class_students(
    class_id: UUID,
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all students in a class. Only teachers can view student list."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view class student list"
        )
    
    try:
        class_service = ClassService(db)
        memberships = await class_service.get_class_memberships(
            class_id, current_user.id, include_inactive
        )
        
        return [
            ClassStudentWithInfo(
                id=membership.id,
                class_id=membership.class_id,
                student_id=membership.student_id,
                is_active=membership.is_active,
                joined_at=membership.joined_at,
                left_at=membership.left_at,
                student_name=membership.student.name,
                student_email=membership.student.email
            )
            for membership in memberships
        ]
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/students/{student_id}/history", response_model=List[ClassStudentResponse])
async def get_student_class_history(
    student_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get student's class enrollment history."""
    try:
        class_service = ClassService(db)
        memberships = await class_service.get_student_class_history(student_id, current_user.id)
        
        return [
            ClassStudentResponse(
                id=membership.id,
                class_id=membership.class_id,
                student_id=membership.student_id,
                is_active=membership.is_active,
                joined_at=membership.joined_at,
                left_at=membership.left_at
            )
            for membership in memberships
        ]
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# Analytics and Export Endpoints

@router.get("/{class_id}/analytics")
async def get_class_analytics(
    class_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed analytics for a class."""
    try:
        class_service = ClassService(db)
        analytics = await class_service.get_detailed_class_analytics(class_id, current_user.id)
        return analytics
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{class_id}/performance")
async def get_class_performance(
    class_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get class performance summary."""
    try:
        class_service = ClassService(db)
        performance = await class_service.get_class_performance_summary(class_id, current_user.id)
        return performance
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{class_id}/ranking")
async def get_class_ranking(
    class_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get student ranking in class."""
    try:
        class_service = ClassService(db)
        ranking = await class_service.get_class_ranking(class_id, current_user.id)
        return {"class_id": str(class_id), "ranking": ranking}
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{class_id}/export")
async def export_class_data(
    class_id: UUID,
    format_type: str = "json",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export class data for analysis."""
    if format_type not in ["json", "csv"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be 'json' or 'csv'"
        )
    
    try:
        class_service = ClassService(db)
        export_data = await class_service.export_class_data(class_id, current_user.id, format_type)
        
        if format_type == "json":
            return export_data
        else:
            # For CSV format, we would convert to CSV here
            # For now, return JSON with a note
            export_data["note"] = "CSV export will be implemented in future version"
            return export_data
            
    except ClassNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))