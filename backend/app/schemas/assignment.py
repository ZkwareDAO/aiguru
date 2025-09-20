"""Assignment-related Pydantic schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.models.assignment import AssignmentStatus, SubmissionStatus


class AssignmentBase(BaseModel):
    """Base assignment schema with common fields."""
    title: str = Field(..., min_length=1, max_length=200, description="Assignment title")
    description: Optional[str] = Field(None, description="Assignment description")
    instructions: Optional[str] = Field(None, description="Assignment instructions")
    subject: Optional[str] = Field(None, max_length=100, description="Subject")
    topic: Optional[str] = Field(None, max_length=200, description="Topic")
    difficulty_level: Optional[str] = Field(None, max_length=20, description="Difficulty level")
    total_points: int = Field(100, ge=1, le=1000, description="Total points for assignment")
    passing_score: Optional[int] = Field(None, ge=0, description="Minimum passing score")
    due_date: Optional[datetime] = Field(None, description="Assignment due date")
    start_date: Optional[datetime] = Field(None, description="Assignment start date")
    allow_late_submission: bool = Field(False, description="Allow late submissions")
    auto_grade: bool = Field(True, description="Enable automatic grading")
    show_correct_answers: bool = Field(False, description="Show correct answers to students")

    @validator('passing_score')
    def validate_passing_score(cls, v, values):
        """Validate passing score is not greater than total points."""
        if v is not None and 'total_points' in values and v > values['total_points']:
            raise ValueError('Passing score cannot be greater than total points')
        return v

    @validator('due_date')
    def validate_due_date(cls, v, values):
        """Validate due date is after start date."""
        if v is not None and 'start_date' in values and values['start_date'] is not None:
            if v <= values['start_date']:
                raise ValueError('Due date must be after start date')
        return v


class AssignmentCreate(AssignmentBase):
    """Schema for creating a new assignment."""
    class_id: UUID = Field(..., description="Class ID for the assignment")


class AssignmentUpdate(BaseModel):
    """Schema for updating assignment information."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    instructions: Optional[str] = None
    subject: Optional[str] = Field(None, max_length=100)
    topic: Optional[str] = Field(None, max_length=200)
    difficulty_level: Optional[str] = Field(None, max_length=20)
    total_points: Optional[int] = Field(None, ge=1, le=1000)
    passing_score: Optional[int] = Field(None, ge=0)
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    allow_late_submission: Optional[bool] = None
    auto_grade: Optional[bool] = None
    show_correct_answers: Optional[bool] = None
    status: Optional[AssignmentStatus] = None


class AssignmentResponse(AssignmentBase):
    """Schema for assignment response."""
    id: UUID
    class_id: UUID
    teacher_id: UUID
    status: AssignmentStatus
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    submission_count: int = 0
    is_overdue: bool = False

    class Config:
        from_attributes = True


class AssignmentWithClass(AssignmentResponse):
    """Schema for assignment with class information."""
    class_name: str
    class_code: str


class AssignmentListResponse(BaseModel):
    """Schema for paginated assignment list."""
    assignments: List[AssignmentResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


class AssignmentStats(BaseModel):
    """Schema for assignment statistics."""
    total_submissions: int
    pending_submissions: int
    graded_submissions: int
    average_score: Optional[float] = None
    completion_rate: float = 0.0
    on_time_submissions: int = 0
    late_submissions: int = 0


class AssignmentTemplate(BaseModel):
    """Schema for assignment template."""
    id: UUID
    name: str
    description: Optional[str] = None
    template_data: dict
    created_by: UUID
    created_at: datetime
    is_public: bool = False

    class Config:
        from_attributes = True


class AssignmentTemplateCreate(BaseModel):
    """Schema for creating assignment template."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    template_data: dict = Field(..., description="Template configuration data")
    is_public: bool = Field(False, description="Make template public")


# Submission schemas

class SubmissionBase(BaseModel):
    """Base submission schema."""
    content: Optional[str] = Field(None, description="Submission text content")
    notes: Optional[str] = Field(None, description="Student notes")


class SubmissionCreate(SubmissionBase):
    """Schema for creating a submission."""
    assignment_id: UUID = Field(..., description="Assignment ID")


class SubmissionUpdate(BaseModel):
    """Schema for updating submission."""
    content: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[SubmissionStatus] = None


class SubmissionResponse(SubmissionBase):
    """Schema for submission response."""
    id: UUID
    assignment_id: UUID
    student_id: UUID
    status: SubmissionStatus
    score: Optional[int] = None
    max_score: Optional[int] = None
    feedback: Optional[str] = None
    teacher_comments: Optional[str] = None
    ai_feedback: Optional[str] = None
    submitted_at: Optional[datetime] = None
    graded_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    is_late: bool = False
    needs_review: bool = False
    created_at: datetime
    updated_at: datetime
    grade_percentage: Optional[float] = None

    class Config:
        from_attributes = True


class SubmissionWithStudent(SubmissionResponse):
    """Schema for submission with student information."""
    student_name: str
    student_email: str


class SubmissionWithAssignment(SubmissionResponse):
    """Schema for submission with assignment information."""
    assignment_title: str
    assignment_due_date: Optional[datetime] = None
    assignment_total_points: int


class SubmissionGrade(BaseModel):
    """Schema for grading a submission."""
    score: int = Field(..., ge=0, description="Score for the submission")
    max_score: Optional[int] = Field(None, ge=1, description="Maximum possible score")
    feedback: Optional[str] = Field(None, description="Teacher feedback")
    teacher_comments: Optional[str] = Field(None, description="Additional teacher comments")
    needs_review: bool = Field(False, description="Mark submission for review")

    @validator('score')
    def validate_score(cls, v, values):
        """Validate score is not greater than max score."""
        if 'max_score' in values and values['max_score'] is not None and v > values['max_score']:
            raise ValueError('Score cannot be greater than maximum score')
        return v


class SubmissionListResponse(BaseModel):
    """Schema for paginated submission list."""
    submissions: List[SubmissionResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


# File attachment schemas

class AssignmentFileResponse(BaseModel):
    """Schema for assignment file response."""
    id: UUID
    filename: str
    original_name: str
    file_type: str
    file_size: int
    file_url: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class SubmissionFileResponse(BaseModel):
    """Schema for submission file response."""
    id: UUID
    filename: str
    original_name: str
    file_type: str
    file_size: int
    file_url: str
    ocr_text: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True