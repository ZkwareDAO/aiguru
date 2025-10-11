"""User schemas for request/response models."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    school: Optional[str] = Field(None, max_length=200)
    grade: Optional[str] = Field(None, max_length=50)


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password requirements."""
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        return v


class UserUpdate(BaseModel):
    """User update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    school: Optional[str] = Field(None, max_length=200)
    grade: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    email: EmailStr
    name: str
    role: UserRole
    school: Optional[str] = None
    grade: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserRegister(UserCreate):
    """User registration schema."""
    pass


class PasswordChange(BaseModel):
    """Password change schema."""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password requirements."""
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        return v


class PasswordReset(BaseModel):
    """Password reset schema."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema."""
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password requirements."""
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        return v


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenRefresh(BaseModel):
    """Token refresh schema."""
    refresh_token: str = Field(..., min_length=1)


class ParentStudentLink(BaseModel):
    """Parent-student link schema."""
    student_id: UUID
    relation_type: str = Field(default="parent", max_length=20)


class ParentStudentRelationResponse(BaseModel):
    """Parent-student relation response schema."""
    id: UUID
    parent_id: UUID
    student_id: UUID
    relation_type: str
    created_at: datetime
    parent: UserResponse
    student: UserResponse
    
    model_config = {"from_attributes": True}


class UserRelationshipSummary(BaseModel):
    """User relationship summary schema."""
    user_id: UUID
    role: str
    relationships: dict


class RelationshipValidation(BaseModel):
    """Relationship validation response schema."""
    is_valid: bool
    message: str


class TeacherStudentRelation(BaseModel):
    """Teacher-student relation info schema."""
    teacher: UserResponse
    student: UserResponse
    class_name: str
    class_id: UUID
    joined_at: datetime


class UserSearchQuery(BaseModel):
    """User search query schema."""
    query: Optional[str] = Field(None, max_length=100, description="搜索关键词")
    role: Optional[UserRole] = Field(None, description="用户角色")
    is_active: Optional[bool] = Field(None, description="是否激活")
    is_verified: Optional[bool] = Field(None, description="是否验证")
    school: Optional[str] = Field(None, max_length=200, description="学校")
    grade: Optional[str] = Field(None, max_length=50, description="年级")
    page: int = Field(default=1, ge=1, description="页码")
    per_page: int = Field(default=20, ge=1, le=100, description="每页数量")


class UserListResponse(BaseModel):
    """User list response schema."""
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class EmailVerification(BaseModel):
    """Email verification schema."""
    token: str = Field(..., min_length=1)


class FirebaseAuthRequest(BaseModel):
    """Firebase authentication request schema."""
    firebase_token: str = Field(..., min_length=1, description="Firebase ID token")


class FirebaseAuthResponse(BaseModel):
    """Firebase authentication response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    is_new_user: bool = False


class UserProfile(UserResponse):
    """Extended user profile schema."""
    # Add additional profile fields if needed
    pass


class UserStats(BaseModel):
    """User statistics schema."""
    total_users: int
    active_users: int
    inactive_users: int
    verified_users: int
    unverified_users: int
    students: int
    teachers: int
    parents: int


class BulkUserOperation(BaseModel):
    """Bulk user operation schema."""
    user_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    operation: str = Field(..., pattern="^(activate|deactivate|verify)$")


class UserActivityLog(BaseModel):
    """User activity log schema."""
    user_id: UUID
    action: str
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[dict] = None
    
    model_config = {"from_attributes": True}