"""Tests for the authentication and authorization system."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import auth_manager
from app.core.permissions import Permission, PermissionManager, ResourceType
from app.models.user import User, UserRole
from app.services.user_service import UserService
from app.services.password_service import PasswordService


class TestAuthManager:
    """Test authentication manager."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "test_password_123!"
        
        # Hash password
        hashed = auth_manager.get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 0
        
        # Verify password
        assert auth_manager.verify_password(password, hashed)
        assert not auth_manager.verify_password("wrong_password", hashed)
    
    def test_password_strength_validation(self):
        """Test password strength validation."""
        # Valid password
        is_valid, message = auth_manager.validate_password_strength("StrongPass123!")
        assert is_valid
        assert message == "密码强度符合要求"
        
        # Too short
        is_valid, message = auth_manager.validate_password_strength("Short1!")
        assert not is_valid
        assert "长度" in message
        
        # Missing uppercase
        is_valid, message = auth_manager.validate_password_strength("lowercase123!")
        assert not is_valid
        assert "大写" in message
        
        # Missing lowercase
        is_valid, message = auth_manager.validate_password_strength("UPPERCASE123!")
        assert not is_valid
        assert "小写" in message
        
        # Missing digit
        is_valid, message = auth_manager.validate_password_strength("NoDigits!")
        assert not is_valid
        assert "数字" in message
        
        # Missing special character
        is_valid, message = auth_manager.validate_password_strength("NoSpecial123")
        assert not is_valid
        assert "特殊字符" in message
    
    def test_token_creation_and_verification(self):
        """Test JWT token creation and verification."""
        user_id = str(uuid4())
        email = "test@example.com"
        role = "student"
        
        # Create token pair
        token_response = auth_manager.create_token_pair(user_id, email, role)
        
        assert token_response.access_token
        assert token_response.refresh_token
        assert token_response.token_type == "bearer"
        assert token_response.expires_in > 0
        
        # Verify access token
        token_data = auth_manager.verify_token(token_response.access_token)
        assert token_data is not None
        assert token_data.user_id == user_id
        assert token_data.email == email
        assert token_data.role == role
        
        # Verify refresh token
        refresh_data = auth_manager.verify_token(
            token_response.refresh_token, 
            token_type="refresh"
        )
        assert refresh_data is not None
        assert refresh_data.user_id == user_id
    
    def test_invalid_token_verification(self):
        """Test verification of invalid tokens."""
        # Invalid token
        token_data = auth_manager.verify_token("invalid_token")
        assert token_data is None
        
        # Wrong token type
        user_id = str(uuid4())
        token_response = auth_manager.create_token_pair(user_id, "test@example.com", "student")
        
        # Try to verify access token as refresh token
        token_data = auth_manager.verify_token(
            token_response.access_token, 
            token_type="refresh"
        )
        assert token_data is None


@pytest.mark.asyncio
class TestUserService:
    """Test user service."""
    
    async def test_create_user(self, db_session: AsyncSession):
        """Test user creation."""
        user_service = UserService(db_session)
        
        from app.schemas.user import UserCreate
        user_data = UserCreate(
            email="test@example.com",
            password="StrongPass123!",
            name="Test User",
            role=UserRole.STUDENT,
            school="Test School",
            grade="Grade 1"
        )
        
        user = await user_service.create_user(user_data)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.role == UserRole.STUDENT
        assert user.school == "Test School"
        assert user.grade == "Grade 1"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.password_hash != "StrongPass123!"
    
    async def test_create_duplicate_user(self, db_session: AsyncSession):
        """Test creating user with duplicate email."""
        user_service = UserService(db_session)
        
        from app.schemas.user import UserCreate
        user_data = UserCreate(
            email="duplicate@example.com",
            password="StrongPass123!",
            name="Test User",
            role=UserRole.STUDENT
        )
        
        # Create first user
        await user_service.create_user(user_data)
        
        # Try to create duplicate
        with pytest.raises(ValueError, match="邮箱已被注册"):
            await user_service.create_user(user_data)
    
    async def test_authenticate_user(self, db_session: AsyncSession):
        """Test user authentication."""
        user_service = UserService(db_session)
        
        from app.schemas.user import UserCreate
        user_data = UserCreate(
            email="auth@example.com",
            password="StrongPass123!",
            name="Auth User",
            role=UserRole.STUDENT
        )
        
        # Create user
        created_user = await user_service.create_user(user_data)
        
        # Authenticate with correct credentials
        authenticated_user = await user_service.authenticate_user(
            "auth@example.com", 
            "StrongPass123!"
        )
        assert authenticated_user is not None
        assert authenticated_user.id == created_user.id
        
        # Authenticate with wrong password
        authenticated_user = await user_service.authenticate_user(
            "auth@example.com", 
            "WrongPassword"
        )
        assert authenticated_user is None
        
        # Authenticate with wrong email
        authenticated_user = await user_service.authenticate_user(
            "wrong@example.com", 
            "StrongPass123!"
        )
        assert authenticated_user is None
    
    async def test_change_password(self, db_session: AsyncSession):
        """Test password change."""
        user_service = UserService(db_session)
        
        from app.schemas.user import UserCreate
        user_data = UserCreate(
            email="changepass@example.com",
            password="OldPass123!",
            name="Change Pass User",
            role=UserRole.STUDENT
        )
        
        # Create user
        user = await user_service.create_user(user_data)
        
        # Change password with correct old password
        success = await user_service.change_password(
            user.id,
            "OldPass123!",
            "NewPass456!"
        )
        assert success is True
        
        # Verify new password works
        authenticated_user = await user_service.authenticate_user(
            "changepass@example.com",
            "NewPass456!"
        )
        assert authenticated_user is not None
        
        # Verify old password doesn't work
        authenticated_user = await user_service.authenticate_user(
            "changepass@example.com",
            "OldPass123!"
        )
        assert authenticated_user is None
        
        # Try to change with wrong old password
        success = await user_service.change_password(
            user.id,
            "WrongOldPass",
            "AnotherNewPass789!"
        )
        assert success is False


