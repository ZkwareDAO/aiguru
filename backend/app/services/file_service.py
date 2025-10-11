"""File service for file upload and management operations."""

import hashlib
import json
import mimetypes
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy import and_, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.file import File, FileStatus, FileType
from app.models.user import User


class FileService:
    """Service class for file operations."""
    
    # Allowed file types and their MIME types
    ALLOWED_IMAGE_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff"
    }
    
    ALLOWED_DOCUMENT_TYPES = {
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-powerpoint": ".ppt",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "text/plain": ".txt",
        "text/csv": ".csv",
        "application/rtf": ".rtf"
    }
    
    ALLOWED_VIDEO_TYPES = {
        "video/mp4": ".mp4",
        "video/avi": ".avi",
        "video/mov": ".mov",
        "video/wmv": ".wmv"
    }
    
    ALLOWED_AUDIO_TYPES = {
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/m4a": ".m4a"
    }
    
    ALLOWED_ARCHIVE_TYPES = {
        "application/zip": ".zip",
        "application/x-rar-compressed": ".rar",
        "application/x-7z-compressed": ".7z"
    }
    
    # File size limits (in bytes)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_AUDIO_SIZE = 20 * 1024 * 1024  # 20MB
    MAX_ARCHIVE_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB
    
    # Avatar image dimensions
    AVATAR_SIZE = (200, 200)
    
    # Security settings
    VIRUS_SCAN_ENABLED = False  # Would integrate with antivirus service
    CONTENT_MODERATION_ENABLED = False  # Would integrate with content moderation service
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self._s3_client = None
        self._setup_storage()
    
    def _setup_storage(self):
        """Setup cloud storage client."""
        if (self.settings.AWS_ACCESS_KEY_ID and 
            self.settings.AWS_SECRET_ACCESS_KEY and 
            self.settings.AWS_S3_BUCKET):
            try:
                self._s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
                    region_name=self.settings.AWS_REGION
                )
            except Exception as e:
                print(f"Warning: Failed to setup S3 client: {e}")
                self._s3_client = None
    
    @property
    def has_cloud_storage(self) -> bool:
        """Check if cloud storage is available."""
        return self._s3_client is not None
    
    def _get_all_allowed_types(self) -> Dict[str, str]:
        """Get all allowed file types."""
        return {
            **self.ALLOWED_IMAGE_TYPES,
            **self.ALLOWED_DOCUMENT_TYPES,
            **self.ALLOWED_VIDEO_TYPES,
            **self.ALLOWED_AUDIO_TYPES,
            **self.ALLOWED_ARCHIVE_TYPES
        }
    
    def _get_file_type(self, mime_type: str) -> FileType:
        """Determine file type from MIME type."""
        if mime_type in self.ALLOWED_IMAGE_TYPES:
            return FileType.IMAGE
        elif mime_type in self.ALLOWED_DOCUMENT_TYPES:
            return FileType.DOCUMENT
        elif mime_type in self.ALLOWED_VIDEO_TYPES:
            return FileType.VIDEO
        elif mime_type in self.ALLOWED_AUDIO_TYPES:
            return FileType.AUDIO
        elif mime_type in self.ALLOWED_ARCHIVE_TYPES:
            return FileType.ARCHIVE
        else:
            return FileType.OTHER
    
    def _get_max_size_for_type(self, file_type: FileType) -> int:
        """Get maximum file size for file type."""
        size_map = {
            FileType.IMAGE: self.MAX_IMAGE_SIZE,
            FileType.DOCUMENT: self.MAX_DOCUMENT_SIZE,
            FileType.VIDEO: self.MAX_VIDEO_SIZE,
            FileType.AUDIO: self.MAX_AUDIO_SIZE,
            FileType.ARCHIVE: self.MAX_ARCHIVE_SIZE,
            FileType.OTHER: self.MAX_DOCUMENT_SIZE
        }
        return size_map.get(file_type, self.MAX_DOCUMENT_SIZE)
    
    def _calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()
    
    def _detect_mime_type(self, filename: str, content: bytes) -> str:
        """Detect MIME type from filename and content."""
        # First try to detect from filename
        mime_type, _ = mimetypes.guess_type(filename)
        
        if mime_type:
            return mime_type
        
        # Fallback to content-based detection for common types
        if content.startswith(b'\xFF\xD8\xFF'):
            return 'image/jpeg'
        elif content.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        elif content.startswith(b'GIF8'):
            return 'image/gif'
        elif content.startswith(b'%PDF'):
            return 'application/pdf'
        elif content.startswith(b'PK\x03\x04'):
            return 'application/zip'
        
        return 'application/octet-stream'
    
    async def _scan_for_malware(self, file_path: str) -> bool:
        """Scan file for malware (placeholder implementation)."""
        if not self.VIRUS_SCAN_ENABLED:
            return True
        
        # TODO: Integrate with antivirus service (e.g., ClamAV, VirusTotal)
        # For now, just check file size and basic patterns
        
        try:
            file_size = os.path.getsize(file_path)
            
            # Reject extremely large files as potentially suspicious
            if file_size > 500 * 1024 * 1024:  # 500MB
                return False
            
            # Basic content checks
            with open(file_path, 'rb') as f:
                content = f.read(1024)  # Read first 1KB
                
                # Check for suspicious patterns
                suspicious_patterns = [
                    b'<script',
                    b'javascript:',
                    b'vbscript:',
                    b'onload=',
                    b'onerror='
                ]
                
                for pattern in suspicious_patterns:
                    if pattern in content.lower():
                        return False
            
            return True
            
        except Exception:
            return False
    
    async def _validate_file(
        self,
        file: UploadFile,
        allowed_types: dict,
        max_size: int,
        is_avatar: bool = False,
        content: Optional[bytes] = None
    ) -> Tuple[bool, str]:
        """Validate uploaded file with enhanced security checks."""
        
        # Basic filename validation
        if not file.filename or len(file.filename) > 255:
            return False, "文件名无效或过长"
        
        # Check for dangerous filename patterns
        dangerous_patterns = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        if any(pattern in file.filename for pattern in dangerous_patterns):
            return False, "文件名包含非法字符"
        
        # Check file size
        if hasattr(file, 'size') and file.size and file.size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            return False, f"文件大小不能超过 {max_size_mb:.1f}MB"
        
        # Read content if not provided
        if content is None:
            content = await file.read()
            await file.seek(0)  # Reset file position
        
        # Check actual file size from content
        if len(content) > max_size:
            max_size_mb = max_size / (1024 * 1024)
            return False, f"文件大小不能超过 {max_size_mb:.1f}MB"
        
        # Detect actual MIME type from content
        actual_mime_type = self._detect_mime_type(file.filename, content)
        
        # Check if detected MIME type matches declared type
        if file.content_type and actual_mime_type != file.content_type:
            # Allow some common variations
            mime_variations = {
                'image/jpg': 'image/jpeg',
                'application/x-pdf': 'application/pdf'
            }
            
            normalized_declared = mime_variations.get(file.content_type, file.content_type)
            normalized_actual = mime_variations.get(actual_mime_type, actual_mime_type)
            
            if normalized_declared != normalized_actual:
                return False, f"文件类型不匹配：声明为 {file.content_type}，实际为 {actual_mime_type}"
        
        # Use actual MIME type for validation
        mime_type_to_check = actual_mime_type
        
        # Check MIME type against allowed types
        if mime_type_to_check not in allowed_types:
            allowed_extensions = ", ".join(allowed_types.values())
            return False, f"不支持的文件类型，支持的格式: {allowed_extensions}"
        
        # Additional validation for avatar images
        if is_avatar and not mime_type_to_check.startswith("image/"):
            return False, "头像必须是图片文件"
        
        # Check for empty files
        if len(content) == 0:
            return False, "文件不能为空"
        
        # Validate image files
        if mime_type_to_check.startswith("image/"):
            try:
                from PIL import Image
                import io
                
                with Image.open(io.BytesIO(content)) as img:
                    # Check image dimensions
                    width, height = img.size
                    
                    if width > 10000 or height > 10000:
                        return False, "图片尺寸过大"
                    
                    if width < 1 or height < 1:
                        return False, "图片尺寸无效"
                    
                    # Check for avatar specific requirements
                    if is_avatar:
                        if width > 2000 or height > 2000:
                            return False, "头像图片尺寸不能超过 2000x2000"
                        
                        if width < 50 or height < 50:
                            return False, "头像图片尺寸不能小于 50x50"
                
            except Exception as e:
                return False, f"图片文件损坏或格式错误: {str(e)}"
        
        return True, "验证通过"
    
    def _generate_filename(self, original_filename: str, file_extension: str) -> str:
        """Generate unique filename."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}{file_extension}"
    
    async def _upload_to_s3(
        self, 
        content: bytes, 
        filename: str, 
        mime_type: str,
        user_id: UUID
    ) -> Tuple[str, str]:
        """Upload file to S3 and return URL and storage path."""
        if not self.has_cloud_storage:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="云存储服务不可用"
            )
        
        try:
            # Create S3 key with user folder structure
            s3_key = f"uploads/{user_id}/{datetime.now().strftime('%Y/%m/%d')}/{filename}"
            
            # Upload to S3
            self._s3_client.put_object(
                Bucket=self.settings.AWS_S3_BUCKET,
                Key=s3_key,
                Body=content,
                ContentType=mime_type,
                ServerSideEncryption='AES256',
                Metadata={
                    'uploaded_by': str(user_id),
                    'upload_time': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Generate file URL
            file_url = f"https://{self.settings.AWS_S3_BUCKET}.s3.{self.settings.AWS_REGION}.amazonaws.com/{s3_key}"
            
            return file_url, s3_key
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="存储桶不存在"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"文件上传失败: {error_code}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件上传失败: {str(e)}"
            )
    
    async def _save_file_locally(self, file: UploadFile, filename: str) -> str:
        """Save file to local storage (fallback implementation)."""
        # Create upload directory structure
        upload_dir = os.path.join("uploads", "local")
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        
        # Save file
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Reset file position for potential reuse
        await file.seek(0)
        
        return file_path
    
    async def _generate_secure_url(
        self, 
        file_id: UUID, 
        expires_in: int = 3600
    ) -> Optional[str]:
        """Generate secure presigned URL for file access."""
        file_record = await self.get_file_by_id(file_id)
        
        if not file_record or not file_record.storage_path:
            return None
        
        if self.has_cloud_storage and file_record.storage_path.startswith('uploads/'):
            try:
                # Generate presigned URL for S3
                url = self._s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.settings.AWS_S3_BUCKET,
                        'Key': file_record.storage_path
                    },
                    ExpiresIn=expires_in
                )
                return url
            except Exception:
                return None
        else:
            # For local files, return the regular URL with access token
            access_token = self._generate_access_token(file_id, expires_in)
            return f"/files/serve/{file_record.filename}?token={access_token}"
    
    def _generate_access_token(self, file_id: UUID, expires_in: int) -> str:
        """Generate access token for file."""
        import jwt
        
        payload = {
            'file_id': str(file_id),
            'exp': datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        }
        
        return jwt.encode(payload, self.settings.SECRET_KEY, algorithm='HS256')
    
    def _verify_access_token(self, token: str) -> Optional[UUID]:
        """Verify access token and return file ID."""
        try:
            import jwt
            
            payload = jwt.decode(token, self.settings.SECRET_KEY, algorithms=['HS256'])
            return UUID(payload['file_id'])
        except Exception:
            return None
    
    def _process_avatar_image(self, file_path: str) -> str:
        """Process avatar image (resize and optimize)."""
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                # Resize to avatar dimensions
                img.thumbnail(self.AVATAR_SIZE, Image.Resampling.LANCZOS)
                
                # Create a square image with white background
                square_img = Image.new("RGB", self.AVATAR_SIZE, (255, 255, 255))
                
                # Center the image
                x = (self.AVATAR_SIZE[0] - img.width) // 2
                y = (self.AVATAR_SIZE[1] - img.height) // 2
                square_img.paste(img, (x, y))
                
                # Save processed image
                processed_path = file_path.replace(".", "_processed.")
                square_img.save(processed_path, "JPEG", quality=85, optimize=True)
                
                return processed_path
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"图片处理失败: {str(e)}"
            )
    
    async def upload_file(
        self,
        file: UploadFile,
        user_id: UUID,
        file_category: str = "general",
        assignment_id: Optional[UUID] = None,
        submission_id: Optional[UUID] = None
    ) -> File:
        """Upload a file with enhanced validation and cloud storage."""
        
        # Determine allowed types and size limits based on category
        if file_category == "avatar":
            allowed_types = self.ALLOWED_IMAGE_TYPES
            max_size = self.MAX_AVATAR_SIZE
            is_avatar = True
        elif file_category == "image":
            allowed_types = self.ALLOWED_IMAGE_TYPES
            max_size = self.MAX_IMAGE_SIZE
            is_avatar = False
        elif file_category == "document":
            allowed_types = self.ALLOWED_DOCUMENT_TYPES
            max_size = self.MAX_DOCUMENT_SIZE
            is_avatar = False
        elif file_category == "video":
            allowed_types = self.ALLOWED_VIDEO_TYPES
            max_size = self.MAX_VIDEO_SIZE
            is_avatar = False
        elif file_category == "audio":
            allowed_types = self.ALLOWED_AUDIO_TYPES
            max_size = self.MAX_AUDIO_SIZE
            is_avatar = False
        else:
            # General file upload - allow all types
            allowed_types = self._get_all_allowed_types()
            max_size = self.MAX_DOCUMENT_SIZE
            is_avatar = False
        
        # Read file content for validation
        content = await file.read()
        await file.seek(0)  # Reset file position
        
        # Enhanced file validation
        is_valid, message = await self._validate_file(
            file, allowed_types, max_size, is_avatar, content
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Detect actual MIME type
        actual_mime_type = self._detect_mime_type(file.filename, content)
        
        # Get file extension
        file_extension = allowed_types.get(actual_mime_type, "")
        if not file_extension:
            # Try to get extension from filename
            _, ext = os.path.splitext(file.filename or "")
            file_extension = ext.lower() if ext else ".bin"
        
        # Generate unique filename
        filename = self._generate_filename(file.filename or "file", file_extension)
        
        # Calculate file hash for deduplication
        file_hash = self._calculate_file_hash(content)
        
        # Check for duplicate files
        existing_file = await self._check_duplicate_file(file_hash, user_id)
        if existing_file:
            return existing_file
        
        # Create initial file record
        file_record = File(
            filename=filename,
            original_name=file.filename or filename,
            file_type=self._get_file_type(actual_mime_type),
            mime_type=actual_mime_type,
            file_size=len(content),
            file_url="",  # Will be set after upload
            storage_path="",  # Will be set after upload
            status=FileStatus.UPLOADING,
            uploaded_by=user_id,
            assignment_id=assignment_id,
            submission_id=submission_id,
            is_public=False
        )
        
        self.db.add(file_record)
        await self.db.commit()
        await self.db.refresh(file_record)
        
        try:
            # Upload to cloud storage or save locally
            if self.has_cloud_storage:
                file_url, storage_path = await self._upload_to_s3(
                    content, filename, actual_mime_type, user_id
                )
            else:
                # Save locally as fallback
                await file.seek(0)
                storage_path = await self._save_file_locally(file, filename)
                file_url = f"/files/serve/{filename}"
            
            # Process avatar image if needed
            if is_avatar and file_record.file_type == FileType.IMAGE:
                storage_path = self._process_avatar_image(storage_path)
                filename = os.path.basename(storage_path)
                file_record.filename = filename
            
            # Scan for malware
            if not self.has_cloud_storage:  # Only scan local files
                is_safe = await self._scan_for_malware(storage_path)
                if not is_safe:
                    # Delete the file and record
                    if os.path.exists(storage_path):
                        os.remove(storage_path)
                    await self.db.delete(file_record)
                    await self.db.commit()
                    
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="文件未通过安全检查"
                    )
            
            # Update file record with final information
            file_record.file_url = file_url
            file_record.storage_path = storage_path
            file_record.status = FileStatus.READY
            file_record.processed_at = datetime.now(timezone.utc)
            
            # Store file metadata
            metadata = await self._extract_file_metadata(content, actual_mime_type)
            if metadata:
                file_record.file_metadata = json.dumps(metadata)
            
            await self.db.commit()
            await self.db.refresh(file_record)
            
            return file_record
            
        except Exception as e:
            # Clean up on error
            file_record.status = FileStatus.ERROR
            await self.db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件上传失败: {str(e)}"
            )
    
    async def _check_duplicate_file(self, file_hash: str, user_id: UUID) -> Optional[File]:
        """Check if file with same hash already exists for user."""
        # For now, we'll skip deduplication to avoid complexity
        # In production, you might want to implement this
        return None
    
    async def _extract_file_metadata(self, content: bytes, mime_type: str) -> Optional[Dict[str, Any]]:
        """Extract metadata from file content."""
        metadata = {}
        
        try:
            if mime_type.startswith("image/"):
                from PIL import Image
                import io
                
                with Image.open(io.BytesIO(content)) as img:
                    metadata.update({
                        "width": img.width,
                        "height": img.height,
                        "format": img.format,
                        "mode": img.mode
                    })
                    
                    # Extract EXIF data if available
                    if hasattr(img, '_getexif') and img._getexif():
                        exif = img._getexif()
                        if exif:
                            metadata["has_exif"] = True
                            # Add specific EXIF fields if needed
            
            elif mime_type == "application/pdf":
                # For PDF files, you could extract page count, title, etc.
                # This would require PyPDF2 or similar library
                metadata["type"] = "pdf"
                metadata["size_bytes"] = len(content)
            
            return metadata if metadata else None
            
        except Exception:
            return None
    
    async def upload_avatar(self, file: UploadFile, user_id: UUID) -> File:
        """Upload user avatar image."""
        return await self.upload_file(file, user_id, "avatar")
    
    async def get_file_by_id(self, file_id: UUID) -> Optional[File]:
        """Get file by ID."""
        result = await self.db.execute(
            select(File).where(File.id == file_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_files(
        self,
        user_id: UUID,
        file_type: Optional[FileType] = None,
        limit: int = 50
    ) -> List[File]:
        """Get files uploaded by user."""
        stmt = select(File).where(
            and_(
                File.uploaded_by == user_id,
                File.status != FileStatus.DELETED
            )
        )
        
        if file_type:
            stmt = stmt.where(File.file_type == file_type)
        
        stmt = stmt.order_by(File.created_at.desc()).limit(limit)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def delete_file(self, file_id: UUID, user_id: UUID) -> bool:
        """Delete file (soft delete)."""
        file_record = await self.get_file_by_id(file_id)
        
        if not file_record:
            return False
        
        # Check if user owns the file
        if file_record.uploaded_by != user_id:
            return False
        
        # Soft delete
        file_record.status = FileStatus.DELETED
        file_record.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        
        # TODO: Delete physical file from storage
        
        return True
    
    async def check_file_access(
        self, 
        file_id: UUID, 
        user_id: UUID, 
        access_type: str = "view"
    ) -> bool:
        """Check if user has access to file."""
        file_record = await self.get_file_by_id(file_id)
        
        if not file_record:
            return False
        
        # Owner always has access
        if file_record.uploaded_by == user_id:
            return True
        
        # Public files can be viewed by anyone
        if file_record.is_public and access_type == "view":
            return True
        
        # Check assignment/submission based access
        if file_record.assignment_id or file_record.submission_id:
            return await self._check_assignment_file_access(
                file_record, user_id, access_type
            )
        
        # TODO: Add more sophisticated permission checking
        # - Shared files
        # - Class-based access
        # - Role-based access
        
        return False
    
    async def _check_assignment_file_access(
        self, 
        file_record: File, 
        user_id: UUID, 
        access_type: str
    ) -> bool:
        """Check access to assignment/submission files."""
        # This would integrate with assignment and class services
        # For now, implement basic logic
        
        if file_record.assignment_id:
            # Assignment files - check if user is teacher or student in class
            # TODO: Implement proper class membership check
            return True
        
        if file_record.submission_id:
            # Submission files - check if user is the student or the teacher
            # TODO: Implement proper submission access check
            return True
        
        return False
    
    async def get_file_url(self, file_id: UUID, user_id: UUID) -> Optional[str]:
        """Get secure file URL with access control."""
        # Check access permissions
        has_access = await self.check_file_access(file_id, user_id, "view")
        if not has_access:
            return None
        
        # Generate secure URL
        return await self._generate_secure_url(file_id)
    
    async def update_user_avatar(self, user_id: UUID, file_id: UUID) -> bool:
        """Update user avatar."""
        # Get file record
        file_record = await self.get_file_by_id(file_id)
        
        if not file_record:
            return False
        
        # Check if user owns the file and it's an image
        if file_record.uploaded_by != user_id or file_record.file_type != FileType.IMAGE:
            return False
        
        # Update user avatar URL
        from app.services.user_service import UserService
        user_service = UserService(self.db)
        
        user = await user_service.get_user_by_id(user_id)
        if not user:
            return False
        
        user.avatar_url = file_record.file_url
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        
        return True
    
    async def share_file(
        self,
        file_id: UUID,
        owner_id: UUID,
        share_with_users: Optional[List[UUID]] = None,
        is_public: bool = False,
        access_type: str = "view",
        expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Share file with specific users or make it public."""
        from app.models.file import FileShare
        
        file_record = await self.get_file_by_id(file_id)
        
        if not file_record or file_record.uploaded_by != owner_id:
            return {"success": False, "error": "文件不存在或无权限"}
        
        try:
            # Update file public status
            file_record.is_public = is_public
            file_record.expires_at = expires_at
            file_record.updated_at = datetime.now(timezone.utc)
            
            share_results = []
            
            if is_public:
                # Create public share
                share_token = self._generate_share_token()
                
                public_share = FileShare(
                    file_id=file_id,
                    shared_by=owner_id,
                    shared_with=None,  # Public share
                    access_type=access_type,
                    is_public=True,
                    share_token=share_token,
                    expires_at=expires_at
                )
                
                self.db.add(public_share)
                share_results.append({
                    "type": "public",
                    "share_token": share_token,
                    "share_url": f"/files/shared/{share_token}"
                })
            
            if share_with_users:
                # Create specific user shares
                for user_id in share_with_users:
                    # Check if share already exists
                    existing_share = await self.db.execute(
                        select(FileShare).where(
                            and_(
                                FileShare.file_id == file_id,
                                FileShare.shared_with == user_id
                            )
                        )
                    )
                    
                    if existing_share.scalar_one_or_none():
                        continue  # Skip if already shared
                    
                    share_token = self._generate_share_token()
                    
                    user_share = FileShare(
                        file_id=file_id,
                        shared_by=owner_id,
                        shared_with=user_id,
                        access_type=access_type,
                        is_public=False,
                        share_token=share_token,
                        expires_at=expires_at
                    )
                    
                    self.db.add(user_share)
                    share_results.append({
                        "type": "user",
                        "user_id": str(user_id),
                        "share_token": share_token
                    })
            
            await self.db.commit()
            
            return {
                "success": True,
                "shares": share_results,
                "message": "文件分享成功"
            }
            
        except Exception as e:
            await self.db.rollback()
            return {"success": False, "error": f"分享失败: {str(e)}"}
    
    def _generate_share_token(self) -> str:
        """Generate unique share token."""
        import secrets
        return secrets.token_urlsafe(32)
    
    async def create_temporary_access_link(
        self,
        file_id: UUID,
        user_id: UUID,
        expires_in: int = 3600
    ) -> Optional[str]:
        """Create temporary access link for file."""
        # Check if user has access to the file
        has_access = await self.check_file_access(file_id, user_id, "view")
        if not has_access:
            return None
        
        # Generate secure temporary URL
        return await self._generate_secure_url(file_id, expires_in)
    
    async def get_file_by_share_token(self, share_token: str) -> Optional[File]:
        """Get file by share token."""
        from app.models.file import FileShare
        
        # Find the share record
        result = await self.db.execute(
            select(FileShare).where(
                and_(
                    FileShare.share_token == share_token,
                    or_(
                        FileShare.expires_at.is_(None),
                        FileShare.expires_at > datetime.now(timezone.utc)
                    )
                )
            )
        )
        
        share = result.scalar_one_or_none()
        if not share:
            return None
        
        # Update access tracking
        share.increment_access_count()
        await self.db.commit()
        
        # Get the file
        return await self.get_file_by_id(share.file_id)
    
    async def check_share_access(
        self,
        share_token: str,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Check if share token is valid and return access info."""
        from app.models.file import FileShare
        
        result = await self.db.execute(
            select(FileShare).where(FileShare.share_token == share_token)
        )
        
        share = result.scalar_one_or_none()
        if not share:
            return {"valid": False, "error": "分享链接不存在"}
        
        # Check expiration
        if share.is_expired:
            return {"valid": False, "error": "分享链接已过期"}
        
        # Check user-specific access
        if not share.is_public and share.shared_with != user_id:
            return {"valid": False, "error": "无权限访问此文件"}
        
        # Get file info
        file_record = await self.get_file_by_id(share.file_id)
        if not file_record:
            return {"valid": False, "error": "文件不存在"}
        
        return {
            "valid": True,
            "file_id": str(share.file_id),
            "access_type": share.access_type,
            "is_public": share.is_public,
            "expires_at": share.expires_at.isoformat() if share.expires_at else None,
            "file_info": {
                "name": file_record.original_name,
                "type": file_record.file_type,
                "size": file_record.file_size
            }
        }
    
    async def get_file_shares(self, file_id: UUID, owner_id: UUID) -> List[Dict[str, Any]]:
        """Get all shares for a file."""
        from app.models.file import FileShare
        
        file_record = await self.get_file_by_id(file_id)
        if not file_record or file_record.uploaded_by != owner_id:
            return []
        
        result = await self.db.execute(
            select(FileShare).where(FileShare.file_id == file_id)
        )
        
        shares = list(result.scalars().all())
        share_list = []
        
        for share in shares:
            share_info = {
                "id": str(share.id),
                "share_token": share.share_token,
                "access_type": share.access_type,
                "is_public": share.is_public,
                "access_count": share.access_count,
                "created_at": share.created_at.isoformat(),
                "expires_at": share.expires_at.isoformat() if share.expires_at else None,
                "last_accessed": share.last_accessed.isoformat() if share.last_accessed else None,
                "is_expired": share.is_expired
            }
            
            if share.shared_with:
                # Get user info for specific shares
                from app.services.user_service import UserService
                user_service = UserService(self.db)
                user = await user_service.get_user_by_id(share.shared_with)
                if user:
                    share_info["shared_with"] = {
                        "id": str(user.id),
                        "name": user.name,
                        "email": user.email
                    }
            
            share_list.append(share_info)
        
        return share_list
    
    async def revoke_file_share(
        self,
        share_id: UUID,
        owner_id: UUID
    ) -> bool:
        """Revoke a specific file share."""
        from app.models.file import FileShare
        
        result = await self.db.execute(
            select(FileShare).where(FileShare.id == share_id)
        )
        
        share = result.scalar_one_or_none()
        if not share:
            return False
        
        # Check if user owns the file
        file_record = await self.get_file_by_id(share.file_id)
        if not file_record or file_record.uploaded_by != owner_id:
            return False
        
        # Delete the share
        await self.db.delete(share)
        await self.db.commit()
        
        return True
    
    async def revoke_file_access(self, file_id: UUID, owner_id: UUID) -> bool:
        """Revoke all access to file."""
        from app.models.file import FileShare
        
        file_record = await self.get_file_by_id(file_id)
        
        if not file_record or file_record.uploaded_by != owner_id:
            return False
        
        # Remove all shares
        await self.db.execute(
            select(FileShare).where(FileShare.file_id == file_id)
        )
        
        shares = await self.db.execute(
            select(FileShare).where(FileShare.file_id == file_id)
        )
        
        for share in shares.scalars().all():
            await self.db.delete(share)
        
        # Update file settings
        file_record.is_public = False
        file_record.access_token = None
        file_record.expires_at = None
        file_record.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        return True
    
    async def log_file_access(
        self,
        file_id: UUID,
        user_id: Optional[UUID],
        action: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Log file access for security auditing."""
        # This would typically log to a separate audit table
        # For now, we'll just update the file's last accessed time
        
        file_record = await self.get_file_by_id(file_id)
        if file_record:
            # In a production system, you'd log to an audit table
            # audit_log = FileAuditLog(
            #     file_id=file_id,
            #     user_id=user_id,
            #     action=action,
            #     ip_address=ip_address,
            #     user_agent=user_agent,
            #     timestamp=datetime.now(timezone.utc)
            # )
            # self.db.add(audit_log)
            
            # For now, just update the file's updated_at timestamp
            file_record.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
    
    async def check_file_security_violations(
        self,
        user_id: UUID,
        time_window_minutes: int = 60
    ) -> Dict[str, Any]:
        """Check for potential security violations by user."""
        from sqlalchemy import and_, func
        
        # Check for excessive file access attempts
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
        
        # Count recent file accesses
        access_count = await self.db.execute(
            select(func.count(File.id)).where(
                and_(
                    File.uploaded_by == user_id,
                    File.updated_at > time_threshold
                )
            )
        )
        
        recent_accesses = access_count.scalar() or 0
        
        # Define thresholds
        max_accesses_per_hour = 1000
        
        violations = []
        
        if recent_accesses > max_accesses_per_hour:
            violations.append({
                "type": "excessive_access",
                "count": recent_accesses,
                "threshold": max_accesses_per_hour,
                "severity": "high"
            })
        
        return {
            "user_id": str(user_id),
            "time_window_minutes": time_window_minutes,
            "violations": violations,
            "risk_level": "high" if violations else "low"
        }
    
    async def quarantine_file(
        self,
        file_id: UUID,
        reason: str,
        quarantined_by: UUID
    ) -> bool:
        """Quarantine a file for security reasons."""
        file_record = await self.get_file_by_id(file_id)
        
        if not file_record:
            return False
        
        # Mark file as quarantined
        file_record.status = FileStatus.ERROR  # Using ERROR status for quarantine
        file_record.updated_at = datetime.now(timezone.utc)
        
        # In production, you'd add quarantine metadata
        metadata = json.loads(file_record.file_metadata or "{}")
        metadata.update({
            "quarantined": True,
            "quarantine_reason": reason,
            "quarantined_by": str(quarantined_by),
            "quarantined_at": datetime.now(timezone.utc).isoformat()
        })
        file_record.file_metadata = json.dumps(metadata)
        
        await self.db.commit()
        return True
    
    async def cleanup_expired_files(self) -> int:
        """Clean up expired files and shares."""
        from app.models.file import FileShare
        
        now = datetime.now(timezone.utc)
        cleanup_count = 0
        
        # Clean up expired files
        expired_files = await self.db.execute(
            select(File).where(
                and_(
                    File.expires_at.isnot(None),
                    File.expires_at < now,
                    File.status != FileStatus.DELETED
                )
            )
        )
        
        for file_record in expired_files.scalars().all():
            file_record.status = FileStatus.DELETED
            file_record.updated_at = now
            cleanup_count += 1
        
        # Clean up expired shares
        expired_shares = await self.db.execute(
            select(FileShare).where(
                and_(
                    FileShare.expires_at.isnot(None),
                    FileShare.expires_at < now
                )
            )
        )
        
        for share in expired_shares.scalars().all():
            await self.db.delete(share)
            cleanup_count += 1
        
        if cleanup_count > 0:
            await self.db.commit()
        
        return cleanup_count
    
    async def analyze_content_with_ai(
        self,
        file_id: UUID,
        analysis_type: str = "general"
    ) -> Optional[Dict[str, Any]]:
        """Analyze file content using AI multimodal capabilities."""
        file_record = await self.get_file_by_id(file_id)
        
        if not file_record or file_record.status != FileStatus.READY:
            return None
        
        try:
            if file_record.file_type == FileType.IMAGE:
                return await self._analyze_image_content(file_record, analysis_type)
            elif file_record.file_type == FileType.PDF:
                return await self._analyze_pdf_content(file_record, analysis_type)
            elif file_record.file_type == FileType.DOCUMENT:
                return await self._analyze_document_content(file_record, analysis_type)
            else:
                return {"error": "不支持的文件类型进行AI分析"}
        
        except Exception as e:
            return {"error": f"AI分析失败: {str(e)}"}
    
    async def _analyze_image_content(
        self,
        file_record: File,
        analysis_type: str
    ) -> Dict[str, Any]:
        """Analyze image content using AI vision models."""
        if not self.settings.OPENAI_API_KEY:
            return {"error": "OpenAI API密钥未配置"}
        
        try:
            import openai
            from openai import OpenAI
            
            client = OpenAI(api_key=self.settings.OPENAI_API_KEY)
            
            # Get image content
            image_content = await self._get_file_content(file_record)
            if not image_content:
                return {"error": "无法读取图片内容"}
            
            # Encode image to base64
            import base64
            image_base64 = base64.b64encode(image_content).decode('utf-8')
            
            # Prepare analysis prompt based on type
            if analysis_type == "homework":
                prompt = """请分析这张图片中的作业内容：
1. 识别题目类型（数学、语文、英语等）
2. 提取题目文本
3. 识别学生答案
4. 分析答题质量
5. 提供改进建议

请用中文回答，格式化为JSON结构。"""
            
            elif analysis_type == "document":
                prompt = """请分析这张图片中的文档内容：
1. 提取所有文本内容
2. 识别文档类型和结构
3. 总结主要内容
4. 提取关键信息

请用中文回答，格式化为JSON结构。"""
            
            else:  # general
                prompt = """请分析这张图片的内容：
1. 描述图片中的主要内容
2. 识别图片中的文字（如果有）
3. 分析图片的用途和类型
4. 提供相关的教育价值

请用中文回答，格式化为JSON结构。"""
            
            # Call OpenAI Vision API
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{file_record.mime_type};base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            analysis_result = response.choices[0].message.content
            
            # Try to parse as JSON, fallback to text
            try:
                import json
                result = json.loads(analysis_result)
            except:
                result = {"analysis": analysis_result}
            
            # Add metadata
            result.update({
                "analysis_type": analysis_type,
                "model_used": "gpt-4-vision-preview",
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "file_type": "image"
            })
            
            return result
            
        except Exception as e:
            return {"error": f"图片AI分析失败: {str(e)}"}
    
    async def _analyze_pdf_content(
        self,
        file_record: File,
        analysis_type: str
    ) -> Dict[str, Any]:
        """Analyze PDF content using AI document understanding."""
        if not self.settings.OPENAI_API_KEY:
            return {"error": "OpenAI API密钥未配置"}
        
        try:
            # Extract text from PDF
            pdf_text = await self._extract_pdf_text(file_record)
            if not pdf_text:
                return {"error": "无法提取PDF文本内容"}
            
            # Limit text length for API
            max_length = 8000  # Leave room for prompt
            if len(pdf_text) > max_length:
                pdf_text = pdf_text[:max_length] + "..."
            
            import openai
            from openai import OpenAI
            
            client = OpenAI(api_key=self.settings.OPENAI_API_KEY)
            
            # Prepare analysis prompt
            if analysis_type == "homework":
                prompt = f"""请分析以下PDF文档中的作业内容：

{pdf_text}

请提供：
1. 题目类型和科目识别
2. 题目内容提取
3. 答案分析（如果有）
4. 学习要点总结
5. 改进建议

请用中文回答，格式化为JSON结构。"""
            
            elif analysis_type == "educational":
                prompt = f"""请分析以下PDF文档的教育内容：

{pdf_text}

请提供：
1. 文档类型和主题
2. 主要知识点
3. 学习目标
4. 重点内容摘要
5. 教学建议

请用中文回答，格式化为JSON结构。"""
            
            else:  # general
                prompt = f"""请分析以下PDF文档内容：

{pdf_text}

请提供：
1. 文档主题和类型
2. 内容结构分析
3. 关键信息提取
4. 内容摘要
5. 实用价值评估

请用中文回答，格式化为JSON结构。"""
            
            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.1
            )
            
            analysis_result = response.choices[0].message.content
            
            # Try to parse as JSON
            try:
                import json
                result = json.loads(analysis_result)
            except:
                result = {"analysis": analysis_result}
            
            # Add metadata
            result.update({
                "analysis_type": analysis_type,
                "model_used": "gpt-4-turbo-preview",
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "file_type": "pdf",
                "text_length": len(pdf_text)
            })
            
            return result
            
        except Exception as e:
            return {"error": f"PDF AI分析失败: {str(e)}"}
    
    async def _analyze_document_content(
        self,
        file_record: File,
        analysis_type: str
    ) -> Dict[str, Any]:
        """Analyze document content using AI text understanding."""
        if not self.settings.OPENAI_API_KEY:
            return {"error": "OpenAI API密钥未配置"}
        
        try:
            # Extract text from document
            doc_text = await self._extract_document_text(file_record)
            if not doc_text:
                return {"error": "无法提取文档文本内容"}
            
            # Limit text length
            max_length = 8000
            if len(doc_text) > max_length:
                doc_text = doc_text[:max_length] + "..."
            
            import openai
            from openai import OpenAI
            
            client = OpenAI(api_key=self.settings.OPENAI_API_KEY)
            
            # Prepare analysis prompt
            prompt = f"""请分析以下文档内容：

{doc_text}

请提供：
1. 文档类型和主题
2. 内容结构分析
3. 关键信息提取
4. 内容质量评估
5. 改进建议

请用中文回答，格式化为JSON结构。"""
            
            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.1
            )
            
            analysis_result = response.choices[0].message.content
            
            # Try to parse as JSON
            try:
                import json
                result = json.loads(analysis_result)
            except:
                result = {"analysis": analysis_result}
            
            # Add metadata
            result.update({
                "analysis_type": analysis_type,
                "model_used": "gpt-4-turbo-preview",
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "file_type": "document",
                "text_length": len(doc_text)
            })
            
            return result
            
        except Exception as e:
            return {"error": f"文档AI分析失败: {str(e)}"}
    
    async def _get_file_content(self, file_record: File) -> Optional[bytes]:
        """Get file content from storage."""
        try:
            if self.has_cloud_storage and file_record.storage_path.startswith('uploads/'):
                # Download from S3
                response = self._s3_client.get_object(
                    Bucket=self.settings.AWS_S3_BUCKET,
                    Key=file_record.storage_path
                )
                return response['Body'].read()
            else:
                # Read from local storage
                if os.path.exists(file_record.storage_path):
                    with open(file_record.storage_path, 'rb') as f:
                        return f.read()
            
            return None
            
        except Exception:
            return None
    
    async def _extract_pdf_text(self, file_record: File) -> Optional[str]:
        """Extract text content from PDF file."""
        try:
            content = await self._get_file_content(file_record)
            if not content:
                return None
            
            # Use PyPDF2 to extract text
            import PyPDF2
            import io
            
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            text_content = []
            
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())
            
            return "\n".join(text_content)
            
        except Exception:
            return None
    
    async def _extract_document_text(self, file_record: File) -> Optional[str]:
        """Extract text content from document files."""
        try:
            content = await self._get_file_content(file_record)
            if not content:
                return None
            
            if file_record.mime_type == "text/plain":
                return content.decode('utf-8', errors='ignore')
            
            elif file_record.mime_type in [
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ]:
                # Extract text from DOCX
                import docx
                import io
                
                doc = docx.Document(io.BytesIO(content))
                text_content = []
                
                for paragraph in doc.paragraphs:
                    text_content.append(paragraph.text)
                
                return "\n".join(text_content)
            
            # For other document types, return basic info
            return f"文档类型: {file_record.mime_type}, 大小: {file_record.file_size} 字节"
            
        except Exception:
            return None
    
    async def batch_analyze_files(
        self,
        file_ids: List[UUID],
        analysis_type: str = "general"
    ) -> Dict[UUID, Dict[str, Any]]:
        """Batch analyze multiple files."""
        results = {}
        
        for file_id in file_ids:
            try:
                result = await self.analyze_content_with_ai(file_id, analysis_type)
                results[file_id] = result or {"error": "分析失败"}
            except Exception as e:
                results[file_id] = {"error": f"分析异常: {str(e)}"}
        
        return results
    
    async def get_file_statistics(self, user_id: Optional[UUID] = None) -> dict:
        """Get file upload statistics."""
        from sqlalchemy import func
        
        base_query = select(File).where(File.status != FileStatus.DELETED)
        
        if user_id:
            base_query = base_query.where(File.uploaded_by == user_id)
        
        # Total files
        total_result = await self.db.execute(
            select(func.count(File.id)).select_from(base_query.subquery())
        )
        total_files = total_result.scalar() or 0
        
        # Total size
        size_result = await self.db.execute(
            select(func.sum(File.file_size)).select_from(base_query.subquery())
        )
        total_size = size_result.scalar() or 0
        
        # Files by type
        type_stats = {}
        for file_type in FileType:
            type_result = await self.db.execute(
                select(func.count(File.id))
                .select_from(base_query.where(File.file_type == file_type).subquery())
            )
            type_stats[file_type.value] = type_result.scalar() or 0
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "files_by_type": type_stats
        }