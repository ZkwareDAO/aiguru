"""Enhanced API endpoints for AI grading with visual annotations."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile, Form
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.exceptions import AIServiceError, ValidationError
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.services.enhanced_grading_service import get_enhanced_grading_service
from app.services.file_service import FileService

router = APIRouter(prefix="/enhanced-grading", tags=["enhanced-grading"])


class VisualGradingRequest(BaseModel):
    """Request for visual grading with annotations."""
    
    submission_id: UUID = Field(..., description="Submission ID")
    image_file_id: UUID = Field(..., description="Uploaded image file ID")
    question_text: str = Field(..., description="Question or problem text")
    answer_standard: str = Field(..., description="Standard answer for comparison")
    grading_instructions: Optional[str] = Field(None, description="Specific grading instructions")
    display_mode: str = Field(default="coordinates", description="Display mode: coordinates or cropped_regions")
    
    class Config:
        json_encoders = {UUID: str}


class BatchVisualGradingRequest(BaseModel):
    """Request for batch visual grading."""
    
    submissions: List[VisualGradingRequest] = Field(..., description="List of submissions to grade")
    display_mode: str = Field(default="coordinates", description="Display mode for all submissions")


class VisualGradingResponse(BaseModel):
    """Response for visual grading."""
    
    submission_id: str
    display_mode: str
    grading_summary: dict
    coordinate_annotations: Optional[List[dict]] = None
    error_cards: Optional[List[dict]] = None
    original_image_url: Optional[str] = None
    knowledge_point_summary: dict
    processing_timestamp: str


class CoordinateAnnotation(BaseModel):
    """Coordinate annotation data."""
    
    annotation_id: str
    coordinates: dict
    error_details: dict
    knowledge_points: List[str]
    popup_content: dict


class ErrorCard(BaseModel):
    """Error card data for cropped regions."""
    
    card_id: str
    error_details: dict
    cropped_image: dict
    knowledge_points: List[str]
    actions: dict


@router.post(
    "/grade-visual",
    response_model=VisualGradingResponse,
    status_code=status.HTTP_200_OK,
    summary="Grade submission with visual annotations",
    description="Grade a submission and return visual annotations (coordinates or cropped regions)"
)
async def grade_submission_visual(
    request: VisualGradingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enhanced_grading_service=Depends(get_enhanced_grading_service)
):
    """Grade submission with visual annotations."""
    try:
        # Check permissions
        require_permission(current_user, "grade_submissions")
        
        # Validate display mode
        if request.display_mode not in ["coordinates", "cropped_regions"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid display mode. Must be 'coordinates' or 'cropped_regions'"
            )
        
        # Process grading
        result = await enhanced_grading_service.grade_submission_with_annotations(
            submission_id=request.submission_id,
            image_file_id=request.image_file_id,
            question_text=request.question_text,
            answer_standard=request.answer_standard,
            grading_instructions=request.grading_instructions,
            display_mode=request.display_mode
        )
        
        return VisualGradingResponse(**result)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AIServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI grading failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during grading"
        )


@router.post(
    "/grade-visual-batch",
    response_model=List[VisualGradingResponse],
    status_code=status.HTTP_200_OK,
    summary="Batch grade submissions with visual annotations",
    description="Grade multiple submissions and return visual annotations"
)
async def batch_grade_submissions_visual(
    request: BatchVisualGradingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enhanced_grading_service=Depends(get_enhanced_grading_service)
):
    """Batch grade submissions with visual annotations."""
    try:
        # Check permissions
        require_permission(current_user, "grade_submissions")
        
        # Validate display mode
        if request.display_mode not in ["coordinates", "cropped_regions"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid display mode. Must be 'coordinates' or 'cropped_regions'"
            )
        
        # Convert requests to dict format
        submissions = []
        for sub_request in request.submissions:
            submissions.append({
                "submission_id": sub_request.submission_id,
                "image_file_id": sub_request.image_file_id,
                "question_text": sub_request.question_text,
                "answer_standard": sub_request.answer_standard,
                "grading_instructions": sub_request.grading_instructions
            })
        
        # Process batch grading
        results = await enhanced_grading_service.batch_grade_with_annotations(
            submissions=submissions,
            display_mode=request.display_mode
        )
        
        return [VisualGradingResponse(**result) for result in results]
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AIServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI grading failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during batch grading"
        )


@router.post(
    "/upload-and-grade",
    response_model=VisualGradingResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload image and grade with visual annotations",
    description="Upload an image file and immediately grade it with visual annotations"
)
async def upload_and_grade_visual(
    submission_id: UUID = Form(...),
    question_text: str = Form(...),
    answer_standard: str = Form(...),
    grading_instructions: Optional[str] = Form(None),
    display_mode: str = Form(default="coordinates"),
    image_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enhanced_grading_service=Depends(get_enhanced_grading_service),
    file_service: FileService = Depends(FileService)
):
    """Upload image and grade with visual annotations."""
    try:
        # Check permissions
        require_permission(current_user, "grade_submissions")
        
        # Validate file type
        if not image_file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )
        
        # Validate display mode
        if display_mode not in ["coordinates", "cropped_regions"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid display mode. Must be 'coordinates' or 'cropped_regions'"
            )
        
        # Upload file
        file_content = await image_file.read()
        file_id = await file_service.save_file(
            filename=image_file.filename,
            content=file_content,
            content_type=image_file.content_type
        )
        
        # Process grading
        result = await enhanced_grading_service.grade_submission_with_annotations(
            submission_id=submission_id,
            image_file_id=file_id,
            question_text=question_text,
            answer_standard=answer_standard,
            grading_instructions=grading_instructions,
            display_mode=display_mode
        )
        
        # Add original image URL
        result["original_image_url"] = f"/api/files/{file_id}"
        
        return VisualGradingResponse(**result)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AIServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI grading failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during upload and grading"
        )


@router.get(
    "/health",
    summary="Check enhanced grading service health",
    description="Check the health status of the enhanced grading service"
)
async def check_enhanced_grading_health(
    enhanced_grading_service=Depends(get_enhanced_grading_service)
):
    """Check enhanced grading service health."""
    try:
        health_status = await enhanced_grading_service.health_check()
        
        if health_status.get("status") == "healthy":
            return health_status
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health_status
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


@router.get(
    "/display-modes",
    summary="Get available display modes",
    description="Get list of available display modes for visual grading"
)
async def get_display_modes():
    """Get available display modes."""
    return {
        "display_modes": [
            {
                "mode": "coordinates",
                "name": "坐标标注模式",
                "description": "在原图上通过坐标点标注错误位置，点击显示详细信息",
                "features": [
                    "原图overlay显示",
                    "点击式交互",
                    "Canvas渲染",
                    "缩放拖拽支持"
                ]
            },
            {
                "mode": "cropped_regions", 
                "name": "局部图卡片模式",
                "description": "将错误区域裁剪为局部图片，配合文字说明形成卡片展示",
                "features": [
                    "局部图片展示",
                    "卡片式布局",
                    "定位回原图",
                    "详细分析说明"
                ]
            }
        ]
    }