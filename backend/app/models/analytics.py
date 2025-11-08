"""Learning analytics and performance tracking models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LearningAnalytics(Base):
    """Learning analytics model for tracking student performance."""
    
    __tablename__ = "learning_analytics"
    
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
    
    # Academic context
    subject: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    topic: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    knowledge_point: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Performance metrics
    mastery_level: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),  # 0.00 to 100.00
        default=Decimal('0.00')
    )
    accuracy_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),  # 0.00 to 100.00
        default=Decimal('0.00')
    )
    
    # Activity counters
    total_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    practice_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Time tracking
    total_time_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # in seconds
    average_response_time: Mapped[Optional[int]] = mapped_column(Integer)  # in seconds
    
    # Improvement tracking
    improvement_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    streak_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Additional analytics data
    analytics_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Timestamps
    first_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="learning_analytics"
    )
    
    def __repr__(self) -> str:
        return f"<LearningAnalytics(id={self.id}, user_id={self.user_id}, subject={self.subject})>"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_attempts == 0:
            return 0.0
        return (self.correct_attempts / self.total_attempts) * 100
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.total_attempts == 0:
            return 0.0
        return (self.error_count / self.total_attempts) * 100
    
    @property
    def is_mastered(self) -> bool:
        """Check if knowledge point is mastered (>= 80% mastery)."""
        if not self.mastery_level:
            return False
        return self.mastery_level >= Decimal('80.00')
    
    @property
    def needs_practice(self) -> bool:
        """Check if knowledge point needs more practice (< 60% mastery)."""
        if not self.mastery_level:
            return True
        return self.mastery_level < Decimal('60.00')
    
    @property
    def average_time_per_attempt(self) -> Optional[float]:
        """Calculate average time per attempt in seconds."""
        if self.total_attempts == 0:
            return None
        return self.total_time_spent / self.total_attempts
    
    @property
    def total_time_hours(self) -> float:
        """Get total time spent in hours."""
        return self.total_time_spent / 3600
    
    def update_performance(
        self,
        is_correct: bool,
        time_spent: int,
        difficulty: Optional[str] = None
    ) -> None:
        """Update performance metrics with new attempt data."""
        # Update counters
        self.total_attempts += 1
        if is_correct:
            self.correct_attempts += 1
            self.streak_count += 1
            if self.streak_count > self.best_streak:
                self.best_streak = self.streak_count
        else:
            self.error_count += 1
            self.streak_count = 0
        
        # Update time tracking
        self.total_time_spent += time_spent
        if self.average_response_time is None:
            self.average_response_time = time_spent
        else:
            # Calculate rolling average
            self.average_response_time = int(
                (self.average_response_time * (self.total_attempts - 1) + time_spent) / self.total_attempts
            )
        
        # Update accuracy rate
        self.accuracy_rate = Decimal(str(self.success_rate))
        
        # Update mastery level (weighted by recent performance)
        recent_weight = 0.3  # Give more weight to recent performance
        if self.mastery_level is None:
            self.mastery_level = Decimal('50.00') if is_correct else Decimal('20.00')
        else:
            adjustment = Decimal('10.00') if is_correct else Decimal('-5.00')
            self.mastery_level = max(
                Decimal('0.00'),
                min(Decimal('100.00'), self.mastery_level + adjustment * Decimal(str(recent_weight)))
            )
        
        # Update timestamps
        now = datetime.utcnow()
        if self.first_attempt_at is None:
            self.first_attempt_at = now
        self.last_attempt_at = now
        self.last_updated = now