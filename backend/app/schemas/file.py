"""File schemas for request/response models."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.file import FileStatus, FileType


class FileBase(BaseModel):
    """Base file schema."""
    filename: str
    original_name: str
    file_type: FileType
    mime_type: str
    file_size: int


class FileResponse(BaseModel):
    """File response schema."""
    id: UUID
    filename: str
    original_name: str
    file_type: FileType
    mime_type: str
    file_size: int
    file_url: str
    status: FileStatus
    is_public: bool
    uploaded_by: UUID
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size / (1024 * 1024)


class FileUploadResponse(BaseModel):
    """File upload response schema."""
    file: FileResponse
    message: str = "文件上传成功"


class FileListResponse(BaseModel):
    """File list response schema."""
    files: List[FileResponse]
    total: int
    total_size_bytes: int
    total_size_mb: float


class FileStats(BaseModel):
    """File statistics schema."""
    total_files: int
    total_size_bytes: int
    total_size_mb: float
    files_by_type: dict


class AvatarUploadResponse(BaseModel):
    """Avatar upload response schema."""
    file: FileResponse
    avatar_url: str
    message: str = "头像上传成功"


class FileDeleteResponse(BaseModel):
    """File delete response schema."""
    message: str = "文件删除成功"


class FileUrlResponse(BaseModel):
    """File URL response schema."""
    file_id: UUID
    file_url: str
    expires_at: Optional[datetime] = None


class FileValidationError(BaseModel):
    """File validation error schema."""
    field: str
    message: str


class BulkFileOperation(BaseModel):
    """Bulk file operation schema."""
    file_ids: List[UUID] = Field(..., min_items=1, max_items=50)
    operation: str = Field(..., pattern="^(delete|make_public|make_private)$")


class FileSearchQuery(BaseModel):
    """File search query schema."""
    query: Optional[str] = Field(None, max_length=100, description="搜索关键词")
    file_type: Optional[FileType] = Field(None, description="文件类型")
    status: Optional[FileStatus] = Field(None, description="文件状态")
    uploaded_after: Optional[datetime] = Field(None, description="上传时间起始")
    uploaded_before: Optional[datetime] = Field(None, description="上传时间结束")
    min_size: Optional[int] = Field(None, ge=0, description="最小文件大小(字节)")
    max_size: Optional[int] = Field(None, ge=0, description="最大文件大小(字节)")
    page: int = Field(default=1, ge=1, description="页码")
    per_page: int = Field(default=20, ge=1, le=100, description="每页数量")


class FileMetadata(BaseModel):
    """File metadata schema."""
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    pages: Optional[int] = None
    author: Optional[str] = None
    title: Optional[str] = None
    created_date: Optional[datetime] = None


class FileProcessingResult(BaseModel):
    """File processing result schema."""
    file_id: UUID
    status: FileStatus
    ocr_text: Optional[str] = None
    extracted_text: Optional[str] = None
    metadata: Optional[FileMetadata] = None
    error_message: Optional[str] = None
    processed_at: datetime


class FileAccessRequest(BaseModel):
    """File access request schema."""
    file_id: UUID
    access_type: str = Field(..., pattern="^(view|download)$")
    expires_in: Optional[int] = Field(None, ge=60, le=86400, description="访问链接有效期(秒)")


class FileShareRequest(BaseModel):
    """File share request schema."""
    file_id: UUID
    share_with_users: Optional[List[UUID]] = Field(None, max_items=50)
    is_public: bool = False
    expires_at: Optional[datetime] = None


class FileShareResponse(BaseModel):
    """File share response schema."""
    file_id: UUID
    share_url: str
    is_public: bool
    expires_at: Optional[datetime] = None
    shared_with: List[UUID] = []