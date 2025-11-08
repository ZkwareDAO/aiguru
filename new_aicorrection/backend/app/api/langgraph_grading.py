"""API endpoints for LangGraph-based grading system."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.langgraph_grading_workflow import get_langgraph_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/langgraph/grading", tags=["LangGraph Grading"])


# Request/Response schemas
class LangGraphGradingRequest(BaseModel):
    """Request schema for LangGraph grading."""
    
    question_files: List[str] = Field(default_factory=list, description="Question file paths")
    answer_files: List[str] = Field(..., description="Answer file paths (required)")
    marking_scheme_files: List[str] = Field(default_factory=list, description="Marking scheme file paths")
    
    task_type: str = Field(default="auto", description="Grading task type")
    strictness_level: str = Field(default="中等", description="Grading strictness")
    language: str = Field(default="zh", description="Language")
    
    submission_id: Optional[str] = Field(None, description="Submission ID")
    assignment_id: Optional[str] = Field(None, description="Assignment ID")
    subject: Optional[str] = Field(None, description="Subject")
    difficulty: Optional[str] = Field(None, description="Difficulty level")
    max_score: int = Field(default=100, ge=1, description="Maximum score")
    
    stream: bool = Field(default=False, description="Enable streaming response")


class LangGraphGradingResponse(BaseModel):
    """Response schema for LangGraph grading."""
    
    task_id: str
    status: str
    message: str
    result: Optional[dict] = None


class TaskStatusResponse(BaseModel):
    """Response schema for task status."""
    
    task_id: str
    status: str
    phase: str
    progress: int
    result: Optional[dict] = None
    error: Optional[str] = None


@router.post("/tasks", response_model=LangGraphGradingResponse)
async def create_grading_task(
    request: LangGraphGradingRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new LangGraph grading task.
    
    This endpoint creates a grading task and processes it using the LangGraph workflow.
    If streaming is disabled, it runs in the background and returns immediately.
    """
    try:
        logger.info(f"Creating LangGraph grading task for user {current_user.id}")
        
        # Validate input
        if not request.answer_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要提供学生答案文件"
            )
        
        # Get workflow
        workflow = get_langgraph_workflow(db)
        
        if request.stream:
            # Return streaming response
            async def event_generator():
                try:
                    async for event in workflow.execute_stream(
                        question_files=request.question_files,
                        answer_files=request.answer_files,
                        marking_scheme_files=request.marking_scheme_files,
                        task_type=request.task_type,
                        strictness_level=request.strictness_level,
                        language=request.language,
                        submission_id=request.submission_id,
                        assignment_id=request.assignment_id,
                        user_id=str(current_user.id),
                        subject=request.subject,
                        difficulty=request.difficulty,
                        max_score=request.max_score
                    ):
                        import json
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except Exception as e:
                    logger.error(f"Streaming error: {str(e)}", exc_info=True)
                    import json
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream"
            )
        else:
            # Execute in background
            async def run_grading():
                try:
                    await workflow.execute(
                        question_files=request.question_files,
                        answer_files=request.answer_files,
                        marking_scheme_files=request.marking_scheme_files,
                        task_type=request.task_type,
                        strictness_level=request.strictness_level,
                        language=request.language,
                        submission_id=request.submission_id,
                        assignment_id=request.assignment_id,
                        user_id=str(current_user.id),
                        subject=request.subject,
                        difficulty=request.difficulty,
                        max_score=request.max_score
                    )
                except Exception as e:
                    logger.error(f"Background grading error: {str(e)}", exc_info=True)
            
            # Add to background tasks
            background_tasks.add_task(run_grading)
            
            return LangGraphGradingResponse(
                task_id="pending",  # Will be generated in background
                status="queued",
                message="批改任务已创建，正在后台处理"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create grading task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建批改任务失败: {str(e)}"
        )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get status of a grading task.
    
    Returns current progress and results if available.
    """
    try:
        workflow = get_langgraph_workflow(db)
        status_info = await workflow.get_task_status(task_id)
        
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务未找到: {task_id}"
            )
        
        return TaskStatusResponse(**status_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务状态失败: {str(e)}"
        )


@router.delete("/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a running grading task.
    """
    try:
        workflow = get_langgraph_workflow(db)
        success = await workflow.cancel_task(task_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法取消任务"
            )
        
        return {"message": "任务已取消", "task_id": task_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消任务失败: {str(e)}"
        )


@router.post("/tasks/batch", response_model=List[LangGraphGradingResponse])
async def create_batch_grading_tasks(
    requests: List[LangGraphGradingRequest],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create multiple grading tasks in batch.
    
    Useful for grading multiple students' submissions at once.
    """
    try:
        logger.info(f"Creating {len(requests)} batch grading tasks for user {current_user.id}")
        
        responses = []
        workflow = get_langgraph_workflow(db)
        
        for req in requests:
            # Validate
            if not req.answer_files:
                continue
            
            # Execute in background
            async def run_grading(request=req):
                try:
                    await workflow.execute(
                        question_files=request.question_files,
                        answer_files=request.answer_files,
                        marking_scheme_files=request.marking_scheme_files,
                        task_type=request.task_type,
                        strictness_level=request.strictness_level,
                        language=request.language,
                        submission_id=request.submission_id,
                        assignment_id=request.assignment_id,
                        user_id=str(current_user.id),
                        subject=request.subject,
                        difficulty=request.difficulty,
                        max_score=request.max_score
                    )
                except Exception as e:
                    logger.error(f"Batch grading error: {str(e)}", exc_info=True)
            
            background_tasks.add_task(run_grading)
            
            responses.append(LangGraphGradingResponse(
                task_id="pending",
                status="queued",
                message="批改任务已创建"
            ))
        
        return responses
        
    except Exception as e:
        logger.error(f"Failed to create batch tasks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建批量任务失败: {str(e)}"
        )

