"""Assignment and submission models."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AssignmentStatus(str, Enum):
    """Assignment status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class SubmissionStatus(str, Enum):
    """Submission status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    GRADING = "grading"
    GRADED = "graded"
    RETURNED = "returned"


class Assignment(Base):
    """Assignment model for homework and tasks."""
    
    __tablename__ = "assignments"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Basic information
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    
    # Academic information
    subject: Mapped[Optional[str]] = mapped_column(String(100))
    topic: Mapped[Optional[str]] = mapped_column(String(200))
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Grading information
    total_points: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    passing_score: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Timing
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Status
    status: Mapped[AssignmentStatus] = mapped_column(
        String(20),
        default=AssignmentStatus.DRAFT,
        nullable=False,
        index=True
    )
    
    # Foreign keys
    teacher_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    class_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("classes.id"),
        nullable=False,
        index=True
    )
    
    # Settings
    allow_late_submission: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_grade: Mapped[bool] = mapped_column(Boolean, default=True)
    show_correct_answers: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    teacher: Mapped["User"] = relationship(
        "User",
        back_populates="created_assignments"
    )
    class_: Mapped["Class"] = relationship(
        "Class",
        back_populates="assignments"
    )
    
    # Submissions
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        back_populates="assignment",
        cascade="all, delete-orphan"
    )
    
    # Assignment files (reference materials, templates, etc.)
    assignment_files: Mapped[List["File"]] = relationship(
        "File",
        foreign_keys="File.assignment_id",
        back_populates="assignment",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Assignment(id={self.id}, title={self.title}, status={self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Check if assignment is active."""
        return self.status == AssignmentStatus.ACTIVE
    
    @property
    def is_overdue(self) -> bool:
        """Check if assignment is overdue."""
        if not self.due_date:
            return False
        return datetime.utcnow() > self.due_date.replace(tzinfo=None)
    
    @property
    def submission_count(self) -> int:
        """Get the number of submissions for this assignment."""
        return len(self.submissions)


class Submission(Base):
    """Submission model for student assignment submissions."""
    
    __tablename__ = "submissions"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign keys
    assignment_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("assignments.id"),
        nullable=False,
        index=True
    )
    student_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Submission content
    content: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Status and grading
    status: Mapped[SubmissionStatus] = mapped_column(
        String(20),
        default=SubmissionStatus.PENDING,
        nullable=False,
        index=True
    )
    score: Mapped[Optional[int]] = mapped_column(Integer)
    max_score: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Feedback
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    teacher_comments: Mapped[Optional[str]] = mapped_column(Text)
    ai_feedback: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timing
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Flags
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    assignment: Mapped["Assignment"] = relationship(
        "Assignment",
        back_populates="submissions"
    )
    student: Mapped["User"] = relationship(
        "User",
        back_populates="submissions"
    )
    
    # Submission files
    files: Mapped[List["File"]] = relationship(
        "File",
        foreign_keys="File.submission_id",
        back_populates="submission",
        cascade="all, delete-orphan"
    )
    
    # Grading tasks
    grading_tasks: Mapped[List["GradingTask"]] = relationship(
        "GradingTask",
        back_populates="submission",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Submission(id={self.id}, assignment_id={self.assignment_id}, student_id={self.student_id})>"
    
    @property
    def is_submitted(self) -> bool:
        """Check if submission has been submitted."""
        return self.status != SubmissionStatus.PENDING
    
    @property
    def is_graded(self) -> bool:
        """Check if submission has been graded."""
        return self.status == SubmissionStatus.GRADED
    
    @property
    def grade_percentage(self) -> Optional[float]:
        """Calculate grade as percentage."""
        if self.score is None or self.max_score is None or self.max_score == 0:
            return None
        return (self.score / self.max_score) * 100