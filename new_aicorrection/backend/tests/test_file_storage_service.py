"""Tests for enhanced file storage and processing service."""

import os
import tempfile
from datetime import datetime, timezone, timedelta
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import UploadFile
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File, FileStatus, FileType
from app.models.user import User, UserRole
from app.services.file_service import FileService


@pytest.fixture
async def file_service(db_session: AsyncSession) -> FileService:
    """Create file service instance."""
    return FileService(db_session)


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user."""
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        name="Test User",
        role=UserRole.STUDENT,
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def test_image_file() -> UploadFile:
    """Create test image file."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return UploadFile(
        filename="test_image.jpg",
        file=img_bytes,
        content_type="image/jpeg",
        size=len(img_bytes.getvalue())
    )


@pytest.fixture
def test_pdf_file() -> UploadFile:
    """Create test PDF file."""
    # Create a simple PDF content (mock)
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_bytes = BytesIO(pdf_content)
    
    return UploadFile(
        filename="test_document.pdf",
        file=pdf_bytes,
        content_type="application/pdf",
        size=len(pdf_content)
    )


class TestFileUpload:
    """Test file upload functionality."""
    
    async def test_upload_image_file(
        self,
        file_service: FileService,
        test_user: User,
        test_image_file: UploadFile
    ):
        """Test uploading an image file."""
        uploaded_file = await file_service.upload_file(
            file=test_image_file,
            user_id=test_user.id,
            file_category="image"
        )
        
        assert uploaded_file.id is not None
        assert uploaded_file.original_name == "test_image.jpg"
        assert uploaded_file.file_type == FileType.IMAGE
        assert uploaded_file.mime_type == "image/jpeg"
        assert uploaded_file.uploaded_by == test_user.id
        assert uploaded_file.status == FileStatus.READY
    
    async def test_upload_pdf_file(
        self,
        file_service: FileService,
        test_user: User,
        test_pdf_file: UploadFile
    ):
        """Test uploading a PDF file."""
        uploaded_file = await file_service.upload_file(
            file=test_pdf_file,
            user_id=test_user.id,
            file_category="document"
        )
        
        assert uploaded_file.id is not None
        assert uploaded_file.original_name == "test_document.pdf"
        assert uploaded_file.file_type == FileType.PDF
        assert uploaded_file.mime_type == "application/pdf"
        assert uploaded_file.uploaded_by == test_user.id
        assert uploaded_file.status == FileStatus.READY
    
    async def test_file_validation_size_limit(
        self,
        file_service: FileService,
        test_user: User
    ):
        """Test file size validation."""
        # Create oversized file
        large_content = b"x" * (100 * 1024 * 1024)  # 100MB
        large_file = UploadFile(
            filename="large_file.jpg",
            file=BytesIO(large_content),
            content_type="image/jpeg",
            size=len(large_content)
        )
        
        with pytest.raises(Exception):  # Should raise HTTPException
            await file_service.upload_file(
                file=large_file,
                user_id=test_user.id,
                file_category="image"
            )
    
    async def test_file_validation_mime_type(
        self,
        file_service: FileService,
        test_user: User
    ):
        """Test MIME type validation."""
        # Create file with wrong MIME type
        wrong_file = UploadFile(
            filename="test.exe",
            file=BytesIO(b"executable content"),
            content_type="application/x-executable"
        )
        
        with pytest.raises(Exception):  # Should raise HTTPException
            await file_service.upload_file(
                file=wrong_file,
                user_id=test_user.id,
                file_category="image"
            )


class TestFileAccess:
    """Test file access control."""
    
    async def test_check_file_access_owner(
        self,
        file_service: FileService,
        test_user: User,
        test_image_file: UploadFile
    ):
        """Test file access for owner."""
        uploaded_file = await file_service.upload_file(
            file=test_image_file,
            user_id=test_user.id
        )
        
        has_access = await file_service.check_file_access(
            uploaded_file.id,
            test_user.id,
            "view"
        )
        
        assert has_access is True
    
    async def test_check_file_access_non_owner(
        self,
        file_service: FileService,
        test_user: User,
        test_image_file: UploadFile,
        db_session: AsyncSession
    ):
        """Test file access for non-owner."""
        # Create another user
        other_user = User(
            email="other@example.com",
            password_hash="hashed_password",
            name="Other User",
            role=UserRole.STUDENT,
            is_active=True,
            is_verified=True
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)
        
        uploaded_file = await file_service.upload_file(
            file=test_image_file,
            user_id=test_user.id
        )
        
        has_access = await file_service.check_file_access(
            uploaded_file.id,
            other_user.id,
            "view"
        )
        
        assert has_access is False
    
    async def test_get_secure_file_url(
        self,
        file_service: FileService,
        test_user: User,
        test_image_file: UploadFile
    ):
        """Test getting secure file URL."""
        uploaded_file = await file_service.upload_file(
            file=test_image_file,
            user_id=test_user.id
        )
        
        file_url = await file_service.get_file_url(
            uploaded_file.id,
            test_user.id
        )
        
        assert file_url is not None
        assert isinstance(file_url, str)


