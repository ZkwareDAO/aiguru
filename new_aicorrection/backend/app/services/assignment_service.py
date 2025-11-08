"""Assignment management service."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AssignmentNotFoundError,
    ClassNotFoundError,
    InsufficientPermissionError,
    SubmissionNotFoundError,
    ValidationError
)
from app.models.assignment import Assignment, AssignmentStatus, Submission, SubmissionStatus
from app.models.class_model import Class, ClassStudent
from app.models.user import User, UserRole
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentStats,
    AssignmentUpdate,
    SubmissionCreate,
    SubmissionGrade,
    SubmissionUpdate
)


class AssignmentService:
    """Service for managing assignments and submissions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Assignment CRUD operations

    async def create_assignment(
        self,
        teacher_id: UUID,
        assignment_data: AssignmentCreate
    ) -> Assignment:
        """Create a new assignment."""
        # Verify teacher exists and has permission to create assignments in this class
        await self._verify_teacher_class_permission(teacher_id, assignment_data.class_id)
        
        # Create assignment
        assignment = Assignment(
            title=assignment_data.title,
            description=assignment_data.description,
            instructions=assignment_data.instructions,
            subject=assignment_data.subject,
            topic=assignment_data.topic,
            difficulty_level=assignment_data.difficulty_level,
            total_points=assignment_data.total_points,
            passing_score=assignment_data.passing_score,
            due_date=assignment_data.due_date,
            start_date=assignment_data.start_date,
            allow_late_submission=assignment_data.allow_late_submission,
            auto_grade=assignment_data.auto_grade,
            show_correct_answers=assignment_data.show_correct_answers,
            teacher_id=teacher_id,
            class_id=assignment_data.class_id,
            status=AssignmentStatus.DRAFT
        )
        
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)
        
        return assignment

    async def get_assignment_by_id(
        self,
        assignment_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Assignment:
        """Get assignment by ID with permission check."""
        query = (
            select(Assignment)
            .options(
                selectinload(Assignment.teacher),
                selectinload(Assignment.class_),
                selectinload(Assignment.submissions)
            )
            .where(Assignment.id == assignment_id)
        )
        result = await self.db.execute(query)
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise AssignmentNotFoundError(f"Assignment with ID {assignment_id} not found")
        
        # Check permissions if user_id provided
        if user_id:
            await self._check_assignment_access_permission(assignment, user_id)
        
        return assignment

    async def update_assignment(
        self,
        assignment_id: UUID,
        teacher_id: UUID,
        update_data: AssignmentUpdate
    ) -> Assignment:
        """Update assignment information."""
        assignment = await self.get_assignment_by_id(assignment_id)
        
        # Check if user is the teacher of this assignment
        if assignment.teacher_id != teacher_id:
            raise InsufficientPermissionError("Only the assignment creator can update this assignment")
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(assignment, field, value)
        
        assignment.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(assignment)
        
        return assignment

    async def delete_assignment(
        self,
        assignment_id: UUID,
        teacher_id: UUID
    ) -> bool:
        """Delete (archive) an assignment."""
        assignment = await self.get_assignment_by_id(assignment_id)
        
        # Check if user is the teacher of this assignment
        if assignment.teacher_id != teacher_id:
            raise InsufficientPermissionError("Only the assignment creator can delete this assignment")
        
        assignment.status = AssignmentStatus.ARCHIVED
        assignment.updated_at = datetime.utcnow()
        
        await self.db.commit()
        return True

    async def publish_assignment(
        self,
        assignment_id: UUID,
        teacher_id: UUID
    ) -> Assignment:
        """Publish an assignment to make it active."""
        assignment = await self.get_assignment_by_id(assignment_id)
        
        # Check if user is the teacher of this assignment
        if assignment.teacher_id != teacher_id:
            raise InsufficientPermissionError("Only the assignment creator can publish this assignment")
        
        if assignment.status != AssignmentStatus.DRAFT:
            raise ValidationError("Only draft assignments can be published")
        
        assignment.status = AssignmentStatus.ACTIVE
        assignment.published_at = datetime.utcnow()
        assignment.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(assignment)
        
        # Send notifications to students
        try:
            from app.services.notification_service import AssignmentNotificationService
            notification_service = AssignmentNotificationService(self.db)
            await notification_service.notify_assignment_published(assignment)
        except Exception:
            # Don't fail the assignment publishing if notifications fail
            pass
        
        return assignment

    async def close_assignment(
        self,
        assignment_id: UUID,
        teacher_id: UUID
    ) -> Assignment:
        """Close an assignment to stop accepting submissions."""
        assignment = await self.get_assignment_by_id(assignment_id)
        
        # Check if user is the teacher of this assignment
        if assignment.teacher_id != teacher_id:
            raise InsufficientPermissionError("Only the assignment creator can close this assignment")
        
        if assignment.status != AssignmentStatus.ACTIVE:
            raise ValidationError("Only active assignments can be closed")
        
        assignment.status = AssignmentStatus.CLOSED
        assignment.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(assignment)
        
        return assignment

    # Assignment listing and filtering

    async def get_teacher_assignments(
        self,
        teacher_id: UUID,
        class_id: Optional[UUID] = None,
        status: Optional[AssignmentStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Assignment]:
        """Get assignments created by a teacher."""
        query = (
            select(Assignment)
            .options(selectinload(Assignment.class_))
            .where(Assignment.teacher_id == teacher_id)
        )
        
        if class_id:
            query = query.where(Assignment.class_id == class_id)
        
        if status:
            query = query.where(Assignment.status == status)
        
        query = query.order_by(desc(Assignment.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_student_assignments(
        self,
        student_id: UUID,
        class_id: Optional[UUID] = None,
        status: Optional[AssignmentStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Assignment]:
        """Get assignments available to a student."""
        # Get classes the student is enrolled in
        class_query = (
            select(ClassStudent.class_id)
            .where(
                and_(
                    ClassStudent.student_id == student_id,
                    ClassStudent.is_active == True
                )
            )
        )
        
        if class_id:
            class_query = class_query.where(ClassStudent.class_id == class_id)
        
        class_result = await self.db.execute(class_query)
        class_ids = [row[0] for row in class_result]
        
        if not class_ids:
            return []
        
        # Get assignments from those classes
        query = (
            select(Assignment)
            .options(selectinload(Assignment.class_))
            .where(Assignment.class_id.in_(class_ids))
        )
        
        if status:
            query = query.where(Assignment.status == status)
        else:
            # By default, only show active assignments to students
            query = query.where(Assignment.status == AssignmentStatus.ACTIVE)
        
        query = query.order_by(desc(Assignment.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_class_assignments(
        self,
        class_id: UUID,
        user_id: UUID,
        status: Optional[AssignmentStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Assignment]:
        """Get assignments for a specific class."""
        # Verify user has access to this class
        await self._verify_class_access(user_id, class_id)
        
        query = (
            select(Assignment)
            .where(Assignment.class_id == class_id)
        )
        
        if status:
            query = query.where(Assignment.status == status)
        
        query = query.order_by(desc(Assignment.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    # Assignment statistics

    async def get_assignment_stats(
        self,
        assignment_id: UUID,
        user_id: UUID
    ) -> AssignmentStats:
        """Get statistics for an assignment."""
        assignment = await self.get_assignment_by_id(assignment_id, user_id)
        
        # Get submission counts
        total_submissions_query = select(func.count(Submission.id)).where(
            Submission.assignment_id == assignment_id
        )
        total_submissions_result = await self.db.execute(total_submissions_query)
        total_submissions = total_submissions_result.scalar() or 0
        
        pending_submissions_query = select(func.count(Submission.id)).where(
            and_(
                Submission.assignment_id == assignment_id,
                Submission.status == SubmissionStatus.PENDING
            )
        )
        pending_submissions_result = await self.db.execute(pending_submissions_query)
        pending_submissions = pending_submissions_result.scalar() or 0
        
        graded_submissions_query = select(func.count(Submission.id)).where(
            and_(
                Submission.assignment_id == assignment_id,
                Submission.status == SubmissionStatus.GRADED
            )
        )
        graded_submissions_result = await self.db.execute(graded_submissions_query)
        graded_submissions = graded_submissions_result.scalar() or 0
        
        # Calculate average score
        avg_score_query = select(func.avg(Submission.score)).where(
            and_(
                Submission.assignment_id == assignment_id,
                Submission.score.isnot(None)
            )
        )
        avg_score_result = await self.db.execute(avg_score_query)
        average_score = avg_score_result.scalar()
        
        # Get total students in class
        total_students_query = select(func.count(ClassStudent.id)).where(
            and_(
                ClassStudent.class_id == assignment.class_id,
                ClassStudent.is_active == True
            )
        )
        total_students_result = await self.db.execute(total_students_query)
        total_students = total_students_result.scalar() or 0
        
        # Calculate completion rate
        completion_rate = (total_submissions / total_students * 100) if total_students > 0 else 0.0
        
        # Count on-time vs late submissions
        on_time_submissions_query = select(func.count(Submission.id)).where(
            and_(
                Submission.assignment_id == assignment_id,
                Submission.is_late == False
            )
        )
        on_time_submissions_result = await self.db.execute(on_time_submissions_query)
        on_time_submissions = on_time_submissions_result.scalar() or 0
        
        late_submissions = total_submissions - on_time_submissions
        
        return AssignmentStats(
            total_submissions=total_submissions,
            pending_submissions=pending_submissions,
            graded_submissions=graded_submissions,
            average_score=average_score,
            completion_rate=completion_rate,
            on_time_submissions=on_time_submissions,
            late_submissions=late_submissions
        )

    # Submission operations

    async def create_submission(
        self,
        student_id: UUID,
        submission_data: SubmissionCreate
    ) -> Submission:
        """Create a new submission for an assignment."""
        # Verify assignment exists and student can access it
        assignment = await self.get_assignment_by_id(submission_data.assignment_id)
        
        if not await self.can_student_access_assignment(submission_data.assignment_id, student_id):
            raise InsufficientPermissionError("Student cannot access this assignment")
        
        # Check if assignment is accepting submissions
        if assignment.status != AssignmentStatus.ACTIVE:
            raise ValidationError("Assignment is not accepting submissions")
        
        # Check if student already has a submission
        existing_submission = await self._get_student_submission(
            submission_data.assignment_id, student_id
        )
        if existing_submission:
            raise ValidationError("Student already has a submission for this assignment")
        
        # Check if submission is late
        is_late = False
        if assignment.due_date and datetime.utcnow() > assignment.due_date.replace(tzinfo=None):
            if not assignment.allow_late_submission:
                raise ValidationError("Assignment due date has passed and late submissions are not allowed")
            is_late = True
        
        # Create submission
        submission = Submission(
            assignment_id=submission_data.assignment_id,
            student_id=student_id,
            content=submission_data.content,
            notes=submission_data.notes,
            status=SubmissionStatus.SUBMITTED,
            is_late=is_late,
            submitted_at=datetime.utcnow(),
            max_score=assignment.total_points
        )
        
        self.db.add(submission)
        await self.db.commit()
        await self.db.refresh(submission)
        
        # Send notification to teacher
        try:
            from app.services.notification_service import AssignmentNotificationService
            notification_service = AssignmentNotificationService(self.db)
            await notification_service.notify_submission_received(submission)
        except Exception:
            # Don't fail the submission if notifications fail
            pass
        
        return submission

    async def update_submission(
        self,
        submission_id: UUID,
        student_id: UUID,
        update_data: SubmissionUpdate
    ) -> Submission:
        """Update a submission (only by the student who created it)."""
        submission = await self.get_submission_by_id(submission_id)
        
        # Check if user is the student who created this submission
        if submission.student_id != student_id:
            raise InsufficientPermissionError("Only the submission creator can update this submission")
        
        # Check if submission can still be updated
        if submission.status in [SubmissionStatus.GRADED, SubmissionStatus.RETURNED]:
            raise ValidationError("Cannot update a graded submission")
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            if field != 'status':  # Students cannot change status directly
                setattr(submission, field, value)
        
        submission.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(submission)
        
        return submission

    async def get_submission_by_id(
        self,
        submission_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Submission:
        """Get submission by ID with permission check."""
        query = (
            select(Submission)
            .options(
                selectinload(Submission.assignment),
                selectinload(Submission.student),
                selectinload(Submission.files)
            )
            .where(Submission.id == submission_id)
        )
        result = await self.db.execute(query)
        submission = result.scalar_one_or_none()
        
        if not submission:
            raise SubmissionNotFoundError(f"Submission with ID {submission_id} not found")
        
        # Check permissions if user_id provided
        if user_id:
            await self._check_submission_access_permission(submission, user_id)
        
        return submission

    async def grade_submission(
        self,
        submission_id: UUID,
        teacher_id: UUID,
        grade_data: SubmissionGrade
    ) -> Submission:
        """Grade a submission."""
        submission = await self.get_submission_by_id(submission_id)
        
        # Check if user is the teacher of this assignment
        if submission.assignment.teacher_id != teacher_id:
            raise InsufficientPermissionError("Only the assignment creator can grade submissions")
        
        # Update submission with grade
        submission.score = grade_data.score
        if grade_data.max_score:
            submission.max_score = grade_data.max_score
        submission.feedback = grade_data.feedback
        submission.teacher_comments = grade_data.teacher_comments
        submission.needs_review = grade_data.needs_review
        submission.status = SubmissionStatus.GRADED
        submission.graded_at = datetime.utcnow()
        submission.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(submission)
        
        # Send notification to student
        try:
            from app.services.notification_service import AssignmentNotificationService
            notification_service = AssignmentNotificationService(self.db)
            await notification_service.notify_submission_graded(submission)
        except Exception:
            # Don't fail the grading if notifications fail
            pass
        
        return submission

    async def return_submission(
        self,
        submission_id: UUID,
        teacher_id: UUID
    ) -> Submission:
        """Return a graded submission to student."""
        submission = await self.get_submission_by_id(submission_id)
        
        # Check if user is the teacher of this assignment
        if submission.assignment.teacher_id != teacher_id:
            raise InsufficientPermissionError("Only the assignment creator can return submissions")
        
        if submission.status != SubmissionStatus.GRADED:
            raise ValidationError("Only graded submissions can be returned")
        
        submission.status = SubmissionStatus.RETURNED
        submission.returned_at = datetime.utcnow()
        submission.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(submission)
        
        # Send notification to student
        try:
            from app.services.notification_service import AssignmentNotificationService
            notification_service = AssignmentNotificationService(self.db)
            await notification_service.notify_submission_returned(submission)
        except Exception:
            # Don't fail the return if notifications fail
            pass
        
        return submission

    # Permission checking methods

    async def is_assignment_teacher(
        self,
        assignment_id: UUID,
        teacher_id: UUID
    ) -> bool:
        """Check if user is the teacher of an assignment."""
        try:
            assignment = await self.get_assignment_by_id(assignment_id)
            return assignment.teacher_id == teacher_id
        except AssignmentNotFoundError:
            return False

    async def can_student_access_assignment(
        self,
        assignment_id: UUID,
        student_id: UUID
    ) -> bool:
        """Check if student can access an assignment."""
        try:
            assignment = await self.get_assignment_by_id(assignment_id)
            
            # Check if student is enrolled in the assignment's class
            membership_query = select(ClassStudent).where(
                and_(
                    ClassStudent.class_id == assignment.class_id,
                    ClassStudent.student_id == student_id,
                    ClassStudent.is_active == True
                )
            )
            membership_result = await self.db.execute(membership_query)
            membership = membership_result.scalar_one_or_none()
            
            return membership is not None
        except AssignmentNotFoundError:
            return False

    async def can_parent_access_assignment(
        self,
        assignment_id: UUID,
        parent_id: UUID
    ) -> bool:
        """Check if parent can access an assignment (through their children)."""
        # This will be implemented when parent-student relationships are added
        # For now, return False
        return False

    # Helper methods

    async def _verify_teacher_class_permission(
        self,
        teacher_id: UUID,
        class_id: UUID
    ) -> None:
        """Verify teacher has permission to create assignments in a class."""
        class_query = select(Class).where(
            and_(
                Class.id == class_id,
                Class.teacher_id == teacher_id,
                Class.is_active == True
            )
        )
        class_result = await self.db.execute(class_query)
        class_obj = class_result.scalar_one_or_none()
        
        if not class_obj:
            raise InsufficientPermissionError("Teacher does not have permission to create assignments in this class")

    async def _verify_class_access(
        self,
        user_id: UUID,
        class_id: UUID
    ) -> None:
        """Verify user has access to a class."""
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValidationError("User not found")
        
        if user.role == UserRole.TEACHER:
            # Check if teacher owns the class
            class_query = select(Class).where(
                and_(
                    Class.id == class_id,
                    Class.teacher_id == user_id
                )
            )
            class_result = await self.db.execute(class_query)
            class_obj = class_result.scalar_one_or_none()
            
            if not class_obj:
                raise InsufficientPermissionError("Teacher does not have access to this class")
        
        elif user.role == UserRole.STUDENT:
            # Check if student is enrolled in the class
            membership_query = select(ClassStudent).where(
                and_(
                    ClassStudent.class_id == class_id,
                    ClassStudent.student_id == user_id,
                    ClassStudent.is_active == True
                )
            )
            membership_result = await self.db.execute(membership_query)
            membership = membership_result.scalar_one_or_none()
            
            if not membership:
                raise InsufficientPermissionError("Student is not enrolled in this class")
        
        else:
            raise InsufficientPermissionError("User does not have access to this class")

    async def _check_assignment_access_permission(
        self,
        assignment: Assignment,
        user_id: UUID
    ) -> None:
        """Check if user has permission to access an assignment."""
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValidationError("User not found")
        
        # Teacher can access their own assignments
        if assignment.teacher_id == user_id:
            return
        
        # Students can access assignments in their classes
        if user.role == UserRole.STUDENT:
            if await self.can_student_access_assignment(assignment.id, user_id):
                return
        
        # Parents can access assignments their children have
        if user.role == UserRole.PARENT:
            if await self.can_parent_access_assignment(assignment.id, user_id):
                return
        
        raise InsufficientPermissionError("User does not have permission to access this assignment")

    async def _check_submission_access_permission(
        self,
        submission: Submission,
        user_id: UUID
    ) -> None:
        """Check if user has permission to access a submission."""
        user_query = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValidationError("User not found")
        
        # Student can access their own submissions
        if submission.student_id == user_id:
            return
        
        # Teacher can access submissions for their assignments
        if submission.assignment.teacher_id == user_id:
            return
        
        # Parents can access their children's submissions (to be implemented)
        if user.role == UserRole.PARENT:
            # This will be implemented when parent-student relationships are added
            pass
        
        raise InsufficientPermissionError("User does not have permission to access this submission")

    async def _get_student_submission(
        self,
        assignment_id: UUID,
        student_id: UUID
    ) -> Optional[Submission]:
        """Get existing submission for a student and assignment."""
        query = select(Submission).where(
            and_(
                Submission.assignment_id == assignment_id,
                Submission.student_id == student_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()