"""Tests for grading service."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import GradingError, NotFoundError, ValidationError
from app.models.ai import GradingTask, GradingTaskStatus
from app.models.assignment import Assignment, Submission, SubmissionStatus, AssignmentStatus
from app.models.class_model import Class
from app.models.user import User, UserRole
from app.schemas.grading import (
    BatchGradingRequest,
    GradingTaskCreate,
    GradingTaskFilter,
    GradingTaskUpdate
)
from app.services.grading_service import GradingTaskManager


@pytest.fixture
async def grading_manager(db_session: AsyncSession):
    """Create grading task manager."""
    return GradingTaskManager(db_session)


@pytest.fixture
async def test_teacher(db_session: AsyncSession):
    """Create test teacher."""
    teacher = User(
        email="teacher@test.com",
        password_hash="hashed_password",
        name="Test Teacher",
        role=UserRole.TEACHER
    )
    db_session.add(teacher)
    await db_session.commit()
    await db_session.refresh(teacher)
    return teacher


@pytest.fixture
async def test_student(db_session: AsyncSession):
    """Create test student."""
    student = User(
        email="student@test.com",
        password_hash="hashed_password",
        name="Test Student",
        role=UserRole.STUDENT
    )
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)
    return student


@pytest.fixture
async def test_class(db_session: AsyncSession, test_teacher: User):
    """Create test class."""
    test_class = Class(
        name="Test Class",
        teacher_id=test_teacher.id,
        class_code="TEST123",
        subject="Math"
    )
    db_session.add(test_class)
    await db_session.commit()
    await db_session.refresh(test_class)
    return test_class


@pytest.fixture
async def test_assignment(db_session: AsyncSession, test_teacher: User, test_class: Class):
    """Create test assignment."""
    assignment = Assignment(
        title="Test Assignment",
        description="Test assignment description",
        teacher_id=test_teacher.id,
        class_id=test_class.id,
        status=AssignmentStatus.ACTIVE,
        total_points=100
    )
    db_session.add(assignment)
    await db_session.commit()
    await db_session.refresh(assignment)
    return assignment


@pytest.fixture
async def test_submission(
    db_session: AsyncSession,
    test_assignment: Assignment,
    test_student: User
):
    """Create test submission."""
    submission = Submission(
        assignment_id=test_assignment.id,
        student_id=test_student.id,
        content="Test submission content",
        status=SubmissionStatus.SUBMITTED
    )
    db_session.add(submission)
    await db_session.commit()
    await db_session.refresh(submission)
    return submission


class TestGradingTaskManager:
    """Test grading task manager functionality."""
    
    async def test_create_grading_task(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission
    ):
        """Test creating a grading task."""
        task_data = GradingTaskCreate(
            submission_id=test_submission.id,
            task_type="auto_grade",
            ai_model="gpt-4",
            max_retries=3
        )
        
        task = await grading_manager.create_grading_task(task_data)
        
        assert task.submission_id == test_submission.id
        assert task.task_type == "auto_grade"
        assert task.ai_model == "gpt-4"
        assert task.status == GradingTaskStatus.PENDING
        assert task.max_retries == 3
        assert task.retry_count == 0
        assert task.progress == 0
    
    async def test_create_grading_task_nonexistent_submission(
        self,
        grading_manager: GradingTaskManager
    ):
        """Test creating grading task for nonexistent submission."""
        task_data = GradingTaskCreate(
            submission_id=uuid4(),
            task_type="auto_grade"
        )
        
        with pytest.raises(GradingError):
            await grading_manager.create_grading_task(task_data)
    
    async def test_create_duplicate_grading_task(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission
    ):
        """Test creating duplicate grading task returns existing task."""
        task_data = GradingTaskCreate(
            submission_id=test_submission.id,
            task_type="auto_grade"
        )
        
        # Create first task
        task1 = await grading_manager.create_grading_task(task_data)
        
        # Try to create second task for same submission
        task2 = await grading_manager.create_grading_task(task_data)
        
        # Should return the same task
        assert task1.id == task2.id
    
    async def test_get_grading_task(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission
    ):
        """Test getting a grading task."""
        # Create task first
        task_data = GradingTaskCreate(
            submission_id=test_submission.id,
            task_type="auto_grade"
        )
        created_task = await grading_manager.create_grading_task(task_data)
        
        # Get the task
        retrieved_task = await grading_manager.get_grading_task(created_task.id)
        
        assert retrieved_task.id == created_task.id
        assert retrieved_task.submission_id == test_submission.id
    
    async def test_get_nonexistent_grading_task(
        self,
        grading_manager: GradingTaskManager
    ):
        """Test getting nonexistent grading task."""
        with pytest.raises(NotFoundError):
            await grading_manager.get_grading_task(uuid4())
    
    async def test_update_grading_task(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission
    ):
        """Test updating a grading task."""
        # Create task first
        task_data = GradingTaskCreate(
            submission_id=test_submission.id,
            task_type="auto_grade"
        )
        created_task = await grading_manager.create_grading_task(task_data)
        
        # Update the task
        update_data = GradingTaskUpdate(
            status=GradingTaskStatus.PROCESSING,
            progress=50,
            started_at=datetime.utcnow()
        )
        
        updated_task = await grading_manager.update_grading_task(
            created_task.id,
            update_data
        )
        
        assert updated_task.status == GradingTaskStatus.PROCESSING
        assert updated_task.progress == 50
        assert updated_task.started_at is not None
    
    async def test_complete_grading_task(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission
    ):
        """Test completing a grading task."""
        # Create task first
        task_data = GradingTaskCreate(
            submission_id=test_submission.id,
            task_type="auto_grade"
        )
        created_task = await grading_manager.create_grading_task(task_data)
        
        # Complete the task
        update_data = GradingTaskUpdate(
            status=GradingTaskStatus.COMPLETED,
            progress=100,
            score=85,
            feedback="Good work!",
            completed_at=datetime.utcnow()
        )
        
        updated_task = await grading_manager.update_grading_task(
            created_task.id,
            update_data
        )
        
        assert updated_task.status == GradingTaskStatus.COMPLETED
        assert updated_task.progress == 100
        assert updated_task.score == 85
        assert updated_task.feedback == "Good work!"
        assert updated_task.is_completed
    
    async def test_retry_failed_task(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission
    ):
        """Test retrying a failed grading task."""
        # Create and fail a task
        task_data = GradingTaskCreate(
            submission_id=test_submission.id,
            task_type="auto_grade"
        )
        created_task = await grading_manager.create_grading_task(task_data)
        
        # Mark as failed
        update_data = GradingTaskUpdate(
            status=GradingTaskStatus.FAILED,
            error_message="Test error"
        )
        await grading_manager.update_grading_task(created_task.id, update_data)
        
        # Retry the task
        retried_task = await grading_manager.retry_failed_task(created_task.id)
        
        assert retried_task.status == GradingTaskStatus.PENDING
        assert retried_task.retry_count == 1
        assert retried_task.error_message is None
        assert retried_task.can_retry
    
    async def test_retry_task_max_retries_exceeded(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission
    ):
        """Test retrying task that has exceeded max retries."""
        # Create task with low max retries
        task_data = GradingTaskCreate(
            submission_id=test_submission.id,
            task_type="auto_grade",
            max_retries=1
        )
        created_task = await grading_manager.create_grading_task(task_data)
        
        # Fail and retry once
        update_data = GradingTaskUpdate(
            status=GradingTaskStatus.FAILED,
            error_message="Test error"
        )
        await grading_manager.update_grading_task(created_task.id, update_data)
        await grading_manager.retry_failed_task(created_task.id)
        
        # Fail again
        await grading_manager.update_grading_task(created_task.id, update_data)
        
        # Should not be able to retry again
        with pytest.raises(ValidationError):
            await grading_manager.retry_failed_task(created_task.id)
    
    async def test_cancel_task(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission
    ):
        """Test cancelling a grading task."""
        # Create task
        task_data = GradingTaskCreate(
            submission_id=test_submission.id,
            task_type="auto_grade"
        )
        created_task = await grading_manager.create_grading_task(task_data)
        
        # Cancel the task
        cancelled_task = await grading_manager.cancel_task(created_task.id)
        
        assert cancelled_task.status == GradingTaskStatus.CANCELLED
        assert cancelled_task.completed_at is not None
    
    async def test_cancel_completed_task(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission
    ):
        """Test cancelling a completed task should fail."""
        # Create and complete task
        task_data = GradingTaskCreate(
            submission_id=test_submission.id,
            task_type="auto_grade"
        )
        created_task = await grading_manager.create_grading_task(task_data)
        
        update_data = GradingTaskUpdate(
            status=GradingTaskStatus.COMPLETED,
            progress=100
        )
        await grading_manager.update_grading_task(created_task.id, update_data)
        
        # Should not be able to cancel completed task
        with pytest.raises(ValidationError):
            await grading_manager.cancel_task(created_task.id)
    
    async def test_list_grading_tasks(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission
    ):
        """Test listing grading tasks."""
        # Create multiple tasks
        for i in range(3):
            task_data = GradingTaskCreate(
                submission_id=test_submission.id,
                task_type=f"task_type_{i}"
            )
            await grading_manager.create_grading_task(task_data)
        
        # List tasks
        filters = GradingTaskFilter(page=1, size=10)
        task_list = await grading_manager.list_grading_tasks(filters)
        
        assert len(task_list.tasks) >= 3
        assert task_list.total >= 3
        assert task_list.page == 1
        assert task_list.size == 10
    
    async def test_list_grading_tasks_with_filters(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission
    ):
        """Test listing grading tasks with filters."""
        # Create tasks with different statuses
        task_data = GradingTaskCreate(
            submission_id=test_submission.id,
            task_type="auto_grade"
        )
        created_task = await grading_manager.create_grading_task(task_data)
        
        # Update one to completed
        update_data = GradingTaskUpdate(status=GradingTaskStatus.COMPLETED)
        await grading_manager.update_grading_task(created_task.id, update_data)
        
        # Filter by completed status
        filters = GradingTaskFilter(
            status=GradingTaskStatus.COMPLETED,
            page=1,
            size=10
        )
        task_list = await grading_manager.list_grading_tasks(filters)
        
        assert len(task_list.tasks) >= 1
        assert all(task.status == GradingTaskStatus.COMPLETED for task in task_list.tasks)
    
    async def test_create_batch_grading_tasks(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission,
        db_session: AsyncSession,
        test_assignment: Assignment,
        test_student: User
    ):
        """Test creating batch grading tasks."""
        # Create additional submissions
        submissions = [test_submission]
        for i in range(2):
            submission = Submission(
                assignment_id=test_assignment.id,
                student_id=test_student.id,
                content=f"Test submission {i}",
                status=SubmissionStatus.SUBMITTED
            )
            db_session.add(submission)
            submissions.append(submission)
        
        await db_session.commit()
        
        # Create batch request
        batch_request = BatchGradingRequest(
            submission_ids=[s.id for s in submissions],
            task_type="auto_grade"
        )
        
        response = await grading_manager.create_batch_grading_tasks(batch_request)
        
        assert len(response.created_tasks) == 3
        assert len(response.failed_submissions) == 0
        assert response.total_requested == 3
        assert response.total_created == 3
        assert response.estimated_completion_time_minutes is not None
    
    async def test_get_grading_stats(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission
    ):
        """Test getting grading statistics."""
        # Create tasks with different statuses
        task_data = GradingTaskCreate(
            submission_id=test_submission.id,
            task_type="auto_grade"
        )
        created_task = await grading_manager.create_grading_task(task_data)
        
        # Complete one task
        update_data = GradingTaskUpdate(
            status=GradingTaskStatus.COMPLETED,
            started_at=datetime.utcnow() - timedelta(minutes=5),
            completed_at=datetime.utcnow()
        )
        await grading_manager.update_grading_task(created_task.id, update_data)
        
        # Get stats
        stats = await grading_manager.get_grading_stats()
        
        assert stats.total_tasks >= 1
        assert stats.completed_tasks >= 1
        assert stats.success_rate >= 0.0
        assert stats.retry_rate >= 0.0
    
    async def test_cleanup_old_tasks(
        self,
        grading_manager: GradingTaskManager,
        test_submission: Submission,
        db_session: AsyncSession
    ):
        """Test cleaning up old grading tasks."""
        # Create an old completed task
        old_task = GradingTask(
            submission_id=test_submission.id,
            task_type="auto_grade",
            status=GradingTaskStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(days=35),
            updated_at=datetime.utcnow() - timedelta(days=35)
        )
        db_session.add(old_task)
        await db_session.commit()
        
        # Clean up old tasks
        deleted_count = await grading_manager.cleanup_old_tasks(days_old=30)
        
        assert deleted_count >= 1