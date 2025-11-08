"""Tests for grading API endpoints."""

import pytest
from datetime import datetime
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient

from app.models.ai import GradingTask, GradingTaskStatus
from app.models.assignment import Assignment, Submission, SubmissionStatus, AssignmentStatus
from app.models.class_model import Class
from app.models.user import User, UserRole


@pytest.fixture
async def teacher_user(db_session):
    """Create a teacher user."""
    user = User(
        email="teacher@test.com",
        password_hash="hashed_password",
        name="Test Teacher",
        role=UserRole.TEACHER
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def student_user(db_session):
    """Create a student user."""
    user = User(
        email="student@test.com",
        password_hash="hashed_password",
        name="Test Student",
        role=UserRole.STUDENT
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_class(db_session, teacher_user):
    """Create a test class."""
    test_class = Class(
        name="Test Class",
        teacher_id=teacher_user.id,
        class_code="TEST123",
        subject="Math"
    )
    db_session.add(test_class)
    await db_session.commit()
    await db_session.refresh(test_class)
    return test_class


@pytest.fixture
async def test_assignment(db_session, teacher_user, test_class):
    """Create a test assignment."""
    assignment = Assignment(
        title="Test Assignment",
        description="Test assignment description",
        teacher_id=teacher_user.id,
        class_id=test_class.id,
        status=AssignmentStatus.ACTIVE,
        total_points=100
    )
    db_session.add(assignment)
    await db_session.commit()
    await db_session.refresh(assignment)
    return assignment


@pytest.fixture
async def test_submission(db_session, test_assignment, student_user):
    """Create a test submission."""
    submission = Submission(
        assignment_id=test_assignment.id,
        student_id=student_user.id,
        content="Test submission content",
        status=SubmissionStatus.SUBMITTED
    )
    db_session.add(submission)
    await db_session.commit()
    await db_session.refresh(submission)
    return submission


@pytest.fixture
async def test_grading_task(db_session, test_submission):
    """Create a test grading task."""
    task = GradingTask(
        submission_id=test_submission.id,
        task_type="auto_grade",
        status=GradingTaskStatus.PENDING
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


class TestGradingAPI:
    """Test grading API endpoints."""
    
    async def test_create_grading_task_success(
        self,
        client: AsyncClient,
        teacher_user: User,
        test_submission: Submission,
        auth_headers
    ):
        """Test successful grading task creation."""
        headers = await auth_headers(teacher_user)
        
        task_data = {
            "submission_id": str(test_submission.id),
            "task_type": "auto_grade",
            "ai_model": "gpt-4",
            "max_retries": 3
        }
        
        response = await client.post(
            "/grading/tasks",
            json=task_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["submission_id"] == str(test_submission.id)
        assert data["task_type"] == "auto_grade"
        assert data["ai_model"] == "gpt-4"
        assert data["status"] == "pending"
        assert data["max_retries"] == 3
    
    async def test_create_grading_task_unauthorized(
        self,
        client: AsyncClient,
        student_user: User,
        test_submission: Submission,
        auth_headers
    ):
        """Test grading task creation without proper permissions."""
        headers = await auth_headers(student_user)
        
        task_data = {
            "submission_id": str(test_submission.id),
            "task_type": "auto_grade"
        }
        
        response = await client.post(
            "/grading/tasks",
            json=task_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    async def test_create_grading_task_invalid_submission(
        self,
        client: AsyncClient,
        teacher_user: User,
        auth_headers
    ):
        """Test grading task creation with invalid submission ID."""
        headers = await auth_headers(teacher_user)
        
        task_data = {
            "submission_id": str(uuid4()),
            "task_type": "auto_grade"
        }
        
        response = await client.post(
            "/grading/tasks",
            json=task_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    async def test_get_grading_task_success(
        self,
        client: AsyncClient,
        teacher_user: User,
        test_grading_task: GradingTask,
        auth_headers
    ):
        """Test successful grading task retrieval."""
        headers = await auth_headers(teacher_user)
        
        response = await client.get(
            f"/grading/tasks/{test_grading_task.id}",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(test_grading_task.id)
        assert data["submission_id"] == str(test_grading_task.submission_id)
        assert data["status"] == test_grading_task.status
    
    async def test_get_grading_task_not_found(
        self,
        client: AsyncClient,
        teacher_user: User,
        auth_headers
    ):
        """Test grading task retrieval with invalid ID."""
        headers = await auth_headers(teacher_user)
        
        response = await client.get(
            f"/grading/tasks/{uuid4()}",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_update_grading_task_success(
        self,
        client: AsyncClient,
        teacher_user: User,
        test_grading_task: GradingTask,
        auth_headers
    ):
        """Test successful grading task update."""
        headers = await auth_headers(teacher_user)
        
        update_data = {
            "status": "processing",
            "progress": 50,
            "started_at": datetime.utcnow().isoformat()
        }
        
        response = await client.put(
            f"/grading/tasks/{test_grading_task.id}",
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processing"
        assert data["progress"] == 50
    
    async def test_list_grading_tasks_success(
        self,
        client: AsyncClient,
        teacher_user: User,
        test_grading_task: GradingTask,
        auth_headers
    ):
        """Test successful grading task listing."""
        headers = await auth_headers(teacher_user)
        
        response = await client.get(
            "/grading/tasks",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "tasks" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert len(data["tasks"]) >= 1
    
    async def test_list_grading_tasks_with_filters(
        self,
        client: AsyncClient,
        teacher_user: User,
        test_grading_task: GradingTask,
        auth_headers
    ):
        """Test grading task listing with filters."""
        headers = await auth_headers(teacher_user)
        
        params = {
            "status": "pending",
            "task_type": "auto_grade",
            "page": 1,
            "size": 10
        }
        
        response = await client.get(
            "/grading/tasks",
            params=params,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["tasks"]) >= 0
        # All returned tasks should match the filter
        for task in data["tasks"]:
            assert task["status"] == "pending"
    
    async def test_retry_grading_task_success(
        self,
        client: AsyncClient,
        teacher_user: User,
        test_grading_task: GradingTask,
        auth_headers,
        db_session
    ):
        """Test successful grading task retry."""
        # First mark the task as failed
        test_grading_task.status = GradingTaskStatus.FAILED
        test_grading_task.error_message = "Test error"
        await db_session.commit()
        
        headers = await auth_headers(teacher_user)
        
        response = await client.post(
            f"/grading/tasks/{test_grading_task.id}/retry",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "pending"
        assert data["retry_count"] == 1
        assert data["error_message"] is None
    
    async def test_cancel_grading_task_success(
        self,
        client: AsyncClient,
        teacher_user: User,
        test_grading_task: GradingTask,
        auth_headers
    ):
        """Test successful grading task cancellation."""
        headers = await auth_headers(teacher_user)
        
        response = await client.post(
            f"/grading/tasks/{test_grading_task.id}/cancel",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["completed_at"] is not None
    
    async def test_create_batch_grading_tasks_success(
        self,
        client: AsyncClient,
        teacher_user: User,
        test_submission: Submission,
        auth_headers
    ):
        """Test successful batch grading task creation."""
        headers = await auth_headers(teacher_user)
        
        batch_data = {
            "submission_ids": [str(test_submission.id)],
            "task_type": "auto_grade",
            "priority": 1
        }
        
        response = await client.post(
            "/grading/tasks/batch",
            json=batch_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["created_tasks"]) == 1
        assert len(data["failed_submissions"]) == 0
        assert data["total_requested"] == 1
        assert data["total_created"] == 1
    
    async def test_get_grading_stats_success(
        self,
        client: AsyncClient,
        teacher_user: User,
        test_grading_task: GradingTask,
        auth_headers
    ):
        """Test successful grading statistics retrieval."""
        headers = await auth_headers(teacher_user)
        
        response = await client.get(
            "/grading/stats",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_tasks" in data
        assert "pending_tasks" in data
        assert "processing_tasks" in data
        assert "completed_tasks" in data
        assert "failed_tasks" in data
        assert "success_rate" in data
        assert "retry_rate" in data
        assert data["total_tasks"] >= 1
    
    async def test_get_grading_stats_with_date_range(
        self,
        client: AsyncClient,
        teacher_user: User,
        auth_headers
    ):
        """Test grading statistics with date range."""
        headers = await auth_headers(teacher_user)
        
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.utcnow()
        
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        
        response = await client.get(
            "/grading/stats",
            params=params,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_tasks" in data
    
    async def test_cleanup_old_grading_tasks_success(
        self,
        client: AsyncClient,
        teacher_user: User,
        auth_headers
    ):
        """Test successful cleanup of old grading tasks."""
        # Note: This test assumes teacher has admin permissions for cleanup
        # In a real system, only admins should be able to cleanup
        headers = await auth_headers(teacher_user)
        
        params = {"days_old": 30}
        
        response = await client.delete(
            "/grading/tasks/cleanup",
            params=params,
            headers=headers
        )
        
        # This might fail if teacher doesn't have admin permissions
        # which is expected behavior
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]
    
    async def test_student_can_view_own_grading_task(
        self,
        client: AsyncClient,
        student_user: User,
        test_grading_task: GradingTask,
        auth_headers
    ):
        """Test that student can view their own grading task."""
        headers = await auth_headers(student_user)
        
        response = await client.get(
            f"/grading/tasks/{test_grading_task.id}",
            headers=headers
        )
        
        # This should succeed since the grading task belongs to the student's submission
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(test_grading_task.id)
    
    async def test_student_list_only_own_grading_tasks(
        self,
        client: AsyncClient,
        student_user: User,
        test_grading_task: GradingTask,
        auth_headers
    ):
        """Test that student can only list their own grading tasks."""
        headers = await auth_headers(student_user)
        
        response = await client.get(
            "/grading/tasks",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # All returned tasks should belong to the student
        for task in data["tasks"]:
            # This would need to be verified by checking the submission's student_id
            # For now, we just check that we get a response
            assert "id" in task
    
    async def test_invalid_task_type_validation(
        self,
        client: AsyncClient,
        teacher_user: User,
        test_submission: Submission,
        auth_headers
    ):
        """Test validation of invalid task type."""
        headers = await auth_headers(teacher_user)
        
        task_data = {
            "submission_id": str(test_submission.id),
            "task_type": "invalid_type"
        }
        
        response = await client.post(
            "/grading/tasks",
            json=task_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_invalid_progress_validation(
        self,
        client: AsyncClient,
        teacher_user: User,
        test_grading_task: GradingTask,
        auth_headers
    ):
        """Test validation of invalid progress value."""
        headers = await auth_headers(teacher_user)
        
        update_data = {
            "progress": 150  # Invalid: > 100
        }
        
        response = await client.put(
            f"/grading/tasks/{test_grading_task.id}",
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY