"""User model and related models."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, Enum):
    """User role enumeration."""
    STUDENT = "student"
    TEACHER = "teacher"
    PARENT = "parent"


class User(Base):
    """User model for students, teachers, and parents."""
    
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile fields
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(String(20), nullable=False, index=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    school: Mapped[Optional[str]] = mapped_column(String(200))
    grade: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Status fields
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
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
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    # Classes taught (for teachers)
    taught_classes: Mapped[List["Class"]] = relationship(
        "Class",
        back_populates="teacher",
        cascade="all, delete-orphan"
    )
    
    # Class memberships (for students)
    class_memberships: Mapped[List["ClassStudent"]] = relationship(
        "ClassStudent",
        back_populates="student",
        cascade="all, delete-orphan"
    )
    
    # Parent relationships (as parent)
    parent_relations: Mapped[List["ParentStudentRelation"]] = relationship(
        "ParentStudentRelation",
        foreign_keys="ParentStudentRelation.parent_id",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    
    # Student relationships (as student)
    student_relations: Mapped[List["ParentStudentRelation"]] = relationship(
        "ParentStudentRelation",
        foreign_keys="ParentStudentRelation.student_id",
        back_populates="student",
        cascade="all, delete-orphan"
    )
    
    # Assignments created (for teachers)
    created_assignments: Mapped[List["Assignment"]] = relationship(
        "Assignment",
        back_populates="teacher",
        cascade="all, delete-orphan"
    )
    
    # Assignment submissions (for students)
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        back_populates="student",
        cascade="all, delete-orphan"
    )
    
    # Files uploaded
    uploaded_files: Mapped[List["File"]] = relationship(
        "File",
        back_populates="uploaded_by_user",
        cascade="all, delete-orphan"
    )
    
    # Chat messages
    chat_messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Notifications
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Learning analytics
    learning_analytics: Mapped[List["LearningAnalytics"]] = relationship(
        "LearningAnalytics",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # File shares (as sharer)
    shared_files: Mapped[List["FileShare"]] = relationship(
        "FileShare",
        foreign_keys="FileShare.shared_by",
        back_populates="shared_by_user",
        cascade="all, delete-orphan"
    )
    
    # File shares (as recipient)
    received_files: Mapped[List["FileShare"]] = relationship(
        "FileShare",
        foreign_keys="FileShare.shared_with",
        back_populates="shared_with_user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def is_student(self) -> bool:
        """Check if user is a student."""
        return self.role == UserRole.STUDENT
    
    @property
    def is_teacher(self) -> bool:
        """Check if user is a teacher."""
        return self.role == UserRole.TEACHER
    
    @property
    def is_parent(self) -> bool:
        """Check if user is a parent."""
        return self.role == UserRole.PARENT


class ParentStudentRelation(Base):
    """Parent-student relationship model."""
    
    __tablename__ = "parent_student_relations"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Foreign keys
    parent_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    student_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Relationship type
    relation_type: Mapped[str] = mapped_column(
        String(20),
        default="parent",
        nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    parent: Mapped["User"] = relationship(
        "User",
        foreign_keys=[parent_id],
        back_populates="parent_relations"
    )
    student: Mapped["User"] = relationship(
        "User",
        foreign_keys=[student_id],
        back_populates="student_relations"
    )
    
    def __repr__(self) -> str:
        return f"<ParentStudentRelation(parent_id={self.parent_id}, student_id={self.student_id})>"