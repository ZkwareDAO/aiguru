"""Grading API v2 - 使用新的Agent架构."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.smart_orchestrator import SmartOrchestrator
from app.core.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/grading", tags=["grading-v2"])

# 全局编排器实例
orchestrator = SmartOrchestrator()


# ============================================================================
# Schemas
# ============================================================================

class GradingRequest(BaseModel):
    """批改请求"""
    submission_id: UUID = Field(..., description="提交ID")
    assignment_id: UUID = Field(..., description="作业ID")
    mode: Optional[str] = Field("auto", description="批改模式: auto/fast/standard/premium")
    max_score: float = Field(100.0, description="满分")
    config: dict = Field(default_factory=dict, description="批改配置")


class GradingResponse(BaseModel):
    """批改响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="消息")


class GradingResult(BaseModel):
    """批改结果"""
    submission_id: str
    assignment_id: str
    status: str
    score: Optional[float]
    max_score: float
    confidence: Optional[float]
    errors: list
    annotations: list
    feedback_text: str
    suggestions: list
    knowledge_points: list
    grading_mode: str
    complexity: Optional[str]
    processing_time_ms: Optional[int]
    from_cache: bool
    error_message: Optional[str]


class CacheStats(BaseModel):
    """缓存统计"""
    enabled: bool
    total_cached: Optional[int]
    ttl_seconds: Optional[int]
    similarity_threshold: Optional[float]
    error: Optional[str]


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/submit", response_model=GradingResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_grading(
    request: GradingRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """提交批改任务
    
    使用新的Agent架构进行批改:
    - 自动评估任务复杂度
    - 智能选择Agent组合
    - 集成缓存优化
    
    成本优化:
    - 简单任务: ~$0.005
    - 中等任务: ~$0.009
    - 复杂任务: ~$0.015
    - 平均成本: ~$0.009 (节省40%)
    """
    try:
        logger.info(
            f"Received grading request: submission={request.submission_id}, "
            f"mode={request.mode}, user={current_user.id}"
        )
        
        # 准备输入数据
        input_data = {
            "submission_id": request.submission_id,
            "assignment_id": request.assignment_id,
            "mode": request.mode,
            "max_score": request.max_score,
            "config": request.config,
        }
        
        # 在后台执行批改
        task_id = str(request.submission_id)
        background_tasks.add_task(
            _execute_grading_task,
            task_id=task_id,
            input_data=input_data
        )
        
        return GradingResponse(
            task_id=task_id,
            status="pending",
            message="批改任务已提交,正在处理中..."
        )
        
    except Exception as e:
        logger.error(f"Failed to submit grading task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交批改任务失败: {str(e)}"
        )


@router.post("/submit-sync", response_model=GradingResult)
async def submit_grading_sync(
    request: GradingRequest,
    current_user: User = Depends(get_current_user)
):
    """同步批改 (立即返回结果)
    
    适用于:
    - 简单任务
    - 需要立即反馈的场景
    - 测试和调试
    
    注意: 可能会超时,建议使用异步接口
    """
    try:
        logger.info(
            f"Received sync grading request: submission={request.submission_id}, "
            f"mode={request.mode}"
        )
        
        # 准备输入数据
        input_data = {
            "submission_id": request.submission_id,
            "assignment_id": request.assignment_id,
            "mode": request.mode,
            "max_score": request.max_score,
            "config": request.config,
        }
        
        # 执行批改
        result = await orchestrator.execute(input_data)
        
        return GradingResult(**result)
        
    except Exception as e:
        logger.error(f"Sync grading failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批改失败: {str(e)}"
        )


@router.get("/result/{submission_id}", response_model=GradingResult)
async def get_grading_result(
    submission_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """获取批改结果
    
    TODO: 从数据库获取结果
    目前返回模拟数据
    """
    # TODO: 实现从数据库获取结果
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="此接口尚未实现,请使用同步接口"
    )


@router.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """获取缓存统计信息
    
    需要管理员权限
    """
    try:
        # TODO: 添加权限检查
        stats = await orchestrator.cache_service.get_cache_stats()
        return CacheStats(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取缓存统计失败: {str(e)}"
        )


@router.delete("/cache/clear")
async def clear_cache(
    current_user: User = Depends(get_current_user)
):
    """清除缓存
    
    需要管理员权限
    """
    try:
        # TODO: 添加权限检查
        deleted = await orchestrator.cache_service.clear_cache()
        
        return {
            "status": "success",
            "message": f"已清除 {deleted} 条缓存记录"
        }
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清除缓存失败: {str(e)}"
        )


# ============================================================================
# Background Tasks
# ============================================================================

async def _execute_grading_task(task_id: str, input_data: dict):
    """后台执行批改任务"""
    try:
        logger.info(f"Executing grading task: {task_id}")
        
        # 执行批改
        result = await orchestrator.execute(input_data)
        
        # TODO: 保存结果到数据库
        # TODO: 发送WebSocket通知
        
        logger.info(f"Grading task completed: {task_id}, status={result['status']}")
        
    except Exception as e:
        logger.error(f"Grading task failed: {task_id}, error={e}", exc_info=True)
        # TODO: 更新任务状态为失败

