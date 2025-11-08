"""API endpoints for AI grading system."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.exceptions import GradingError, NotFoundError, ValidationError
from app.core.permissions import require_permission
from app.models.user import User, UserRole
from app.schemas.grading import (
    BatchGradingRequest,
    BatchGradingResponse,
    GradingStats,
    GradingTaskCreate,
    GradingTaskFilter,
    GradingTaskList,
    GradingTaskResponse,
    GradingTaskUpdate
)
from app.services.grading_service import GradingTaskManager

router = APIRouter(prefix="/grading", tags=["grading"])


@router.post(
    "/tasks",
    response_model=GradingTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create grading task",
    description="Create a new AI grading task for a submission"
)
async def create_grading_task(
    task_data: GradingTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new grading task."""
    try:
        # Only teachers can create grading tasks
        require_permission(current_user, "create_grading_task")
        
        manager = GradingTaskManager(db)
        task = await manager.create_grading_task(task_data)
        
        return task
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/tasks/{task_id}",
    response_model=GradingTaskResponse,
    summary="Get grading task",
    description="Get details of a specific grading task"
)
async def get_grading_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a grading task by ID."""
    try:
        manager = GradingTaskManager(db)
        task = await manager.get_grading_task(task_id)
        
        # Check permissions - users can only see their own tasks or teachers can see all
        if (current_user.role != UserRole.TEACHER and 
            task.submission.student_id != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this grading task"
            )
        
        return task
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put(
    "/tasks/{task_id}",
    response_model=GradingTaskResponse,
    summary="Update grading task",
    description="Update a grading task (system use only)"
)
async def update_grading_task(
    task_id: UUID,
    update_data: GradingTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a grading task."""
    try:
        # Only system or admin users can update grading tasks
        require_permission(current_user, "update_grading_task")
        
        manager = GradingTaskManager(db)
        task = await manager.update_grading_task(task_id, update_data)
        
        return task
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/tasks",
    response_model=GradingTaskList,
    summary="List grading tasks",
    description="List grading tasks with filtering and pagination"
)
async def list_grading_tasks(
    status: Optional[str] = Query(None, description="Filter by task status"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    submission_id: Optional[UUID] = Query(None, description="Filter by submission ID"),
    student_id: Optional[UUID] = Query(None, description="Filter by student ID"),
    assignment_id: Optional[UUID] = Query(None, description="Filter by assignment ID"),
    class_id: Optional[UUID] = Query(None, description="Filter by class ID"),
    created_after: Optional[datetime] = Query(None, description="Filter by creation date (after)"),
    created_before: Optional[datetime] = Query(None, description="Filter by creation date (before)"),
    has_errors: Optional[bool] = Query(None, description="Filter by error status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List grading tasks with filtering."""
    try:
        # Build filters
        filters = GradingTaskFilter(
            status=status,
            task_type=task_type,
            submission_id=submission_id,
            student_id=student_id,
            assignment_id=assignment_id,
            class_id=class_id,
            created_after=created_after,
            created_before=created_before,
            has_errors=has_errors,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # If user is a student, only show their own tasks
        if current_user.role == UserRole.STUDENT:
            filters.student_id = current_user.id
        
        manager = GradingTaskManager(db)
        tasks = await manager.list_grading_tasks(filters)
        
        return tasks
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/tasks/{task_id}/retry",
    response_model=GradingTaskResponse,
    summary="Retry grading task",
    description="Retry a failed grading task"
)
async def retry_grading_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry a failed grading task."""
    try:
        # Only teachers can retry grading tasks
        require_permission(current_user, "retry_grading_task")
        
        manager = GradingTaskManager(db)
        task = await manager.retry_failed_task(task_id)
        
        return task
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=GradingTaskResponse,
    summary="Cancel grading task",
    description="Cancel a pending or processing grading task"
)
async def cancel_grading_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a grading task."""
    try:
        # Only teachers can cancel grading tasks
        require_permission(current_user, "cancel_grading_task")
        
        manager = GradingTaskManager(db)
        task = await manager.cancel_task(task_id)
        
        return task
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/tasks/batch",
    response_model=BatchGradingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create batch grading tasks",
    description="Create multiple grading tasks in batch"
)
async def create_batch_grading_tasks(
    batch_request: BatchGradingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create multiple grading tasks in batch."""
    try:
        # Only teachers can create batch grading tasks
        require_permission(current_user, "create_batch_grading_tasks")
        
        manager = GradingTaskManager(db)
        response = await manager.create_batch_grading_tasks(batch_request)
        
        return response
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/stats",
    response_model=GradingStats,
    summary="Get grading statistics",
    description="Get grading system statistics"
)
async def get_grading_stats(
    start_date: Optional[datetime] = Query(None, description="Start date for statistics"),
    end_date: Optional[datetime] = Query(None, description="End date for statistics"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get grading statistics."""
    try:
        # Only teachers and admins can view grading stats
        require_permission(current_user, "view_grading_stats")
        
        manager = GradingTaskManager(db)
        stats = await manager.get_grading_stats(start_date, end_date)
        
        return stats
        
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/tasks/cleanup",
    summary="Cleanup old tasks",
    description="Clean up old completed/failed grading tasks"
)
async def cleanup_old_grading_tasks(
    days_old: int = Query(30, ge=1, le=365, description="Age in days for cleanup"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clean up old grading tasks."""
    try:
        # Only admins can cleanup old tasks
        require_permission(current_user, "cleanup_grading_tasks")
        
        manager = GradingTaskManager(db)
        deleted_count = await manager.cleanup_old_tasks(days_old)
        
        return {"message": f"Cleaned up {deleted_count} old grading tasks"}
        
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/tasks/{task_id}/analysis",
    summary="Get grading result analysis",
    description="Get detailed analysis of a grading result"
)
async def get_grading_result_analysis(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analysis of a grading result."""
    try:
        # Check permissions
        require_permission(current_user, "view_grading_analysis")
        
        from app.services.grading_result_processor import GradingResultAnalyzer
        analyzer = GradingResultAnalyzer(db)
        
        # Get the grading task first to get the result
        manager = GradingTaskManager(db)
        task = await manager.get_grading_task(task_id)
        
        if not task.result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No grading result available for analysis"
            )
        
        # Convert result dict to GradingResult object
        from app.schemas.grading import GradingResult
        grading_result = GradingResult(**task.result)
        
        analysis = await analyzer.analyze_grading_result(task_id, grading_result)
        
        return analysis
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/tasks/{task_id}/quality",
    summary="Get grading quality assessment",
    description="Get quality assessment of a grading result"
)
async def get_grading_quality_assessment(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get quality assessment of a grading result."""
    try:
        # Check permissions
        require_permission(current_user, "view_grading_quality")
        
        from app.services.grading_result_processor import GradingResultAnalyzer
        analyzer = GradingResultAnalyzer(db)
        
        # Get the grading task first
        manager = GradingTaskManager(db)
        task = await manager.get_grading_task(task_id)
        
        if not task.result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No grading result available for quality assessment"
            )
        
        # Convert result dict to GradingResult object
        from app.schemas.grading import GradingResult
        grading_result = GradingResult(**task.result)
        
        quality_assessment = await analyzer.assess_grading_quality(task_id, grading_result)
        
        return quality_assessment
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/assignments/{assignment_id}/anomalies",
    summary="Detect grading anomalies",
    description="Detect anomalies in grading results for an assignment"
)
async def detect_grading_anomalies(
    assignment_id: UUID,
    threshold: float = Query(2.0, ge=1.0, le=5.0, description="Standard deviation threshold"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detect grading anomalies for an assignment."""
    try:
        # Check permissions
        require_permission(current_user, "detect_grading_anomalies")
        
        from app.services.grading_result_processor import GradingResultAnalyzer
        analyzer = GradingResultAnalyzer(db)
        
        anomalies = await analyzer.detect_grading_anomalies(assignment_id, threshold)
        
        return {
            "assignment_id": str(assignment_id),
            "threshold": threshold,
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies
        }
        
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/assignments/{assignment_id}/insights",
    summary="Get grading insights",
    description="Get insights about grading patterns and trends for an assignment"
)
async def get_grading_insights(
    assignment_id: UUID,
    time_period_days: int = Query(30, ge=1, le=365, description="Time period for analysis"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get grading insights for an assignment."""
    try:
        # Check permissions
        require_permission(current_user, "view_grading_insights")
        
        from app.services.grading_result_processor import GradingResultAnalyzer
        analyzer = GradingResultAnalyzer(db)
        
        insights = await analyzer.generate_grading_insights(assignment_id, time_period_days)
        
        return insights
        
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/tasks/async",
    response_model=GradingTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create async grading task",
    description="Create a grading task and queue it for async processing"
)
async def create_async_grading_task(
    task_data: GradingTaskCreate,
    priority: int = Query(1, ge=0, le=3, description="Task priority (0=low, 1=normal, 2=high, 3=urgent)"),
    scheduled_at: Optional[datetime] = Query(None, description="Schedule task for future execution"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a grading task and queue it for async processing."""
    try:
        # Only teachers can create grading tasks
        require_permission(current_user, "create_grading_task")
        
        from app.services.async_grading_service import get_async_grading_service
        from app.services.task_queue import TaskPriority
        
        service = await get_async_grading_service(db)
        
        # Convert priority to enum
        task_priority = TaskPriority(priority)
        
        if scheduled_at:
            task = await service.schedule_grading_task(task_data, scheduled_at, task_priority)
        else:
            task = await service.create_and_queue_grading_task(task_data, task_priority)
        
        return task
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/tasks/batch/async",
    response_model=BatchGradingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create async batch grading tasks",
    description="Create multiple grading tasks and queue them for async processing"
)
async def create_async_batch_grading_tasks(
    batch_request: BatchGradingRequest,
    priority: int = Query(1, ge=0, le=3, description="Task priority"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create multiple grading tasks and queue them for async processing."""
    try:
        # Only teachers can create batch grading tasks
        require_permission(current_user, "create_batch_grading_tasks")
        
        from app.services.async_grading_service import get_async_grading_service
        from app.services.task_queue import TaskPriority
        
        service = await get_async_grading_service(db)
        task_priority = TaskPriority(priority)
        
        response = await service.create_and_queue_batch_grading_tasks(
            batch_request, task_priority
        )
        
        return response
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/queue/status",
    summary="Get queue status",
    description="Get current task queue status and statistics"
)
async def get_queue_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current task queue status."""
    try:
        # Check permissions
        require_permission(current_user, "view_grading_stats")
        
        from app.services.async_grading_service import get_async_grading_service
        
        service = await get_async_grading_service(db)
        status_info = await service.get_queue_status()
        
        return status_info
        
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/tasks/{task_id}/cancel/async",
    summary="Cancel queued task",
    description="Cancel a queued grading task"
)
async def cancel_queued_grading_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a queued grading task."""
    try:
        # Only teachers can cancel grading tasks
        require_permission(current_user, "cancel_grading_task")
        
        from app.services.async_grading_service import get_async_grading_service
        
        service = await get_async_grading_service(db)
        cancelled = await service.cancel_queued_task(task_id)
        
        if cancelled:
            return {"message": f"Successfully cancelled task {task_id}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or cannot be cancelled"
            )
        
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/tasks/{task_id}/retry/async",
    summary="Retry failed task",
    description="Retry a failed grading task with high priority"
)
async def retry_failed_grading_task_async(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry a failed grading task with high priority."""
    try:
        # Only teachers can retry grading tasks
        require_permission(current_user, "retry_grading_task")
        
        from app.services.async_grading_service import get_async_grading_service
        
        service = await get_async_grading_service(db)
        retried = await service.retry_failed_task(task_id)
        
        if retried:
            return {"message": f"Successfully queued retry for task {task_id}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or cannot be retried"
            )
        
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/monitor/performance",
    summary="Get performance metrics",
    description="Get performance metrics for grading system"
)
async def get_grading_performance_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get performance metrics for grading system."""
    try:
        # Check permissions
        require_permission(current_user, "view_grading_stats")
        
        from app.services.async_grading_service import get_grading_task_monitor
        
        monitor = await get_grading_task_monitor(db)
        metrics = await monitor.get_performance_metrics()
        
        return metrics
        
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/monitor/health",
    summary="Get system health",
    description="Get health status of grading system"
)
async def get_grading_system_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get health status of grading system."""
    try:
        # Check permissions
        require_permission(current_user, "view_grading_stats")
        
        from app.services.async_grading_service import get_grading_task_monitor
        
        monitor = await get_grading_task_monitor(db)
        health = await monitor.check_system_health()
        
        return health
        
    except GradingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )