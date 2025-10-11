"""Notification and communication models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NotificationType(str, Enum):
    """Notification type enumeration."""
    ASSIGNMENT_CREATED = "assignment_created"
    ASSIGNMENT_PUBLISHED = "assignment_published"
    ASSIGNMENT_DUE = "assignment_due"
    ASSIGNMENT_DUE_SOON = "assignment_due_soon"
    ASSIGNMENT_OVERDUE = "assignment_overdue"
    SUBMISSION_RECEIVED = "submission_received"
    SUBMISSION_GRADED = "submission_graded"
    SUBMISSION_RETURNED = "submission_returned"
    GRADE_UPDATED = "grade_updated"
    CLASS_ANNOUNCEMENT = "class_announcement"
    SYSTEM_UPDATE = "system_update"
    AI_FEEDBACK = "ai_feedback"
    PARENT_UPDATE = "parent_update"
    REMINDER = "reminder"
    WARNING = "warning"
    ERROR = "error"


class NotificationPriority(str, Enum):
    """Notification priority enumeration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    """Notification model for user communications."""
    
    __tablename__ = "notifications"
    
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
    
    # Notification content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Notification metadata
    type: Mapped[NotificationType] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    priority: Mapped[NotificationPriority] = mapped_column(
        String(20),
        default=NotificationPriority.NORMAL,
        nullable=False,
        index=True
    )
    
    # Additional data
    data: Mapped[Optional[dict]] = mapped_column(JSON)
    action_url: Mapped[Optional[str]] = mapped_column(String(500))
    action_text: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Delivery channels
    send_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    send_push: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    send_sms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications"
    )
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type})>"
    
    @property
    def is_unread(self) -> bool:
        """Check if notification is unread."""
        return not self.is_read
    
    @property
    def is_urgent(self) -> bool:
        """Check if notification is urgent."""
        return self.priority == NotificationPriority.URGENT
    
    @property
    def is_high_priority(self) -> bool:
        """Check if notification is high priority."""
        return self.priority in [NotificationPriority.HIGH, NotificationPriority.URGENT]
    
    @property
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at.replace(tzinfo=None)
    
    def mark_as_read(self) -> None:
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
    
    def mark_as_sent(self) -> None:
        """Mark notification as sent."""
        if not self.is_sent:
            self.is_sent = True
            self.sent_at = datetime.utcnow()