"""Tests for assignment API endpoints."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment, AssignmentStatus
from app.models.class_model import Class, ClassStudent
from app.models.user import User, UserRole
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
async def test_assignment(
    db_session: AsyncSession,
    teacher_user: User,
    test_class: Class
) -> Assignment:
    """Create a test assignment."""
    assignment = Assignment(
        title="Test Assignment",
        description="A test assignment",
        instructions="Complete the test",
        subject="Math",
        total_points=100,
        due_date=datetime.utcnow() + timedelta(days=7),
        teacher_id=teacher_user.id,
        class_id=test_class.id,
        status=AssignmentStatus.DRAFT
    )
    db_session.add(assignment)
    await db_session.commit()
    await db_session.refresh(assignment)
    return assignment


class TestAssignmentAPI:
    """Test assignment API endpoints."""

    async def test_create_assignment_success(
        self,
        client: TestClient,
        db_session: AsyncSession,
        teacher_user: User,
        test_class: Class,
        teacher_token: str
    ):
        """Test successful assignment creation."""
        assignment_data = {
            "title": "New Assignment",
            "description": "A new assignment",
            "instructions": "Complete this assignment",
            "subject": "Math",
            "total_points": 100,
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "class_id": str(test_class.id)
        }
        
        response = client.post(
            "/api/v1/assignments/",
            json=assignment_data,
            headers={"Authorization": f"Bearer {teacher_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == assignment_data["title"]
        assert data["status"] == "draft"
        assert data["teacher_id"] == str(teacher_user.id)

    async def test_create_assignment_unauthorized(
        self,
        client: TestClient,
        student_user: User,
        test_class: Class,
        student_token: str
    ):
        """Test assignment creation by non-teacher fails."""
        assignment_data = {
            "title": "New Assignment",
            "class_id": str(test_class.id)
        }
        
        response = client.post(
            "/api/v1/assignments/",
            json=assignment_data,
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        assert response.status_code == 403

    async def test_get_assignment_success(
        self,
        client: TestClient,
        test_assignment: Assignment,
        teacher_token: str
    ):
        """Test successful assignment retrieval."""
        response = client.get(
            f"/api/v1/assignments/{test_assignment.id}",
            headers={"Authorization": f"Bearer {teacher_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_assignment.id)
        assert data["title"] == test_assignment.title

    async def test_get_assignment_not_found(
        self,
        client: TestClient,
        teacher_token: str
    ):
        """Test assignment retrieval with invalid ID."""
        fake_id = uuid4()
        response = client.get(
            f"/api/v1/assignments/{fake_id}",
            headers={"Authorization": f"Bearer {teacher_token}"}
        )
        
        assert response.status_code == 404

    async def test_update_assignment_success(
        self,
        client: TestClient,
        test_assignment: Assignment,
        teacher_token: str
    ):
        """Test successful assignment update."""
        update_data = {
            "title": "Updated Assignment",
            "total_points": 150
        }
        
        response = client.put(
            f"/api/v1/assignments/{test_assignment.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {teacher_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["total_points"] == update_data["total_points"]

    async def test_publish_assignment_success(
        self,
        client: TestClient,
        test_assignment: Assignment,
        teacher_token: str
    ):
        """Test successful assignment publishing."""
        response = client.post(
            f"/api/v1/assignments/{test_assignment.id}/publish",
            headers={"Authorization": f"Bearer {teacher_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["published_at"] is not None

    async def test_get_teacher_assignments(
        self,
        client: TestClient,
        test_assignment: Assignment,
        teacher_token: str
    ):
        """Test getting assignments for teacher."""
        response = client.get(
            "/api/v1/assignments/",
            headers={"Authorization": f"Bearer {teacher_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(assignment["id"] == str(test_assignment.id) for assignment in data)

    async def test_get_student_assignments(
        self,
        client: TestClient,
        test_assignment: Assignment,
        enrolled_student: ClassStudent,
        student_token: str,
        db_session: AsyncSession
    ):
        """Test getting assignments for student."""
        # First publish the assignment so student can see it
        assignment_service = AssignmentService(db_session)
        await assignment_service.publish_assignment(
            test_assignment.id, test_assignment.teacher_id
        )
        
        response = client.get(
            "/api/v1/assignments/",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(assignment["id"] == str(test_assignment.id) for assignment in data)

    async def test_get_assignment_stats(
        self,
        client: TestClient,
        test_assignment: Assignment,
        teacher_token: str
    ):
        """Test getting assignment statistics."""
        response = client.get(
            f"/api/v1/assignments/{test_assignment.id}/stats",
            headers={"Authorization": f"Bearer {teacher_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_submissions" in data
        assert "completion_rate" in data
        assert data["total_submissions"] == 0  # No submissions yet


class TestSubmissionAPI:
    """Test submission API endpoints."""

    async def test_create_submission_success(
        self,
        client: TestClient,
        test_assignment: Assignment,
        enrolled_student: ClassStudent,
        student_token: str,
        db_session: AsyncSession
    ):
        """Test successful submission creation."""
        # First publish the assignment
        assignment_service = AssignmentService(db_session)
        await assignment_service.publish_assignment(
            test_assignment.id, test_assignment.teacher_id
        )
        
        submission_data = {
            "content": "This is my submission",
            "notes": "Some notes about the submission"
        }
        
        response = client.post(
            f"/api/v1/assignments/{test_assignment.id}/submissions",
            json=submission_data,
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == submission_data["content"]
        assert data["status"] == "submitted"

    async def test_create_submission_unauthorized(
        self,
        client: TestClient,
        test_assignment: Assignment,
        teacher_token: str
    ):
        """Test submission creation by non-student fails."""
        submission_data = {
            "content": "This is my submission"
        }
        
        response = client.post(
            f"/api/v1/assignments/{test_assignment.id}/submissions",
            json=submission_data,
            headers={"Authorization": f"Bearer {teacher_token}"}
        )
        
        assert response.status_code == 403

    async def test_get_assignment_submissions(
        self,
        client: TestClient,
        test_assignment: Assignment,
        teacher_token: str
    ):
        """Test getting submissions for an assignment."""
        response = client.get(
            f"/api/v1/assignments/{test_assignment.id}/submissions",
            headers={"Authorization": f"Bearer {teacher_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# Fixtures for authentication tokens
@pytest.fixture
async def teacher_token(teacher_user: User) -> str:
    """Generate JWT token for teacher user."""
    from app.core.auth import create_access_token
    return create_access_token(data={"sub": str(teacher_user.id)})


@pytest.fixture
async def student_token(student_user: User) -> str:
    """Generate JWT token for student user."""
    from app.core.auth import create_access_token
    return create_access_token(data={"sub": str(student_user.id)})