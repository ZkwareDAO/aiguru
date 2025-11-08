"""Class and class-related models."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Class(Base):
    """Class model for organizing students and assignments."""
    
    __tablename__ = "classes"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Basic information
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    class_code: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Academic information
    school: Mapped[Optional[str]] = mapped_column(String(200))
    grade: Mapped[Optional[str]] = mapped_column(String(50))
    subject: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Teacher relationship
    teacher_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
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
    teacher: Mapped["User"] = relationship(
        "User",
        back_populates="taught_classes"
    )
    
    # Student memberships
    student_memberships: Mapped[List["ClassStudent"]] = relationship(
        "ClassStudent",
        back_populates="class_",
        cascade="all, delete-orphan"
    )
    
    # Assignments
    assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment",
        back_populates="class_",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Class(id={self.id}, name={self.name}, code={self.class_code})>"
    
    @property
    def student_count(self) -> int:
        """Get the number of students in this class."""
        return len(self.student_memberships)


class ClassStudent(Base):
    """Association table for class-student relationships."""
    
    __tablename__ = "class_students"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Foreign keys
    class_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("classes.id"),
        nullable=False,
        index=True
    )
    student_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Timestamps
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    class_: Mapped["Class"] = relationship(
        "Class",
        back_populates="student_memberships"
    )
    student: Mapped["User"] = relationship(
        "User",
        back_populates="class_memberships"
    )
    
    def __repr__(self) -> str:
        return f"<ClassStudent(class_id={self.class_id}, student_id={self.student_id})>"