class TestFileSharing:
    """Test file sharing functionality."""
    
    async def test_share_file_public(
        self,
        file_service: FileService,
        test_user: User,
        test_image_file: UploadFile
    ):
        """Test sharing file publicly."""
        uploaded_file = await file_service.upload_file(
            file=test_image_file,
            user_id=test_user.id
        )
        
        result = await file_service.share_file(
            file_id=uploaded_file.id,
            owner_id=test_user.id,
            is_public=True,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        assert result["success"] is True
        assert len(result["shares"]) > 0
        assert result["shares"][0]["type"] == "public"
    
    async def test_get_file_shares(
        self,
        file_service: FileService,
        test_user: User,
        test_image_file: UploadFile
    ):
        """Test getting file shares."""
        uploaded_file = await file_service.upload_file(
            file=test_image_file,
            user_id=test_user.id
        )
        
        # Share the file
        await file_service.share_file(
            file_id=uploaded_file.id,
            owner_id=test_user.id,
            is_public=True
        )
        
        shares = await file_service.get_file_shares(
            uploaded_file.id,
            test_user.id
        )
        
        assert len(shares) > 0
        assert shares[0]["is_public"] is True
    
    async def test_revoke_file_access(
        self,
        file_service: FileService,
        test_user: User,
        test_image_file: UploadFile
    ):
        """Test revoking file access."""
        uploaded_file = await file_service.upload_file(
            file=test_image_file,
            user_id=test_user.id
        )
        
        # Share the file
        await file_service.share_file(
            file_id=uploaded_file.id,
            owner_id=test_user.id,
            is_public=True
        )
        
        # Revoke access
        success = await file_service.revoke_file_access(
            uploaded_file.id,
            test_user.id
        )
        
        assert success is True


class TestFileProcessing:
    """Test file processing and AI analysis."""
    
    async def test_extract_file_metadata(
        self,
        file_service: FileService,
        test_user: User,
        test_image_file: UploadFile
    ):
        """Test extracting file metadata."""
        uploaded_file = await file_service.upload_file(
            file=test_image_file,
            user_id=test_user.id
        )
        
        # Check if metadata was extracted
        assert uploaded_file.file_metadata is not None
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OpenAI API key not available"
    )
    async def test_ai_content_analysis(
        self,
        file_service: FileService,
        test_user: User,
        test_image_file: UploadFile
    ):
        """Test AI content analysis (requires OpenAI API key)."""
        uploaded_file = await file_service.upload_file(
            file=test_image_file,
            user_id=test_user.id
        )
        
        result = await file_service.analyze_content_with_ai(
            uploaded_file.id,
            "general"
        )
        
        assert result is not None
        assert "error" not in result or result.get("analysis_type") == "general"


class TestFileSecurity:
    """Test file security features."""
    
    async def test_malware_scan(
        self,
        file_service: FileService
    ):
        """Test malware scanning."""
        # Create a test file path
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"safe content")
            tmp_file_path = tmp_file.name
        
        try:
            is_safe = await file_service._scan_for_malware(tmp_file_path)
            assert is_safe is True
        finally:
            os.unlink(tmp_file_path)
    
    async def test_security_violations_check(
        self,
        file_service: FileService,
        test_user: User
    ):
        """Test security violations check."""
        violations = await file_service.check_file_security_violations(
            test_user.id,
            time_window_minutes=60
        )
        
        assert "user_id" in violations
        assert "violations" in violations
        assert "risk_level" in violations
    
    async def test_quarantine_file(
        self,
        file_service: FileService,
        test_user: User,
        test_image_file: UploadFile
    ):
        """Test file quarantine."""
        uploaded_file = await file_service.upload_file(
            file=test_image_file,
            user_id=test_user.id
        )
        
        success = await file_service.quarantine_file(
            uploaded_file.id,
            "Test quarantine",
            test_user.id
        )
        
        assert success is True


class TestFileCleanup:
    """Test file cleanup functionality."""
    
    async def test_cleanup_expired_files(
        self,
        file_service: FileService,
        test_user: User,
        test_image_file: UploadFile
    ):
        """Test cleanup of expired files."""
        # Upload file with past expiration
        uploaded_file = await file_service.upload_file(
            file=test_image_file,
            user_id=test_user.id
        )
        
        # Set expiration in the past
        uploaded_file.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await file_service.db.commit()
        
        cleanup_count = await file_service.cleanup_expired_files()
        
        assert cleanup_count >= 1