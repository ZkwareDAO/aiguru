"""File management API endpoints."""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.file import FileType, FileStatus
from app.models.user import User, UserRole
from app.schemas.file import (
    FileResponse,
    FileUploadResponse,
    FileListResponse,
    FileStats,
    AvatarUploadResponse,
    FileDeleteResponse,
    FileUrlResponse,
    BulkFileOperation,
    FileSearchQuery,
    FileShareRequest,
    FileShareResponse,
    FileAccessRequest,
    FileProcessingResult
)
from app.schemas.user import UserUpdate
from app.services.file_service import FileService
from app.services.user_service import UserService


router = APIRouter(prefix="/files", tags=["文件管理"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(default="general", description="文件类别: general, image, document"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FileUploadResponse:
    """上传文件."""
    file_service = FileService(db)
    
    try:
        uploaded_file = await file_service.upload_file(
            file=file,
            user_id=current_user.id,
            file_category=category
        )
        
        return FileUploadResponse(
            file=FileResponse.model_validate(uploaded_file)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}"
        )


@router.post("/upload-avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AvatarUploadResponse:
    """上传用户头像."""
    file_service = FileService(db)
    
    try:
        # Upload avatar file
        uploaded_file = await file_service.upload_avatar(
            file=file,
            user_id=current_user.id
        )
        
        # Update user avatar URL
        success = await file_service.update_user_avatar(
            user_id=current_user.id,
            file_id=uploaded_file.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="头像更新失败"
            )
        
        return AvatarUploadResponse(
            file=FileResponse.model_validate(uploaded_file),
            avatar_url=uploaded_file.file_url
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"头像上传失败: {str(e)}"
        )


@router.get("/my-files", response_model=FileListResponse)
async def get_my_files(
    file_type: Optional[FileType] = Query(None, description="文件类型筛选"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FileListResponse:
    """获取我的文件列表."""
    file_service = FileService(db)
    
    files = await file_service.get_user_files(
        user_id=current_user.id,
        file_type=file_type,
        limit=limit
    )
    
    # Calculate total size
    total_size = sum(f.file_size for f in files)
    
    return FileListResponse(
        files=[FileResponse.model_validate(f) for f in files],
        total=len(files),
        total_size_bytes=total_size,
        total_size_mb=round(total_size / (1024 * 1024), 2)
    )


@router.get("/{file_id}", response_model=FileResponse)
async def get_file_info(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FileResponse:
    """获取文件信息."""
    file_service = FileService(db)
    
    file_record = await file_service.get_file_by_id(file_id)
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # Check access permission
    if not file_record.is_public and file_record.uploaded_by != current_user.id:
        # TODO: Add more sophisticated permission checking (e.g., shared files)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有访问此文件的权限"
        )
    
    return FileResponse.model_validate(file_record)


@router.get("/{file_id}/url", response_model=FileUrlResponse)
async def get_file_url(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FileUrlResponse:
    """获取文件访问URL."""
    file_service = FileService(db)
    
    file_url = await file_service.get_file_url(
        file_id=file_id,
        user_id=current_user.id
    )
    
    if not file_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在或无访问权限"
        )
    
    return FileUrlResponse(
        file_id=file_id,
        file_url=file_url
    )


@router.delete("/{file_id}", response_model=FileDeleteResponse)
async def delete_file(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FileDeleteResponse:
    """删除文件."""
    file_service = FileService(db)
    
    success = await file_service.delete_file(
        file_id=file_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在或无删除权限"
        )
    
    return FileDeleteResponse()


@router.get("/stats/overview", response_model=FileStats)
async def get_file_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FileStats:
    """获取文件统计信息."""
    file_service = FileService(db)
    
    stats = await file_service.get_file_statistics(user_id=current_user.id)
    
    return FileStats(**stats)


@router.get("/stats/global", response_model=FileStats)
async def get_global_file_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FileStats:
    """获取全局文件统计信息 (仅教师可查看)."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有教师可以查看全局统计信息"
        )
    
    file_service = FileService(db)
    
    stats = await file_service.get_file_statistics()
    
    return FileStats(**stats)


@router.post("/bulk-operation")
async def bulk_file_operation(
    operation_data: BulkFileOperation,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """批量文件操作."""
    file_service = FileService(db)
    
    success_count = 0
    
    if operation_data.operation == "delete":
        for file_id in operation_data.file_ids:
            success = await file_service.delete_file(file_id, current_user.id)
            if success:
                success_count += 1
        
        return {"message": f"已删除 {success_count} 个文件"}
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的操作类型"
        )


# File serving endpoint (for development)
@router.get("/serve/{filename}")
async def serve_file(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """提供文件服务 (开发环境)."""
    from fastapi.responses import FileResponse
    import os
    
    # This is a simple file serving endpoint for development
    # In production, files should be served by a CDN or cloud storage
    
    file_path = os.path.join("uploads", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


# Advanced search endpoint
@router.post("/search", response_model=FileListResponse)
async def search_files(
    search_query: FileSearchQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FileListResponse:
    """高级文件搜索."""
    # This would implement advanced file search functionality
    # For now, return user's files with basic filtering
    
    file_service = FileService(db)
    
    files = await file_service.get_user_files(
        user_id=current_user.id,
        file_type=search_query.file_type,
        limit=search_query.per_page
    )
    
    # Apply additional filters if needed
    if search_query.query:
        files = [
            f for f in files 
            if search_query.query.lower() in f.original_name.lower()
        ]
    
    if search_query.min_size:
        files = [f for f in files if f.file_size >= search_query.min_size]
    
    if search_query.max_size:
        files = [f for f in files if f.file_size <= search_query.max_size]
    
    # Calculate total size
    total_size = sum(f.file_size for f in files)
    
    return FileListResponse(
        files=[FileResponse.model_validate(f) for f in files],
        total=len(files),
        total_size_bytes=total_size,
        total_size_mb=round(total_size / (1024 * 1024), 2)
    )


# File sharing and security endpoints
@router.post("/{file_id}/share", response_model=FileShareResponse)
async def share_file(
    file_id: UUID,
    share_request: FileShareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FileShareResponse:
    """分享文件."""
    file_service = FileService(db)
    
    result = await file_service.share_file(
        file_id=file_id,
        owner_id=current_user.id,
        share_with_users=share_request.share_with_users,
        is_public=share_request.is_public,
        expires_at=share_request.expires_at
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return FileShareResponse(
        file_id=file_id,
        share_url=result["shares"][0]["share_url"] if result["shares"] else "",
        is_public=share_request.is_public,
        expires_at=share_request.expires_at,
        shared_with=share_request.share_with_users or []
    )


@router.get("/{file_id}/shares")
async def get_file_shares(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """获取文件分享列表."""
    file_service = FileService(db)
    
    shares = await file_service.get_file_shares(file_id, current_user.id)
    
    return {"shares": shares}


@router.delete("/{file_id}/shares/{share_id}")
async def revoke_file_share(
    file_id: UUID,
    share_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """撤销文件分享."""
    file_service = FileService(db)
    
    success = await file_service.revoke_file_share(share_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分享不存在或无权限"
        )
    
    return {"message": "分享已撤销"}


@router.get("/shared/{share_token}")
async def access_shared_file(
    share_token: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """通过分享链接访问文件."""
    file_service = FileService(db)
    
    # Check share access
    access_info = await file_service.check_share_access(
        share_token, 
        current_user.id if current_user else None
    )
    
    if not access_info["valid"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=access_info["error"]
        )
    
    # Get the file
    file_record = await file_service.get_file_by_share_token(share_token)
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # Log access
    await file_service.log_file_access(
        file_record.id,
        current_user.id if current_user else None,
        "shared_access"
    )
    
    return FileResponse.model_validate(file_record)


@router.post("/{file_id}/analyze", response_model=FileProcessingResult)
async def analyze_file_content(
    file_id: UUID,
    analysis_type: str = Query(default="general", description="分析类型: general, homework, document, educational"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FileProcessingResult:
    """AI分析文件内容."""
    file_service = FileService(db)
    
    # Check file access
    has_access = await file_service.check_file_access(file_id, current_user.id, "view")
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限访问此文件"
        )
    
    # Perform AI analysis
    result = await file_service.analyze_content_with_ai(file_id, analysis_type)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI分析失败"
        )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return FileProcessingResult(
        file_id=file_id,
        status=FileStatus.READY,
        ocr_text=result.get("extracted_text"),
        extracted_text=result.get("analysis"),
        processed_at=datetime.now()
    )


@router.post("/{file_id}/temporary-access")
async def create_temporary_access(
    file_id: UUID,
    access_request: FileAccessRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """创建临时访问链接."""
    file_service = FileService(db)
    
    expires_in = access_request.expires_in or 3600  # Default 1 hour
    
    access_url = await file_service.create_temporary_access_link(
        file_id, current_user.id, expires_in
    )
    
    if not access_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在或无权限"
        )
    
    return {
        "access_url": access_url,
        "expires_in": expires_in,
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
    }


@router.post("/batch-analyze")
async def batch_analyze_files(
    file_ids: List[UUID] = Query(..., description="文件ID列表"),
    analysis_type: str = Query(default="general", description="分析类型"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """批量AI分析文件."""
    if len(file_ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="一次最多分析10个文件"
        )
    
    file_service = FileService(db)
    
    results = await file_service.batch_analyze_files(file_ids, analysis_type)
    
    return {"results": results}