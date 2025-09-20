"""Tests for file service."""

import os
import tempfile
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import FileStatus, FileType
from app.models.user import User, UserRole
from app.services.file_service import FileService


class MockUploadFile:
    """Mock UploadFile for testing."""
    
    def __init__(self, filename: str, content: bytes, content_type: str):
        self.filename = filename
        self.content = content
        self.content_type = content_type
        self.size = len(content)
        self._position = 0
    
    async def read(self) -> bytes:
        return self.content
    
    async def seek(self, position: int) -> None:
        self._position = position


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return User(
        id=uuid4(),
        email="test@example.com",
        name="Test User",
        role=UserRole.STUDENT,
        password_hash="hashed_password",
        is_active=True,
        is_verified=True
    )


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes.getvalue()


@pytest.fixture
def sample_pdf():
    """Create a sample PDF content for testing."""
    # Simple PDF content (not a real PDF, just for testing)
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"


class TestFileService:
    """Test file service functionality."""
    
    def test_get_file_type(self, db_session: AsyncSession):
        """Test file type detection."""
        file_service = FileService(db_session)
        
        assert file_service._get_file_type("image/jpeg") == FileType.IMAGE
        assert file_service._get_file_type("application/pdf") == FileType.DOCUMENT
        assert file_service._get_file_type("video/mp4") == FileType.VIDEO
        assert file_service._get_file_type("audio/mp3") == FileType.AUDIO
        assert file_service._get_file_type("application/zip") == FileType.ARCHIVE
        assert file_service._get_file_type("unknown/type") == FileType.OTHER
    
    def test_validate_file_success(self, db_session: AsyncSession, sample_image):
        """Test successful file validation."""
        file_service = FileService(db_session)
        
        mock_file = MockUploadFile(
            filename="test.jpg",
            content=sample_image,
            content_type="image/jpeg"
        )
        
        is_valid, message = file_service._validate_file(
            file=mock_file,
            allowed_types=file_service.ALLOWED_IMAGE_TYPES,
            max_size=file_service.MAX_IMAGE_SIZE
        )
        
        assert is_valid is True
        assert message == "验证通过"
    
    def test_validate_file_size_error(self, db_session: AsyncSession):
        """Test file size validation error."""
        file_service = FileService(db_session)
        
        # Create a large content
        large_content = b"x" * (file_service.MAX_IMAGE_SIZE + 1)
        
        mock_file = MockUploadFile(
            filename="large.jpg",
            content=large_content,
            content_type="image/jpeg"
        )
        
        is_valid, message = file_service._validate_file(
            file=mock_file,
            allowed_types=file_service.ALLOWED_IMAGE_TYPES,
            max_size=file_service.MAX_IMAGE_SIZE
        )
        
        assert is_valid is False
        assert "文件大小不能超过" in message
    
    def test_validate_file_type_error(self, db_session: AsyncSession, sample_image):
        """Test file type validation error."""
        file_service = FileService(db_session)
        
        mock_file = MockUploadFile(
            filename="test.exe",
            content=sample_image,
            content_type="application/x-executable"
        )
        
        is_valid, message = file_service._validate_file(
            file=mock_file,
            allowed_types=file_service.ALLOWED_IMAGE_TYPES,
            max_size=file_service.MAX_IMAGE_SIZE
        )
        
        assert is_valid is False
        assert "不支持的文件类型" in message
    
    def test_generate_filename(self, db_session: AsyncSession):
        """Test filename generation."""
        file_service = FileService(db_session)
        
        filename = file_service._generate_filename("test.jpg", ".jpg")
        
        assert filename.endswith(".jpg")
        assert len(filename) > 10  # Should include timestamp and UUID
        assert "_" in filename  # Should have timestamp separator
    
    def test_process_avatar_image(self, db_session: AsyncSession, sample_image):
        """Test avatar image processing."""
        file_service = FileService(db_session)
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(sample_image)
            temp_file_path = temp_file.name
        
        try:
            # Process the image
            processed_path = file_service._process_avatar_image(temp_file_path)
            
            # Check that processed file exists
            assert os.path.exists(processed_path)
            
            # Check that processed image has correct dimensions
            with Image.open(processed_path) as img:
                assert img.size == file_service.AVATAR_SIZE
                assert img.mode == "RGB"
            
            # Clean up
            os.unlink(processed_path)
        
        finally:
            # Clean up original file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    @pytest.mark.asyncio
    async def test_get_file_statistics_empty(self, db_session: AsyncSession):
        """Test file statistics with no files."""
        file_service = FileService(db_session)
        
        stats = await file_service.get_file_statistics()
        
        assert stats["total_files"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["total_size_mb"] == 0.0
        assert isinstance(stats["files_by_type"], dict)
        
        # Check all file types are present
        for file_type in FileType:
            assert file_type.value in stats["files_by_type"]
            assert stats["files_by_type"][file_type.value] == 0


# Integration test (requires database)
@pytest.mark.asyncio
async def test_file_upload_integration(db_session: AsyncSession, mock_user, sample_image):
    """Test complete file upload process."""
    file_service = FileService(db_session)
    
    # Add user to session
    db_session.add(mock_user)
    await db_session.commit()
    
    mock_file = MockUploadFile(
        filename="test_avatar.jpg",
        content=sample_image,
        content_type="image/jpeg"
    )
    
    # Upload file
    uploaded_file = await file_service.upload_file(
        file=mock_file,
        user_id=mock_user.id,
        file_category="avatar"
    )
    
    # Verify file record
    assert uploaded_file.id is not None
    assert uploaded_file.original_name == "test_avatar.jpg"
    assert uploaded_file.file_type == FileType.IMAGE
    assert uploaded_file.mime_type == "image/jpeg"
    assert uploaded_file.status == FileStatus.READY
    assert uploaded_file.uploaded_by == mock_user.id
    assert uploaded_file.file_size > 0
    
    # Verify file exists on disk
    assert os.path.exists(uploaded_file.storage_path)
    
    # Clean up
    if os.path.exists(uploaded_file.storage_path):
        os.unlink(uploaded_file.storage_path)