@pytest.mark.asyncio
class TestPasswordService:
    """Test password service."""
    
    async def test_password_strength_score(self, db_session: AsyncSession):
        """Test password strength scoring."""
        password_service = PasswordService(db_session)
        
        # Strong password
        result = await password_service.get_password_strength_score("StrongPass123!")
        assert result["score"] >= 80
        assert result["strength"] == "强"
        assert len(result["recommendations"]) == 0
        
        # Weak password
        result = await password_service.get_password_strength_score("weak")
        assert result["score"] < 40
        assert result["strength"] == "很弱"
        assert len(result["recommendations"]) > 0
    
    async def test_password_compromise_check(self, db_session: AsyncSession):
        """Test password compromise checking."""
        password_service = PasswordService(db_session)
        
        # Common password
        is_compromised = await password_service.is_password_compromised("password")
        assert is_compromised is True
        
        # Unique password
        is_compromised = await password_service.is_password_compromised("UniquePass123!")
        assert is_compromised is False
    
    async def test_secure_password_generation(self, db_session: AsyncSession):
        """Test secure password generation."""
        password_service = PasswordService(db_session)
        
        # Generate password
        password = await password_service.generate_secure_password(12)
        
        assert len(password) == 12
        
        # Check strength
        result = await password_service.get_password_strength_score(password)
        assert result["score"] >= 80  # Should be strong


class TestPermissionManager:
    """Test permission manager."""
    
    def test_role_permissions(self):
        """Test role-based permissions."""
        # Create mock users
        student = User(role=UserRole.STUDENT)
        teacher = User(role=UserRole.TEACHER)
        parent = User(role=UserRole.PARENT)
        
        permission_manager = PermissionManager(None)  # No DB needed for basic tests
        
        # Test student permissions
        assert permission_manager.has_permission(student, Permission.USER_READ)
        assert permission_manager.has_permission(student, Permission.CLASS_READ)
        assert not permission_manager.has_permission(student, Permission.CLASS_WRITE)
        assert not permission_manager.has_permission(student, Permission.ASSIGNMENT_GRADE)
        
        # Test teacher permissions
        assert permission_manager.has_permission(teacher, Permission.USER_READ)
        assert permission_manager.has_permission(teacher, Permission.CLASS_WRITE)
        assert permission_manager.has_permission(teacher, Permission.ASSIGNMENT_GRADE)
        assert permission_manager.has_permission(teacher, Permission.AI_GRADING_USE)
        
        # Test parent permissions
        assert permission_manager.has_permission(parent, Permission.USER_READ)
        assert permission_manager.has_permission(parent, Permission.CLASS_READ)
        assert not permission_manager.has_permission(parent, Permission.CLASS_WRITE)
        assert not permission_manager.has_permission(parent, Permission.ASSIGNMENT_GRADE)
    
    def test_permission_combinations(self):
        """Test permission combination checks."""
        teacher = User(role=UserRole.TEACHER)
        permission_manager = PermissionManager(None)
        
        # Test has_any_permission
        assert permission_manager.has_any_permission(
            teacher, 
            [Permission.CLASS_WRITE, Permission.SYSTEM_ADMIN]
        )
        
        assert not permission_manager.has_any_permission(
            teacher, 
            [Permission.SYSTEM_ADMIN, Permission.SYSTEM_CONFIG]
        )
        
        # Test has_all_permissions
        assert permission_manager.has_all_permissions(
            teacher,
            [Permission.USER_READ, Permission.CLASS_READ, Permission.ASSIGNMENT_READ]
        )
        
        assert not permission_manager.has_all_permissions(
            teacher,
            [Permission.USER_READ, Permission.SYSTEM_ADMIN]
        )


@pytest.mark.asyncio
class TestAuthAPI:
    """Test authentication API endpoints."""
    
    async def test_register_endpoint(self, client: TestClient):
        """Test user registration endpoint."""
        response = client.post("/auth/register", json={
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "name": "New User",
            "role": "student",
            "school": "Test School"
        })
        
        assert response.status_code == 201
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["name"] == "New User"
    
    async def test_login_endpoint(self, client: TestClient):
        """Test user login endpoint."""
        # First register a user
        client.post("/auth/register", json={
            "email": "loginuser@example.com",
            "password": "StrongPass123!",
            "name": "Login User",
            "role": "student"
        })
        
        # Then login
        response = client.post("/auth/login", json={
            "email": "loginuser@example.com",
            "password": "StrongPass123!"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "loginuser@example.com"
    
    async def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials."""
        response = client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "WrongPassword"
        })
        
        assert response.status_code == 401
        assert "邮箱或密码错误" in response.json()["detail"]
    
    async def test_protected_endpoint_without_token(self, client: TestClient):
        """Test accessing protected endpoint without token."""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    async def test_protected_endpoint_with_token(self, client: TestClient):
        """Test accessing protected endpoint with valid token."""
        # Register and get token
        register_response = client.post("/auth/register", json={
            "email": "protected@example.com",
            "password": "StrongPass123!",
            "name": "Protected User",
            "role": "student"
        })
        
        token = register_response.json()["access_token"]
        
        # Access protected endpoint
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "protected@example.com"