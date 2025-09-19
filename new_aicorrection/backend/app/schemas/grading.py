"""Schemas for AI grading system."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.models.ai import GradingTaskStatus


class GradingTaskBase(BaseModel):
    """Base schema for grading tasks."""
    
    task_type: str = Field(default="auto_grade", description="Type of grading task")
    ai_model: Optional[str] = Field(None, description="AI model used for grading")
    prompt_template: Optional[str] = Field(None, description="Prompt template for AI")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")


class GradingTaskCreate(GradingTaskBase):
    """Schema for creating a grading task."""
    
    submission_id: UUID = Field(..., description="ID of the submission to grade")
    
    @validator('task_type')
    def validate_task_type(cls, v):
        """Validate task type."""
        allowed_types = ['auto_grade', 'detailed_feedback', 'rubric_grade', 'peer_review']
        if v not in allowed_types:
            raise ValueError(f'Task type must be one of: {allowed_types}')
        return v


class GradingTaskUpdate(BaseModel):
    """Schema for updating a grading task."""
    
    status: Optional[GradingTaskStatus] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    result: Optional[Dict[str, Any]] = None
    score: Optional[int] = Field(None, ge=0)
    feedback: Optional[str] = None
    suggestions: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @validator('progress')
    def validate_progress(cls, v):
        """Validate progress percentage."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Progress must be between 0 and 100')
        return v


class GradingTaskResponse(GradingTaskBase):
    """Schema for grading task response."""
    
    id: UUID
    submission_id: UUID
    status: GradingTaskStatus
    progress: int
    result: Optional[Dict[str, Any]] = None
    score: Optional[int] = None
    feedback: Optional[str] = None
    suggestions: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime
    
    # Computed properties
    is_pending: bool
    is_processing: bool
    is_completed: bool
    is_failed: bool
    can_retry: bool
    duration_seconds: Optional[int] = None
    
    class Config:
        from_attributes = True


class GradingTaskList(BaseModel):
    """Schema for paginated grading task list."""
    
    tasks: List[GradingTaskResponse]
    total: int
    page: int
    size: int
    pages: int


class GradingRequest(BaseModel):
    """Schema for grading request data."""
    
    submission_id: UUID
    assignment_title: str
    assignment_description: Optional[str] = None
    assignment_instructions: Optional[str] = None
    student_answer: str
    rubric: Optional[Dict[str, Any]] = None
    grading_criteria: Optional[List[str]] = None
    max_score: int = Field(default=100, ge=1)
    
    @validator('student_answer')
    def validate_student_answer(cls, v):
        """Validate student answer is not empty."""
        if not v or not v.strip():
            raise ValueError('Student answer cannot be empty')
        return v.strip()


class GradingResult(BaseModel):
    """Schema for AI grading result."""
    
    score: int = Field(..., ge=0, description="Numerical score")
    max_score: int = Field(..., ge=1, description="Maximum possible score")
    percentage: float = Field(..., ge=0, le=100, description="Score as percentage")
    feedback: str = Field(..., description="Detailed feedback")
    suggestions: Optional[str] = Field(None, description="Improvement suggestions")
    strengths: Optional[List[str]] = Field(None, description="Identified strengths")
    weaknesses: Optional[List[str]] = Field(None, description="Areas for improvement")
    rubric_scores: Optional[Dict[str, int]] = Field(None, description="Scores by rubric criteria")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="AI confidence score")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    
    @validator('percentage')
    def validate_percentage(cls, v, values):
        """Validate percentage matches score/max_score."""
        if 'score' in values and 'max_score' in values:
            expected = (values['score'] / values['max_score']) * 100
            if abs(v - expected) > 0.01:  # Allow small floating point differences
                raise ValueError('Percentage must match score/max_score ratio')
        return v


class GradingStats(BaseModel):
    """Schema for grading statistics."""
    
    total_tasks: int
    pending_tasks: int
    processing_tasks: int
    completed_tasks: int
    failed_tasks: int
    average_processing_time_seconds: Optional[float] = None
    success_rate: float = Field(..., ge=0, le=1)
    retry_rate: float = Field(..., ge=0, le=1)


class BatchGradingRequest(BaseModel):
    """Schema for batch grading request."""
    
    submission_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    task_type: str = Field(default="auto_grade")
    priority: int = Field(default=0, ge=0, le=10, description="Task priority (higher = more urgent)")
    
    @validator('submission_ids')
    def validate_unique_submissions(cls, v):
        """Ensure submission IDs are unique."""
        if len(v) != len(set(v)):
            raise ValueError('Submission IDs must be unique')
        return v


class BatchGradingResponse(BaseModel):
    """Schema for batch grading response."""
    
    created_tasks: List[UUID]
    failed_submissions: List[UUID]
    total_requested: int
    total_created: int
    estimated_completion_time_minutes: Optional[int] = None


class GradingTaskFilter(BaseModel):
    """Schema for filtering grading tasks."""
    
    status: Optional[GradingTaskStatus] = None
    task_type: Optional[str] = None
    submission_id: Optional[UUID] = None
    student_id: Optional[UUID] = None
    assignment_id: Optional[UUID] = None
    class_id: Optional[UUID] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    has_errors: Optional[bool] = None
    
    # Pagination
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    
    # Sorting
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", regex="^(asc|desc)$")
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort field."""
        allowed_fields = [
            'created_at', 'updated_at', 'started_at', 'completed_at',
            'status', 'progress', 'score', 'retry_count'
        ]
        if v not in allowed_fields:
            raise ValueError(f'Sort field must be one of: {allowed_fields}')
        return v