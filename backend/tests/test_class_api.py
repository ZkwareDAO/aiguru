"""Tests for class API endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.models.user import User, UserRole


@pytest.fixture
async def teacher_user(db_session):
    """Create a teacher user for testing."""
    teacher = User(
        email="teacher@test.com",
        password_hash="hashed_password",
        name="Test Teacher",
        role=UserRole.TEACHER,
        is_active=True
    )
    db_session.add(teacher)
    await db_session.commit()
    await db_session.refresh(teacher)
    return teacher


@pytest.fixture
async def student_user(db_session):
    """Create a student user for testing."""
    student = User(
        email="student@test.com",
        password_hash="hashed_password",
        name="Test Student",
        role=UserRole.STUDENT,
        is_active=True
    )
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)
    return student


class TestClassAPI:
    """Test class API endpoints."""

    async def test_create_class_success(self, client: AsyncClient, teacher_user):
        """Test successful class creation."""
        class_data = {
            "name": "Math 101",
            "description": "Basic Mathematics",
            "school": "Test School",
            "grade": "Grade 1",
            "subject": "Mathematics"
        }
        
        # Mock authentication
        with client.auth_context(teacher_user):
            response = await client.post("/classes/", json=class_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == class_data["name"]
        assert data["teacher_id"] == str(teacher_user.id)
        assert "class_code" in data

    async def test_create_class_permission_denied(self, client: AsyncClient, student_user):
        """Test class creation with insufficient permissions."""
        class_data = {
            "name": "Math 101",
            "description": "Basic Mathematics"
        }
        
        with client.auth_context(student_user):
            response = await client.post("/classes/", json=class_data)
        
        assert response.status_code == 403

    async def test_get_class_success(self, client: AsyncClient, teacher_user):
        """Test successful class retrieval."""
        # First create a class
        class_data = {
            "name": "Math 101",
            "description": "Basic Mathematics"
        }
        
        with client.auth_context(teacher_user):
            create_response = await client.post("/classes/", json=class_data)
            class_id = create_response.json()["id"]
            
            # Get the class
            response = await client.get(f"/classes/{class_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == class_data["name"]

    async def test_update_class_success(self, client: AsyncClient, teacher_user):
        """Test successful class update."""
        # First create a class
        class_data = {
            "name": "Math 101",
            "description": "Basic Mathematics"
        }
        
        with client.auth_context(teacher_user):
            create_response = await client.post("/classes/", json=class_data)
            class_id = create_response.json()["id"]
            
            # Update the class
            update_data = {"name": "Advanced Math 101"}
            response = await client.put(f"/classes/{class_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Advanced Math 101"

    async def test_join_class_by_code_success(self, client: AsyncClient, teacher_user, student_user):
        """Test student joining class by code."""
        # First create a class
        class_data = {
            "name": "Math 101",
            "description": "Basic Mathematics"
        }
        
        with client.auth_context(teacher_user):
            create_response = await client.post("/classes/", json=class_data)
            class_code = create_response.json()["class_code"]
        
        # Student joins the class
        join_data = {"class_code": class_code}
        
        with client.auth_context(student_user):
            response = await client.post("/classes/join", json=join_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["student_id"] == str(student_user.id)
        assert data["is_active"] is True

    async def test_get_class_stats(self, client: AsyncClient, teacher_user, student_user):
        """Test getting class statistics."""
        # Create class and add student
        class_data = {
            "name": "Math 101",
            "description": "Basic Mathematics"
        }
        
        with client.auth_context(teacher_user):
            create_response = await client.post("/classes/", json=class_data)
            class_id = create_response.json()["id"]
            class_code = create_response.json()["class_code"]
        
        # Student joins
        with client.auth_context(student_user):
            await client.post("/classes/join", json={"class_code": class_code})
        
        # Get stats
        with client.auth_context(teacher_user):
            response = await client.get(f"/classes/{class_id}/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_students"] == 1
        assert data["active_students"] == 1
        assert "participation_rate" in data

    async def test_get_class_analytics(self, client: AsyncClient, teacher_user, student_user):
        """Test getting class analytics."""
        # Create class and add student
        class_data = {
            "name": "Math 101",
            "description": "Basic Mathematics"
        }
        
        with client.auth_context(teacher_user):
            create_response = await client.post("/classes/", json=class_data)
            class_id = create_response.json()["id"]
            class_code = create_response.json()["class_code"]
        
        # Student joins
        with client.auth_context(student_user):
            await client.post("/classes/join", json={"class_code": class_code})
        
        # Get analytics
        with client.auth_context(teacher_user):
            response = await client.get(f"/classes/{class_id}/analytics")
        
        assert response.status_code == 200
        data = response.json()
        assert "basic_stats" in data
        assert "enrollment_trend" in data
        assert "activity_breakdown" in data
        assert "class_info" in data

    async def test_export_class_data(self, client: AsyncClient, teacher_user, student_user):
        """Test exporting class data."""
        # Create class and add student
        class_data = {
            "name": "Math 101",
            "description": "Basic Mathematics"
        }
        
        with client.auth_context(teacher_user):
            create_response = await client.post("/classes/", json=class_data)
            class_id = create_response.json()["id"]
            class_code = create_response.json()["class_code"]
        
        # Student joins
        with client.auth_context(student_user):
            await client.post("/classes/join", json={"class_code": class_code})
        
        # Export data
        with client.auth_context(teacher_user):
            response = await client.get(f"/classes/{class_id}/export")
        
        assert response.status_code == 200
        data = response.json()
        assert "class_info" in data
        assert "students" in data
        assert "statistics" in data
        assert len(data["students"]) == 1

    async def test_get_class_ranking(self, client: AsyncClient, teacher_user, student_user):
        """Test getting class ranking."""
        # Create class and add student
        class_data = {
            "name": "Math 101",
            "description": "Basic Mathematics"
        }
        
        with client.auth_context(teacher_user):
            create_response = await client.post("/classes/", json=class_data)
            class_id = create_response.json()["id"]
            class_code = create_response.json()["class_code"]
        
        # Student joins
        with client.auth_context(student_user):
            await client.post("/classes/join", json={"class_code": class_code})
        
        # Get ranking
        with client.auth_context(teacher_user):
            response = await client.get(f"/classes/{class_id}/ranking")
        
        assert response.status_code == 200
        data = response.json()
        assert "ranking" in data
        assert len(data["ranking"]) == 1
        assert data["ranking"][0]["rank"] == 1

    async def test_regenerate_class_code(self, client: AsyncClient, teacher_user):
        """Test regenerating class code."""
        # Create class
        class_data = {
            "name": "Math 101",
            "description": "Basic Mathematics"
        }
        
        with client.auth_context(teacher_user):
            create_response = await client.post("/classes/", json=class_data)
            class_id = create_response.json()["id"]
            original_code = create_response.json()["class_code"]
            
            # Regenerate code
            response = await client.post(f"/classes/{class_id}/regenerate-code")
        
        assert response.status_code == 200
        data = response.json()
        assert "class_code" in data
        assert data["class_code"] != original_code

    async def test_get_user_classes(self, client: AsyncClient, teacher_user, student_user):
        """Test getting user's classes."""
        # Teacher creates a class
        class_data = {
            "name": "Math 101",
            "description": "Basic Mathematics"
        }
        
        with client.auth_context(teacher_user):
            create_response = await client.post("/classes/", json=class_data)
            class_code = create_response.json()["class_code"]
            
            # Teacher gets their classes
            response = await client.get("/classes/")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "Math 101"
        
        # Student joins and gets their classes
        with client.auth_context(student_user):
            await client.post("/classes/join", json={"class_code": class_code})
            
            response = await client.get("/classes/")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "Math 101"