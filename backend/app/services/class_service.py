"""Class management service."""

import random
import string
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    ClassNotFoundError,
    DuplicateClassCodeError,
    InsufficientPermissionError,
    StudentAlreadyInClassError,
    StudentNotInClassError,
    ValidationError
)
from app.models.assignment import Assignment
from app.models.class_model import Class, ClassStudent
from app.models.user import User, UserRole
from app.schemas.class_schema import (
    ClassCreate,
    ClassStats,
    ClassUpdate,
    ClassStudentCreate,
    ClassStudentJoin
)


class ClassService:
    """Service for managing classes and class memberships."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_class(
        self,
        teacher_id: UUID,
        class_data: ClassCreate
    ) -> Class:
        """Create a new class with generated class code."""
        # Verify teacher exists and has teacher role
        teacher = await self._get_teacher(teacher_id)
        
        # Generate unique class code
        class_code = await self._generate_unique_class_code()
        
        # Create class
        new_class = Class(
            name=class_data.name,
            description=class_data.description,
            school=class_data.school,
            grade=class_data.grade,
            subject=class_data.subject,
            teacher_id=teacher_id,
            class_code=class_code
        )
        
        self.db.add(new_class)
        await self.db.commit()
        await self.db.refresh(new_class)
        
        return new_class

    async def get_class_by_id(
        self,
        class_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Class:
        """Get class by ID with permission check."""
        query = select(Class).where(Class.id == class_id)
        result = await self.db.execute(query)
        class_obj = result.scalar_one_or_none()
        
        if not class_obj:
            raise ClassNotFoundError(f"Class with ID {class_id} not found")
        
        # Check permissions if user_id provided
        if user_id:
            await self._check_class_access_permission(class_obj, user_id)
        
        return class_obj

    async def get_class_by_code(self, class_code: str) -> Class:
        """Get class by class code."""
        query = select(Class).where(
            and_(
                Class.class_code == class_code,
                Class.is_active == True
            )
        )
        result = await self.db.execute(query)
        class_obj = result.scalar_one_or_none()
        
        if not class_obj:
            raise ClassNotFoundError(f"Class with code {class_code} not found")
        
        return class_obj

    async def update_class(
        self,
        class_id: UUID,
        teacher_id: UUID,
        update_data: ClassUpdate
    ) -> Class:
        """Update class information."""
        class_obj = await self.get_class_by_id(class_id)
        
        # Check if user is the teacher of this class
        if class_obj.teacher_id != teacher_id:
            raise InsufficientPermissionError("Only the class teacher can update class information")
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(class_obj, field, value)
        
        class_obj.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(class_obj)
        
        return class_obj

    async def delete_class(self, class_id: UUID, teacher_id: UUID) -> bool:
        """Soft delete a class (set is_active to False)."""
        class_obj = await self.get_class_by_id(class_id)
        
        # Check if user is the teacher of this class
        if class_obj.teacher_id != teacher_id:
            raise InsufficientPermissionError("Only the class teacher can delete the class")
        
        class_obj.is_active = False
        class_obj.updated_at = datetime.utcnow()
        
        await self.db.commit()
        return True

    async def get_teacher_classes(
        self,
        teacher_id: UUID,
        include_inactive: bool = False
    ) -> List[Class]:
        """Get all classes taught by a teacher."""
        query = select(Class).where(Class.teacher_id == teacher_id)
        
        if not include_inactive:
            query = query.where(Class.is_active == True)
        
        query = query.order_by(Class.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_student_classes(
        self,
        student_id: UUID,
        include_inactive: bool = False
    ) -> List[Class]:
        """Get all classes a student is enrolled in."""
        query = (
            select(Class)
            .join(ClassStudent)
            .where(ClassStudent.student_id == student_id)
        )
        
        if not include_inactive:
            query = query.where(
                and_(
                    Class.is_active == True,
                    ClassStudent.is_active == True
                )
            )
        
        query = query.order_by(ClassStudent.joined_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def regenerate_class_code(
        self,
        class_id: UUID,
        teacher_id: UUID
    ) -> str:
        """Regenerate class code for a class."""
        class_obj = await self.get_class_by_id(class_id)
        
        # Check if user is the teacher of this class
        if class_obj.teacher_id != teacher_id:
            raise InsufficientPermissionError("Only the class teacher can regenerate class code")
        
        # Generate new unique class code
        new_code = await self._generate_unique_class_code()
        class_obj.class_code = new_code
        class_obj.updated_at = datetime.utcnow()
        
        await self.db.commit()
        return new_code

    async def get_class_stats(self, class_id: UUID, user_id: UUID) -> ClassStats:
        """Get statistics for a class."""
        class_obj = await self.get_class_by_id(class_id, user_id)
        
        # Get student counts
        active_students_query = select(func.count(ClassStudent.id)).where(
            and_(
                ClassStudent.class_id == class_id,
                ClassStudent.is_active == True
            )
        )
        active_students_result = await self.db.execute(active_students_query)
        active_students = active_students_result.scalar() or 0
        
        total_students_query = select(func.count(ClassStudent.id)).where(
            ClassStudent.class_id == class_id
        )
        total_students_result = await self.db.execute(total_students_query)
        total_students = total_students_result.scalar() or 0
        
        # Get assignment counts
        assignments_query = select(func.count(Assignment.id)).where(
            Assignment.class_id == class_id
        )
        assignments_result = await self.db.execute(assignments_query)
        total_assignments = assignments_result.scalar() or 0
        
        # Calculate participation rate
        participation_rate = (active_students / total_students * 100) if total_students > 0 else 0.0
        
        return ClassStats(
            total_students=total_students,
            active_students=active_students,
            total_assignments=total_assignments,
            completed_assignments=0,  # Will be implemented in assignment service
            average_score=None,  # Will be implemented in assignment service
            participation_rate=participation_rate
        )

    async def get_detailed_class_analytics(
        self,
        class_id: UUID,
        user_id: UUID
    ) -> dict:
        """Get detailed analytics for a class."""
        class_obj = await self.get_class_by_id(class_id, user_id)
        
        # Basic stats
        basic_stats = await self.get_class_stats(class_id, user_id)
        
        # Student enrollment trends (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        enrollment_trend_query = select(
            func.date(ClassStudent.joined_at).label('date'),
            func.count(ClassStudent.id).label('enrollments')
        ).where(
            and_(
                ClassStudent.class_id == class_id,
                ClassStudent.joined_at >= thirty_days_ago
            )
        ).group_by(func.date(ClassStudent.joined_at)).order_by('date')
        
        enrollment_result = await self.db.execute(enrollment_trend_query)
        enrollment_trend = [
            {"date": str(row.date), "enrollments": row.enrollments}
            for row in enrollment_result
        ]
        
        # Student activity (active vs inactive)
        activity_query = select(
            ClassStudent.is_active,
            func.count(ClassStudent.id).label('count')
        ).where(
            ClassStudent.class_id == class_id
        ).group_by(ClassStudent.is_active)
        
        activity_result = await self.db.execute(activity_query)
        activity_breakdown = {}
        for row in activity_result:
            status = "active" if row.is_active else "inactive"
            activity_breakdown[status] = row.count
        
        return {
            "basic_stats": basic_stats.dict(),
            "enrollment_trend": enrollment_trend,
            "activity_breakdown": activity_breakdown,
            "class_info": {
                "id": str(class_obj.id),
                "name": class_obj.name,
                "created_at": class_obj.created_at.isoformat(),
                "teacher_id": str(class_obj.teacher_id)
            }
        }

    async def get_class_performance_summary(
        self,
        class_id: UUID,
        user_id: UUID
    ) -> dict:
        """Get class performance summary (placeholder for future assignment integration)."""
        class_obj = await self.get_class_by_id(class_id, user_id)
        
        # This will be enhanced when assignment and grading services are implemented
        return {
            "class_id": str(class_id),
            "class_name": class_obj.name,
            "total_students": class_obj.student_count,
            "performance_metrics": {
                "average_score": None,  # To be implemented with assignments
                "completion_rate": None,  # To be implemented with assignments
                "top_performers": [],  # To be implemented with assignments
                "struggling_students": []  # To be implemented with assignments
            },
            "recent_activity": {
                "new_assignments": 0,  # To be implemented with assignments
                "recent_submissions": 0,  # To be implemented with assignments
                "pending_grading": 0  # To be implemented with assignments
            }
        }

    async def export_class_data(
        self,
        class_id: UUID,
        user_id: UUID,
        format_type: str = "json"
    ) -> dict:
        """Export class data for analysis."""
        # Verify permissions
        class_obj = await self.get_class_by_id(class_id, user_id)
        
        # Get class memberships with student details
        memberships = await self.get_class_memberships(class_id, user_id, include_inactive=True)
        
        # Prepare export data
        export_data = {
            "class_info": {
                "id": str(class_obj.id),
                "name": class_obj.name,
                "description": class_obj.description,
                "school": class_obj.school,
                "grade": class_obj.grade,
                "subject": class_obj.subject,
                "class_code": class_obj.class_code,
                "created_at": class_obj.created_at.isoformat(),
                "teacher_id": str(class_obj.teacher_id)
            },
            "students": [
                {
                    "student_id": str(membership.student_id),
                    "student_name": membership.student.name,
                    "student_email": membership.student.email,
                    "joined_at": membership.joined_at.isoformat(),
                    "left_at": membership.left_at.isoformat() if membership.left_at else None,
                    "is_active": membership.is_active
                }
                for membership in memberships
            ],
            "statistics": (await self.get_class_stats(class_id, user_id)).dict(),
            "export_timestamp": datetime.utcnow().isoformat(),
            "format": format_type
        }
        
        return export_data

    async def get_class_ranking(
        self,
        class_id: UUID,
        user_id: UUID
    ) -> List[dict]:
        """Get student ranking in class (placeholder for future implementation)."""
        class_obj = await self.get_class_by_id(class_id, user_id)
        
        # Get all active students
        students = await self.get_class_students(class_id, user_id)
        
        # This will be enhanced when assignment and grading data is available
        ranking = [
            {
                "rank": idx + 1,
                "student_id": str(student.id),
                "student_name": student.name,
                "average_score": None,  # To be calculated from assignments
                "total_assignments": 0,  # To be calculated from assignments
                "completion_rate": 0.0  # To be calculated from assignments
            }
            for idx, student in enumerate(students)
        ]
        
        return ranking

    async def _generate_unique_class_code(self, length: int = 8) -> str:
        """Generate a unique class code."""
        max_attempts = 10
        
        for _ in range(max_attempts):
            # Generate random code with uppercase letters and numbers
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            
            # Check if code already exists
            query = select(Class).where(Class.class_code == code)
            result = await self.db.execute(query)
            existing_class = result.scalar_one_or_none()
            
            if not existing_class:
                return code
        
        raise DuplicateClassCodeError("Failed to generate unique class code after multiple attempts")

    async def _get_teacher(self, teacher_id: UUID) -> User:
        """Get teacher user and verify role."""
        query = select(User).where(
            and_(
                User.id == teacher_id,
                User.role == UserRole.TEACHER,
                User.is_active == True
            )
        )
        result = await self.db.execute(query)
        teacher = result.scalar_one_or_none()
        
        if not teacher:
            raise ValidationError("User is not an active teacher")
        
        return teacher

    async def add_student_to_class(
        self,
        class_id: UUID,
        student_id: UUID,
        teacher_id: UUID
    ) -> ClassStudent:
        """Add a student to a class (teacher action)."""
        # Verify class exists and teacher has permission
        class_obj = await self.get_class_by_id(class_id)
        if class_obj.teacher_id != teacher_id:
            raise InsufficientPermissionError("Only the class teacher can add students")
        
        # Verify student exists and has student role
        student = await self._get_student(student_id)
        
        # Check if student is already in the class
        existing_membership = await self._get_class_membership(class_id, student_id)
        if existing_membership and existing_membership.is_active:
            raise StudentAlreadyInClassError("Student is already enrolled in this class")
        
        # If there's an inactive membership, reactivate it
        if existing_membership and not existing_membership.is_active:
            existing_membership.is_active = True
            existing_membership.joined_at = datetime.utcnow()
            existing_membership.left_at = None
            await self.db.commit()
            await self.db.refresh(existing_membership)
            return existing_membership
        
        # Create new membership
        membership = ClassStudent(
            class_id=class_id,
            student_id=student_id,
            is_active=True
        )
        
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)
        
        return membership

    async def join_class_by_code(
        self,
        student_id: UUID,
        class_code: str
    ) -> ClassStudent:
        """Student joins a class using class code."""
        # Verify student exists and has student role
        student = await self._get_student(student_id)
        
        # Get class by code
        class_obj = await self.get_class_by_code(class_code)
        
        # Check if student is already in the class
        existing_membership = await self._get_class_membership(class_obj.id, student_id)
        if existing_membership and existing_membership.is_active:
            raise StudentAlreadyInClassError("You are already enrolled in this class")
        
        # If there's an inactive membership, reactivate it
        if existing_membership and not existing_membership.is_active:
            existing_membership.is_active = True
            existing_membership.joined_at = datetime.utcnow()
            existing_membership.left_at = None
            await self.db.commit()
            await self.db.refresh(existing_membership)
            return existing_membership
        
        # Create new membership
        membership = ClassStudent(
            class_id=class_obj.id,
            student_id=student_id,
            is_active=True
        )
        
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)
        
        return membership

    async def remove_student_from_class(
        self,
        class_id: UUID,
        student_id: UUID,
        teacher_id: UUID
    ) -> bool:
        """Remove a student from a class (teacher action)."""
        # Verify class exists and teacher has permission
        class_obj = await self.get_class_by_id(class_id)
        if class_obj.teacher_id != teacher_id:
            raise InsufficientPermissionError("Only the class teacher can remove students")
        
        # Get membership
        membership = await self._get_class_membership(class_id, student_id)
        if not membership or not membership.is_active:
            raise StudentNotInClassError("Student is not enrolled in this class")
        
        # Soft delete membership
        membership.is_active = False
        membership.left_at = datetime.utcnow()
        
        await self.db.commit()
        return True

    async def leave_class(
        self,
        class_id: UUID,
        student_id: UUID
    ) -> bool:
        """Student leaves a class."""
        # Verify student exists
        student = await self._get_student(student_id)
        
        # Get membership
        membership = await self._get_class_membership(class_id, student_id)
        if not membership or not membership.is_active:
            raise StudentNotInClassError("You are not enrolled in this class")
        
        # Soft delete membership
        membership.is_active = False
        membership.left_at = datetime.utcnow()
        
        await self.db.commit()
        return True

    async def get_class_students(
        self,
        class_id: UUID,
        teacher_id: UUID,
        include_inactive: bool = False
    ) -> List[User]:
        """Get all students in a class."""
        # Verify class exists and teacher has permission
        class_obj = await self.get_class_by_id(class_id)
        if class_obj.teacher_id != teacher_id:
            raise InsufficientPermissionError("Only the class teacher can view student list")
        
        query = (
            select(User)
            .join(ClassStudent)
            .where(ClassStudent.class_id == class_id)
        )
        
        if not include_inactive:
            query = query.where(ClassStudent.is_active == True)
        
        query = query.order_by(User.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_class_memberships(
        self,
        class_id: UUID,
        teacher_id: UUID,
        include_inactive: bool = False
    ) -> List[ClassStudent]:
        """Get all class memberships with details."""
        # Verify class exists and teacher has permission
        class_obj = await self.get_class_by_id(class_id)
        if class_obj.teacher_id != teacher_id:
            raise InsufficientPermissionError("Only the class teacher can view memberships")
        
        query = (
            select(ClassStudent)
            .options(selectinload(ClassStudent.student))
            .where(ClassStudent.class_id == class_id)
        )
        
        if not include_inactive:
            query = query.where(ClassStudent.is_active == True)
        
        query = query.order_by(ClassStudent.joined_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_student_class_history(
        self,
        student_id: UUID,
        requesting_user_id: UUID
    ) -> List[ClassStudent]:
        """Get student's class enrollment history."""
        # Verify requesting user is the student or has permission
        if requesting_user_id != student_id:
            # Check if requesting user is a teacher of any class the student is in
            # or a parent (to be implemented later)
            requesting_user_query = select(User).where(User.id == requesting_user_id)
            requesting_user_result = await self.db.execute(requesting_user_query)
            requesting_user = requesting_user_result.scalar_one_or_none()
            
            if not requesting_user:
                raise ValidationError("Requesting user not found")
            
            if requesting_user.role not in [UserRole.TEACHER, UserRole.PARENT]:
                raise InsufficientPermissionError("Insufficient permission to view student history")
        
        query = (
            select(ClassStudent)
            .options(selectinload(ClassStudent.class_))
            .where(ClassStudent.student_id == student_id)
            .order_by(ClassStudent.joined_at.desc())
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def _get_student(self, student_id: UUID) -> User:
        """Get student user and verify role."""
        query = select(User).where(
            and_(
                User.id == student_id,
                User.role == UserRole.STUDENT,
                User.is_active == True
            )
        )
        result = await self.db.execute(query)
        student = result.scalar_one_or_none()
        
        if not student:
            raise ValidationError("User is not an active student")
        
        return student

    async def _get_class_membership(
        self,
        class_id: UUID,
        student_id: UUID
    ) -> Optional[ClassStudent]:
        """Get class membership for a student."""
        query = select(ClassStudent).where(
            and_(
                ClassStudent.class_id == class_id,
                ClassStudent.student_id == student_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _check_class_access_permission(self, class_obj: Class, user_id: UUID) -> None:
        """Check if user has permission to access the class."""
        # Get user
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValidationError("User not found")
        
        # Teacher can access their own classes
        if class_obj.teacher_id == user_id:
            return
        
        # Students can access classes they're enrolled in
        if user.role == UserRole.STUDENT:
            membership_query = select(ClassStudent).where(
                and_(
                    ClassStudent.class_id == class_obj.id,
                    ClassStudent.student_id == user_id,
                    ClassStudent.is_active == True
                )
            )
            membership_result = await self.db.execute(membership_query)
            membership = membership_result.scalar_one_or_none()
            
            if membership:
                return
        
        # Parents can access classes their children are in
        if user.role == UserRole.PARENT:
            # This will be implemented when parent-student relationships are added
            pass
        
        raise InsufficientPermissionError("User does not have permission to access this class")