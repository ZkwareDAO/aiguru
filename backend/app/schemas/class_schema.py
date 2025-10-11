"""Class-related Pydantic schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ClassBase(BaseModel):
    """Base class schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="Class name")
    description: Optional[str] = Field(None, max_length=500, description="Class description")
    school: Optional[str] = Field(None, max_length=200, description="School name")
    grade: Optional[str] = Field(None, max_length=50, description="Grade level")
    subject: Optional[str] = Field(None, max_length=100, description="Subject")


class ClassCreate(ClassBase):
    """Schema for creating a new class."""
    pass


class ClassUpdate(BaseModel):
    """Schema for updating class information."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    school: Optional[str] = Field(None, max_length=200)
    grade: Optional[str] = Field(None, max_length=50)
    subject: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class ClassResponse(ClassBase):
    """Schema for class response."""
    id: UUID
    class_code: str
    teacher_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    student_count: int = 0

    class Config:
        from_attributes = True


class ClassWithTeacher(ClassResponse):
    """Schema for class with teacher information."""
    teacher_name: str
    teacher_email: str


class ClassStudentBase(BaseModel):
    """Base schema for class-student relationship."""
    class_id: UUID
    student_id: UUID


class ClassStudentCreate(BaseModel):
    """Schema for adding student to class."""
    student_id: UUID


class ClassStudentJoin(BaseModel):
    """Schema for student joining class with code."""
    class_code: str = Field(..., min_length=6, max_length=10, description="Class join code")


class ClassStudentResponse(ClassStudentBase):
    """Schema for class-student relationship response."""
    id: UUID
    is_active: bool
    joined_at: datetime
    left_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClassStudentWithInfo(ClassStudentResponse):
    """Schema for class-student with user information."""
    student_name: str
    student_email: str


class ClassStats(BaseModel):
    """Schema for class statistics."""
    total_students: int
    active_students: int
    total_assignments: int
    completed_assignments: int
    average_score: Optional[float] = None
    participation_rate: float = 0.0


class ClassCodeResponse(BaseModel):
    """Schema for class code response."""
    class_code: str
    expires_at: Optional[datetime] = None


class ClassListResponse(BaseModel):
    """Schema for paginated class list."""
    classes: List[ClassResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool