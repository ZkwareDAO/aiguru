"""Tests for class service."""

import pytest
from uuid import uuid4

from app.core.exceptions import (
    ClassNotFoundError,
    InsufficientPermissionError,
    StudentAlreadyInClassError,
    StudentNotInClassError,
    ValidationError
)
from app.models.class_model import Class
from app.models.user import User, UserRole
from app.schemas.class_schema import ClassCreate, ClassUpdate
from app.services.class_service import ClassService


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


@pytest.fixture
async def class_service(db_session):
    """Create class service instance."""
    return ClassService(db_session)


@pytest.fixture
def class_create_data():
    """Sample class creation data."""
    return ClassCreate(
        name="Math 101",
        description="Basic Mathematics",
        school="Test School",
        grade="Grade 1",
        subject="Mathematics"
    )


class TestClassService:
    """Test class service functionality."""

    async def test_create_class_success(self, class_service, teacher_user, class_create_data):
        """Test successful class creation."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        assert new_class.name == class_create_data.name
        assert new_class.description == class_create_data.description
        assert new_class.teacher_id == teacher_user.id
        assert new_class.class_code is not None
        assert len(new_class.class_code) == 8
        assert new_class.is_active is True

    async def test_create_class_invalid_teacher(self, class_service, student_user, class_create_data):
        """Test class creation with non-teacher user."""
        with pytest.raises(ValidationError, match="User is not an active teacher"):
            await class_service.create_class(student_user.id, class_create_data)

    async def test_create_class_nonexistent_user(self, class_service, class_create_data):
        """Test class creation with nonexistent user."""
        fake_user_id = uuid4()
        with pytest.raises(ValidationError, match="User is not an active teacher"):
            await class_service.create_class(fake_user_id, class_create_data)

    async def test_get_class_by_id_success(self, class_service, teacher_user, class_create_data):
        """Test successful class retrieval by ID."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        retrieved_class = await class_service.get_class_by_id(new_class.id, teacher_user.id)
        
        assert retrieved_class.id == new_class.id
        assert retrieved_class.name == new_class.name

    async def test_get_class_by_id_not_found(self, class_service, teacher_user):
        """Test class retrieval with nonexistent ID."""
        fake_class_id = uuid4()
        
        with pytest.raises(ClassNotFoundError):
            await class_service.get_class_by_id(fake_class_id, teacher_user.id)

    async def test_get_class_by_code_success(self, class_service, teacher_user, class_create_data):
        """Test successful class retrieval by code."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        retrieved_class = await class_service.get_class_by_code(new_class.class_code)
        
        assert retrieved_class.id == new_class.id
        assert retrieved_class.class_code == new_class.class_code

    async def test_get_class_by_code_not_found(self, class_service):
        """Test class retrieval with nonexistent code."""
        with pytest.raises(ClassNotFoundError):
            await class_service.get_class_by_code("INVALID123")

    async def test_update_class_success(self, class_service, teacher_user, class_create_data):
        """Test successful class update."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        update_data = ClassUpdate(
            name="Updated Math 101",
            description="Updated description"
        )
        
        updated_class = await class_service.update_class(new_class.id, teacher_user.id, update_data)
        
        assert updated_class.name == "Updated Math 101"
        assert updated_class.description == "Updated description"
        assert updated_class.school == class_create_data.school  # Unchanged

    async def test_update_class_permission_denied(self, class_service, teacher_user, student_user, class_create_data):
        """Test class update with insufficient permissions."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        update_data = ClassUpdate(name="Unauthorized Update")
        
        with pytest.raises(InsufficientPermissionError):
            await class_service.update_class(new_class.id, student_user.id, update_data)

    async def test_delete_class_success(self, class_service, teacher_user, class_create_data):
        """Test successful class deletion (soft delete)."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        result = await class_service.delete_class(new_class.id, teacher_user.id)
        
        assert result is True
        
        # Verify class is soft deleted
        deleted_class = await class_service.get_class_by_id(new_class.id)
        assert deleted_class.is_active is False

    async def test_delete_class_permission_denied(self, class_service, teacher_user, student_user, class_create_data):
        """Test class deletion with insufficient permissions."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        with pytest.raises(InsufficientPermissionError):
            await class_service.delete_class(new_class.id, student_user.id)

    async def test_get_teacher_classes(self, class_service, teacher_user, class_create_data):
        """Test getting classes taught by a teacher."""
        # Create multiple classes
        class1 = await class_service.create_class(teacher_user.id, class_create_data)
        
        class_create_data2 = ClassCreate(
            name="Science 101",
            description="Basic Science",
            subject="Science"
        )
        class2 = await class_service.create_class(teacher_user.id, class_create_data2)
        
        classes = await class_service.get_teacher_classes(teacher_user.id)
        
        assert len(classes) == 2
        class_ids = [c.id for c in classes]
        assert class1.id in class_ids
        assert class2.id in class_ids

    async def test_regenerate_class_code(self, class_service, teacher_user, class_create_data):
        """Test class code regeneration."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        original_code = new_class.class_code
        
        new_code = await class_service.regenerate_class_code(new_class.id, teacher_user.id)
        
        assert new_code != original_code
        assert len(new_code) == 8

    async def test_regenerate_class_code_permission_denied(self, class_service, teacher_user, student_user, class_create_data):
        """Test class code regeneration with insufficient permissions."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        with pytest.raises(InsufficientPermissionError):
            await class_service.regenerate_class_code(new_class.id, student_user.id)

    async def test_get_class_stats(self, class_service, teacher_user, class_create_data):
        """Test getting class statistics."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        stats = await class_service.get_class_stats(new_class.id, teacher_user.id)
        
        assert stats.total_students == 0
        assert stats.active_students == 0
        assert stats.total_assignments == 0
        assert stats.participation_rate == 0.0

    async def test_generate_unique_class_code(self, class_service):
        """Test unique class code generation."""
        code1 = await class_service._generate_unique_class_code()
        code2 = await class_service._generate_unique_class_code()
        
        assert code1 != code2
        assert len(code1) == 8
        assert len(code2) == 8
        assert code1.isalnum()
        assert code2.isalnum()

    # Student Management Tests

    async def test_add_student_to_class_success(self, class_service, teacher_user, student_user, class_create_data):
        """Test successfully adding a student to a class."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        membership = await class_service.add_student_to_class(
            new_class.id, student_user.id, teacher_user.id
        )
        
        assert membership.class_id == new_class.id
        assert membership.student_id == student_user.id
        assert membership.is_active is True

    async def test_add_student_permission_denied(self, class_service, teacher_user, student_user, class_create_data):
        """Test adding student with insufficient permissions."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        # Create another student to try adding
        other_student = User(
            email="other@test.com",
            password_hash="hashed",
            name="Other Student",
            role=UserRole.STUDENT,
            is_active=True
        )
        class_service.db.add(other_student)
        await class_service.db.commit()
        await class_service.db.refresh(other_student)
        
        with pytest.raises(InsufficientPermissionError):
            await class_service.add_student_to_class(
                new_class.id, other_student.id, student_user.id  # Student trying to add
            )

    async def test_add_student_already_in_class(self, class_service, teacher_user, student_user, class_create_data):
        """Test adding student who is already in the class."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        # Add student first time
        await class_service.add_student_to_class(
            new_class.id, student_user.id, teacher_user.id
        )
        
        # Try to add again
        with pytest.raises(StudentAlreadyInClassError):
            await class_service.add_student_to_class(
                new_class.id, student_user.id, teacher_user.id
            )

    async def test_join_class_by_code_success(self, class_service, teacher_user, student_user, class_create_data):
        """Test student joining class by code."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        membership = await class_service.join_class_by_code(
            student_user.id, new_class.class_code
        )
        
        assert membership.class_id == new_class.id
        assert membership.student_id == student_user.id
        assert membership.is_active is True

    async def test_join_class_invalid_code(self, class_service, student_user):
        """Test joining class with invalid code."""
        with pytest.raises(ClassNotFoundError):
            await class_service.join_class_by_code(student_user.id, "INVALID123")

    async def test_remove_student_from_class_success(self, class_service, teacher_user, student_user, class_create_data):
        """Test successfully removing student from class."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        # Add student first
        await class_service.add_student_to_class(
            new_class.id, student_user.id, teacher_user.id
        )
        
        # Remove student
        result = await class_service.remove_student_from_class(
            new_class.id, student_user.id, teacher_user.id
        )
        
        assert result is True

    async def test_remove_student_not_in_class(self, class_service, teacher_user, student_user, class_create_data):
        """Test removing student who is not in the class."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        with pytest.raises(StudentNotInClassError):
            await class_service.remove_student_from_class(
                new_class.id, student_user.id, teacher_user.id
            )

    async def test_leave_class_success(self, class_service, teacher_user, student_user, class_create_data):
        """Test student leaving class."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        # Add student first
        await class_service.add_student_to_class(
            new_class.id, student_user.id, teacher_user.id
        )
        
        # Student leaves
        result = await class_service.leave_class(new_class.id, student_user.id)
        
        assert result is True

    async def test_leave_class_not_enrolled(self, class_service, teacher_user, student_user, class_create_data):
        """Test student leaving class they're not enrolled in."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        with pytest.raises(StudentNotInClassError):
            await class_service.leave_class(new_class.id, student_user.id)

    async def test_get_class_students(self, class_service, teacher_user, student_user, class_create_data):
        """Test getting class students."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        # Add student
        await class_service.add_student_to_class(
            new_class.id, student_user.id, teacher_user.id
        )
        
        students = await class_service.get_class_students(new_class.id, teacher_user.id)
        
        assert len(students) == 1
        assert students[0].id == student_user.id

    async def test_get_class_memberships(self, class_service, teacher_user, student_user, class_create_data):
        """Test getting class memberships with details."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        # Add student
        await class_service.add_student_to_class(
            new_class.id, student_user.id, teacher_user.id
        )
        
        memberships = await class_service.get_class_memberships(new_class.id, teacher_user.id)
        
        assert len(memberships) == 1
        assert memberships[0].student_id == student_user.id
        assert memberships[0].student.name == student_user.name

    async def test_get_student_class_history(self, class_service, teacher_user, student_user, class_create_data):
        """Test getting student's class history."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        # Add student
        await class_service.add_student_to_class(
            new_class.id, student_user.id, teacher_user.id
        )
        
        # Student can view their own history
        history = await class_service.get_student_class_history(student_user.id, student_user.id)
        
        assert len(history) == 1
        assert history[0].class_id == new_class.id

    # Analytics Tests

    async def test_get_detailed_class_analytics(self, class_service, teacher_user, student_user, class_create_data):
        """Test getting detailed class analytics."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        # Add student
        await class_service.add_student_to_class(
            new_class.id, student_user.id, teacher_user.id
        )
        
        analytics = await class_service.get_detailed_class_analytics(new_class.id, teacher_user.id)
        
        assert "basic_stats" in analytics
        assert "enrollment_trend" in analytics
        assert "activity_breakdown" in analytics
        assert "class_info" in analytics
        assert analytics["basic_stats"]["total_students"] == 1
        assert analytics["basic_stats"]["active_students"] == 1

    async def test_get_class_performance_summary(self, class_service, teacher_user, class_create_data):
        """Test getting class performance summary."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        performance = await class_service.get_class_performance_summary(new_class.id, teacher_user.id)
        
        assert "class_id" in performance
        assert "class_name" in performance
        assert "performance_metrics" in performance
        assert "recent_activity" in performance
        assert performance["class_name"] == new_class.name

    async def test_export_class_data(self, class_service, teacher_user, student_user, class_create_data):
        """Test exporting class data."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        # Add student
        await class_service.add_student_to_class(
            new_class.id, student_user.id, teacher_user.id
        )
        
        export_data = await class_service.export_class_data(new_class.id, teacher_user.id)
        
        assert "class_info" in export_data
        assert "students" in export_data
        assert "statistics" in export_data
        assert "export_timestamp" in export_data
        assert len(export_data["students"]) == 1
        assert export_data["students"][0]["student_name"] == student_user.name

    async def test_get_class_ranking(self, class_service, teacher_user, student_user, class_create_data):
        """Test getting class ranking."""
        new_class = await class_service.create_class(teacher_user.id, class_create_data)
        
        # Add student
        await class_service.add_student_to_class(
            new_class.id, student_user.id, teacher_user.id
        )
        
        ranking = await class_service.get_class_ranking(new_class.id, teacher_user.id)
        
        assert len(ranking) == 1
        assert ranking[0]["rank"] == 1
        assert ranking[0]["student_name"] == student_user.name
        assert "average_score" in ranking[0]
        assert "completion_rate" in ranking[0]