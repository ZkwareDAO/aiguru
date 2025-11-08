"""AI-related models for grading and chat functionality."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GradingTaskStatus(str, Enum):
    """Grading task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(str, Enum):
    """Chat message type enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class GradingTask(Base):
    """AI grading task model for tracking grading progress."""
    
    __tablename__ = "grading_tasks"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign key
    submission_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("submissions.id"),
        nullable=False,
        index=True
    )
    
    # Task information
    task_type: Mapped[str] = mapped_column(String(50), default="auto_grade", nullable=False)
    status: Mapped[GradingTaskStatus] = mapped_column(
        String(20),
        default=GradingTaskStatus.PENDING,
        nullable=False,
        index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Processing details
    ai_model: Mapped[Optional[str]] = mapped_column(String(100))
    prompt_template: Mapped[Optional[str]] = mapped_column(Text)
    
    # Results
    result: Mapped[Optional[dict]] = mapped_column(JSON)
    score: Mapped[Optional[int]] = mapped_column(Integer)
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    suggestions: Mapped[Optional[str]] = mapped_column(Text)
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    submission: Mapped["Submission"] = relationship(
        "Submission",
        back_populates="grading_tasks"
    )
    
    def __repr__(self) -> str:
        return f"<GradingTask(id={self.id}, submission_id={self.submission_id}, status={self.status})>"
    
    @property
    def is_pending(self) -> bool:
        """Check if task is pending."""
        return self.status == GradingTaskStatus.PENDING
    
    @property
    def is_processing(self) -> bool:
        """Check if task is processing."""
        return self.status == GradingTaskStatus.PROCESSING
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.status == GradingTaskStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if task has failed."""
        return self.status == GradingTaskStatus.FAILED
    
    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.is_failed and self.retry_count < self.max_retries
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Get task duration in seconds."""
        if not self.started_at or not self.completed_at:
            return None
        delta = self.completed_at - self.started_at
        return int(delta.total_seconds())


class ChatMessage(Base):
    """Chat message model for AI assistant conversations."""
    
    __tablename__ = "chat_messages"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign key
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Message content
    message_type: Mapped[MessageType] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Context and metadata
    context_data: Mapped[Optional[dict]] = mapped_column(JSON)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    
    # AI model information
    ai_model: Mapped[Optional[str]] = mapped_column(String(100))
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Response metadata
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    confidence_score: Mapped[Optional[float]] = mapped_column()
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="chat_messages"
    )
    
    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, user_id={self.user_id}, type={self.message_type})>"
    
    @property
    def is_user_message(self) -> bool:
        """Check if message is from user."""
        return self.message_type == MessageType.USER
    
    @property
    def is_assistant_message(self) -> bool:
        """Check if message is from assistant."""
        return self.message_type == MessageType.ASSISTANT
    
    @property
    def is_system_message(self) -> bool:
        """Check if message is a system message."""
        return self.message_type == MessageType.SYSTEM
    
    @property
    def content_preview(self) -> str:
        """Get a preview of the message content."""
        if len(self.content) <= 100:
            return self.content
        return self.content[:97] + "..."