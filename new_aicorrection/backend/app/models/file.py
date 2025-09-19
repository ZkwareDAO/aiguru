"""File storage and management models."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FileType(str, Enum):
    """File type enumeration."""
    IMAGE = "image"
    PDF = "pdf"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    OTHER = "other"


class FileStatus(str, Enum):
    """File processing status enumeration."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"


class File(Base):
    """File model for storing uploaded files and documents."""
    
    __tablename__ = "files"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # File information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[FileType] = mapped_column(String(50), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    # Storage information
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[Optional[str]] = mapped_column(String(500))
    bucket_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Processing information
    status: Mapped[FileStatus] = mapped_column(
        String(20),
        default=FileStatus.UPLOADING,
        nullable=False,
        index=True
    )
    
    # Content extraction
    ocr_text: Mapped[Optional[str]] = mapped_column(Text)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    file_metadata: Mapped[Optional[str]] = mapped_column(Text)  # JSON string
    
    # Security and access
    is_public: Mapped[bool] = mapped_column(default=False, nullable=False)
    access_token: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Foreign keys
    uploaded_by: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Optional associations
    submission_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("submissions.id"),
        index=True
    )
    assignment_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("assignments.id"),
        index=True
    )
    
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
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    uploaded_by_user: Mapped["User"] = relationship(
        "User",
        back_populates="uploaded_files"
    )
    
    submission: Mapped[Optional["Submission"]] = relationship(
        "Submission",
        back_populates="files"
    )
    
    assignment: Mapped[Optional["Assignment"]] = relationship(
        "Assignment",
        back_populates="assignment_files"
    )
    
    shares: Mapped[List["FileShare"]] = relationship(
        "FileShare",
        back_populates="file",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<File(id={self.id}, filename={self.filename}, type={self.file_type})>"
    
    @property
    def is_image(self) -> bool:
        """Check if file is an image."""
        return self.file_type == FileType.IMAGE
    
    @property
    def is_pdf(self) -> bool:
        """Check if file is a PDF."""
        return self.file_type == FileType.PDF
    
    @property
    def is_document(self) -> bool:
        """Check if file is a document."""
        return self.file_type == FileType.DOCUMENT
    
    @property
    def is_ready(self) -> bool:
        """Check if file is ready for use."""
        return self.status == FileStatus.READY
    
    @property
    def has_text_content(self) -> bool:
        """Check if file has extracted text content."""
        return bool(self.ocr_text or self.extracted_text)
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size / (1024 * 1024)
    
    def get_display_name(self) -> str:
        """Get display name for the file."""
        return self.original_name or self.filename


class FileShare(Base):
    """File sharing model for managing file access permissions."""
    
    __tablename__ = "file_shares"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # File reference
    file_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Sharing information
    shared_by: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    shared_with: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
        index=True
    )
    
    # Access control
    access_type: Mapped[str] = mapped_column(
        String(20),
        default="view",
        nullable=False
    )  # view, download, edit
    
    # Sharing settings
    is_public: Mapped[bool] = mapped_column(default=False, nullable=False)
    share_token: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    
    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Usage tracking
    access_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
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
    file: Mapped["File"] = relationship("File", back_populates="shares")
    shared_by_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[shared_by],
        back_populates="shared_files"
    )
    shared_with_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[shared_with],
        back_populates="received_files"
    )
    
    def __repr__(self) -> str:
        return f"<FileShare(id={self.id}, file_id={self.file_id}, access_type={self.access_type})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if share has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def increment_access_count(self):
        """Increment access count and update last accessed time."""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)