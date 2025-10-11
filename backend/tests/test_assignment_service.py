"""Tests for assignment service."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AssignmentNotFoundError,
    InsufficientPermissionError,
    ValidationError
)
from app.models.assignment import Assignment, AssignmentStatus, Submission, SubmissionStatus
from app.models.class_model import Class, ClassStudent
from app.models.user import User, UserRole
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate, SubmissionCreate, SubmissionGrade
from app.services.assignment_service import AssignmentService


@pytest.fixture
async def teacher_user(db_session: AsyncSession) -> User:
    """Create a teacher user for testing."""
    teacher = User(
        email="teacher@test.com",
        password_hash="hashed_password",
        name="Test Teacher",
        role=UserRole.TEACHER,
        is_active=True,
        is_verified=True
    )
    db_session.add(teacher)
    await db_session.commit()
    await db_session.refresh(teacher)
    return teacher


@pytest.fixture
async def student_user(db_session: AsyncSession) -> User:
    """Create a student user for testing."""
    student = User(
        email="student@test.com",
        password_hash="hashed_password",
        name="Test Student",
        role=UserRole.STUDENT,
        is_active=True,
        is_verified=True
    )
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)
    return student


@pytest.fixture
async def test_class(db_session: AsyncSession, teacher_user: User) -> Class:
    """Create a test class."""
    test_class = Class(
        name="Test Class",
        description="A test class",
        class_code="TEST123",
        teacher_id=teacher_user.id,
        school="Test School",
        grade="10",
        subject="Math"
    )
    db_session.add(test_class)
    await db_session.commit()
    await db_session.refresh(test_class)
    return test_class


@pytest.fixture
async def enrolled_student(
    db_session: AsyncSession,
    test_class: Class,
    student_user: User
) -> ClassStudent:
    """Enroll student in test class."""
    membership = ClassStudent(
        class_id=test_class.id,
        student_id=student_user.id,
        is_active=True
    )
    db_session.add(membership)
    await db_session.commit()
    await db_session.refresh(membership)
    return membership


@pytest.fixture
async def assignment_service(db_session: AsyncSession) -> AssignmentService:
    """Create assignment service instance."""
    return AssignmentService(db_session)


class TestAssignmentService:
    """Test assignment service methods."""

    async def test_create_assignment_success(
        self,
        assignment_service: AssignmentService,
        teacher_user: User,
        test_class: Class
    ):
        """Test successful assignment creation."""
        assignment_data = AssignmentCreate(
            title="Test Assignment",
            description="A test assignment",
            instructions="Complete the test",
            subject="Math",
            total_points=100,
            due_date=datetime.utcnow() + timedelta(days=7),
            class_id=test_class.id
        )
        
        assignment = await assignment_service.create_assignment(
            teacher_user.id, assignment_data
        )
        
        assert assignment.title == assignment_data.title
        assert assignment.teacher_id == teacher_user.id
        assert assignment.class_id == test_class.id
        assert assignment.status == AssignmentStatus.DRAFT

    async def test_create_assignment_invalid_teacher(
        self,
        assignment_service: AssignmentService,
        student_user: User,
        test_class: Class
    ):
        """Test assignment creation with invalid teacher."""
        assignment_data = AssignmentCreate(
            title="Test Assignment",
            class_id=test_class.id
        )
        
        with pytest.raises(InsufficientPermissionError):
            await assignment_service.create_assignment(
                student_user.id, assignment_data
            )

    async def test_get_assignment_by_id_success(
        self,
        assignment_service: AssignmentService,
        db_session: AsyncSession,
        teacher_user: User,
        test_class: Class
    ):
        """Test successful assignment retrieval."""
        # Create assignment directly in database
        assignment = Assignment(
            title="Test Assignment",
            teacher_id=teacher_user.id,
            class_id=test_class.id,
            status=AssignmentStatus.DRAFT
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)
        
        retrieved_assignment = await assignment_service.get_assignment_by_id(
            assignment.id, teacher_user.id
        )
        
        assert retrieved_assignment.id == assignment.id
        assert retrieved_assignment.title == assignment.title

    async def test_get_assignment_by_id_not_found(
        self,
        assignment_service: AssignmentService
    ):
        """Test assignment retrieval with invalid ID."""
        fake_id = uuid4()
        
        with pytest.raises(AssignmentNotFoundError):
            await assignment_service.get_assignment_by_id(fake_id)

    async def test_update_assignment_success(
        self,
        assignment_service: AssignmentService,
        db_session: AsyncSession,
        teacher_user: User,
        test_class: Class
    ):
        """Test successful assignment update."""
        # Create assignment
        assignment = Assignment(
            title="Original Title",
            teacher_id=teacher_user.id,
            class_id=test_class.id,
            total_points=100
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)
        
        # Update assignment
        update_data = AssignmentUpdate(
            title="Updated Title",
            total_points=150
        )
        
        updated_assignment = await assignment_service.update_assignment(
            assignment.id, teacher_user.id, update_data
        )
        
        assert updated_assignment.title == "Updated Title"
        assert updated_assignment.total_points == 150

    async def test_update_assignment_unauthorized(
        self,
        assignment_service: AssignmentService,
        db_session: AsyncSession,
        teacher_user: User,
        student_user: User,
        test_class: Class
    ):
        """Test assignment update by non-owner."""
        # Create assignment
        assignment = Assignment(
            title="Original Title",
            teacher_id=teacher_user.id,
            class_id=test_class.id
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)
        
        # Try to update with different user
        update_data = AssignmentUpdate(title="Updated Title")
        
        with pytest.raises(InsufficientPermissionError):
            await assignment_service.update_assignment(
                assignment.id, student_user.id, update_data
            )

    async def test_publish_assignment_success(
        self,
        assignment_service: AssignmentService,
        db_session: AsyncSession,
        teacher_user: User,
        test_class: Class
    ):
        """Test successful assignment publishing."""
        # Create draft assignment
        assignment = Assignment(
            title="Test Assignment",
            teacher_id=teacher_user.id,
            class_id=test_class.id,
            status=AssignmentStatus.DRAFT
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)
        
        # Publish assignment
        published_assignment = await assignment_service.publish_assignment(
            assignment.id, teacher_user.id
        )
        
        assert published_assignment.status == AssignmentStatus.ACTIVE
        assert published_assignment.published_at is not None

    async def test_publish_assignment_invalid_status(
        self,
        assignment_service: AssignmentService,
        db_session: AsyncSession,
        teacher_user: User,
        test_class: Class
    ):
        """Test publishing already active assignment."""
        # Create active assignment
        assignment = Assignment(
            title="Test Assignment",
            teacher_id=teacher_user.id,
            class_id=test_class.id,
            status=AssignmentStatus.ACTIVE
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)
        
        # Try to publish again
        with pytest.raises(ValidationError):
            await assignment_service.publish_assignment(
                assignment.id, teacher_user.id
            )

    async def test_get_teacher_assignments(
        self,
        assignment_service: AssignmentService,
        db_session: AsyncSession,
        teacher_user: User,
        test_class: Class
    ):
        """Test getting assignments for teacher."""
        # Create multiple assignments
        assignment1 = Assignment(
            title="Assignment 1",
            teacher_id=teacher_user.id,
            class_id=test_class.id
        )
        assignment2 = Assignment(
            title="Assignment 2",
            teacher_id=teacher_user.id,
            class_id=test_class.id
        )
        db_session.add_all([assignment1, assignment2])
        await db_session.commit()
        
        # Get teacher assignments
        assignments = await assignment_service.get_teacher_assignments(teacher_user.id)
        
        assert len(assignments) == 2
        assignment_titles = [a.title for a in assignments]
        assert "Assignment 1" in assignment_titles
        assert "Assignment 2" in assignment_titles

    async def test_get_student_assignments(
        self,
        assignment_service: AssignmentService,
        db_session: AsyncSession,
        teacher_user: User,
        student_user: User,
        test_class: Class,
        enrolled_student: ClassStudent
    ):
        """Test getting assignments for student."""
        # Create active assignment
        assignment = Assignment(
            title="Student Assignment",
            teacher_id=teacher_user.id,
            class_id=test_class.id,
            status=AssignmentStatus.ACTIVE
        )
        db_session.add(assignment)
        await db_session.commit()
        
        # Get student assignments
        assignments = await assignment_service.get_student_assignments(student_user.id)
        
        assert len(assignments) == 1
        assert assignments[0].title == "Student Assignment"

    async def test_create_submission_success(
        self,
        assignment_service: AssignmentService,
        db_session: AsyncSession,
        teacher_user: User,
        student_user: User,
        test_class: Class,
        enrolled_student: ClassStudent
    ):
        """Test successful submission creation."""
        # Create active assignment
        assignment = Assignment(
            title="Test Assignment",
            teacher_id=teacher_user.id,
            class_id=test_class.id,
            status=AssignmentStatus.ACTIVE,
            total_points=100,
            due_date=datetime.utcnow() + timedelta(days=7)
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)
        
        # Create submission
        submission_data = SubmissionCreate(
            assignment_id=assignment.id,
            content="This is my submission",
            notes="Some notes"
        )
        
        submission = await assignment_service.create_submission(
            student_user.id, submission_data
        )
        
        assert submission.assignment_id == assignment.id
        assert submission.student_id == student_user.id
        assert submission.content == "This is my submission"
        assert submission.status == SubmissionStatus.SUBMITTED

    async def test_create_submission_not_enrolled(
        self,
        assignment_service: AssignmentService,
        db_session: AsyncSession,
        teacher_user: User,
        student_user: User,
        test_class: Class
    ):
        """Test submission creation by non-enrolled student."""
        # Create active assignment
        assignment = Assignment(
            title="Test Assignment",
            teacher_id=teacher_user.id,
            class_id=test_class.id,
            status=AssignmentStatus.ACTIVE
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)
        
        # Try to create submission without enrollment
        submission_data = SubmissionCreate(
            assignment_id=assignment.id,
            content="This is my submission"
        )
        
        with pytest.raises(InsufficientPermissionError):
            await assignment_service.create_submission(
                student_user.id, submission_data
            )

    async def test_grade_submission_success(
        self,
        assignment_service: AssignmentService,
        db_session: AsyncSession,
        teacher_user: User,
        student_user: User,
        test_class: Class
    ):
        """Test successful submission grading."""
        # Create assignment and submission
        assignment = Assignment(
            title="Test Assignment",
            teacher_id=teacher_user.id,
            class_id=test_class.id,
            total_points=100
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)
        
        submission = Submission(
            assignment_id=assignment.id,
            student_id=student_user.id,
            content="Student work",
            status=SubmissionStatus.SUBMITTED,
            max_score=100
        )
        db_session.add(submission)
        await db_session.commit()
        await db_session.refresh(submission)
        
        # Grade submission
        grade_data = SubmissionGrade(
            score=85,
            feedback="Good work!",
            teacher_comments="Well done"
        )
        
        graded_submission = await assignment_service.grade_submission(
            submission.id, teacher_user.id, grade_data
        )
        
        assert graded_submission.score == 85
        assert graded_submission.feedback == "Good work!"
        assert graded_submission.status == SubmissionStatus.GRADED
        assert graded_submission.graded_at is not None

    async def test_grade_submission_unauthorized(
        self,
        assignment_service: AssignmentService,
        db_session: AsyncSession,
        teacher_user: User,
        student_user: User,
        test_class: Class
    ):
        """Test grading by non-teacher."""
        # Create assignment and submission
        assignment = Assignment(
            title="Test Assignment",
            teacher_id=teacher_user.id,
            class_id=test_class.id
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)
        
        submission = Submission(
            assignment_id=assignment.id,
            student_id=student_user.id,
            status=SubmissionStatus.SUBMITTED
        )
        db_session.add(submission)
        await db_session.commit()
        await db_session.refresh(submission)
        
        # Try to grade with wrong user
        grade_data = SubmissionGrade(score=85)
        
        with pytest.raises(InsufficientPermissionError):
            await assignment_service.grade_submission(
                submission.id, student_user.id, grade_data
            )

    async def test_get_assignment_stats(
        self,
        assignment_service: AssignmentService,
        db_session: AsyncSession,
        teacher_user: User,
        student_user: User,
        test_class: Class,
        enrolled_student: ClassStudent
    ):
        """Test getting assignment statistics."""
        # Create assignment
        assignment = Assignment(
            title="Test Assignment",
            teacher_id=teacher_user.id,
            class_id=test_class.id,
            total_points=100
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)
        
        # Create submission
        submission = Submission(
            assignment_id=assignment.id,
            student_id=student_user.id,
            status=SubmissionStatus.GRADED,
            score=85,
            max_score=100
        )
        db_session.add(submission)
        await db_session.commit()
        
        # Get stats
        stats = await assignment_service.get_assignment_stats(
            assignment.id, teacher_user.id
        )
        
        assert stats.total_submissions == 1
        assert stats.graded_submissions == 1
        assert stats.average_score == 85.0
        assert stats.completion_rate == 100.0  # 1 student, 1 submission