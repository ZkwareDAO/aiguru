"""Async grading service that integrates with the task queue."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import GradingError
from app.schemas.grading import (
    BatchGradingRequest,
    BatchGradingResponse,
    GradingTaskCreate,
    GradingTaskResponse
)
from app.services.grading_service import GradingTaskManager
from app.services.task_queue import TaskPriority, get_task_queue

logger = logging.getLogger(__name__)


class AsyncGradingService:
    """Service for managing async grading operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.task_manager = GradingTaskManager(db)
        self.task_queue = get_task_queue()
    
    async def create_and_queue_grading_task(
        self,
        task_data: GradingTaskCreate,
        priority: TaskPriority = TaskPriority.NORMAL,
        scheduled_at: Optional[datetime] = None
    ) -> GradingTaskResponse:
        """Create a grading task and queue it for async processing."""
        try:
            # Create the grading task
            grading_task = await self.task_manager.create_grading_task(task_data)
            
            # Queue the task for async processing
            queue_task_id = await self.task_queue.enqueue_task(
                task_name="grading_task",
                payload={"task_id": str(grading_task.id)},
                priority=priority,
                scheduled_at=scheduled_at,
                max_retries=3,
                timeout=600,  # 10 minutes timeout
                expires_at=datetime.utcnow() + timedelta(hours=2)  # Expire in 2 hours
            )
            
            logger.info(
                f"Created grading task {grading_task.id} and queued as {queue_task_id} "
                f"with priority {priority}"
            )
            
            return grading_task
            
        except Exception as e:
            logger.error(f"Failed to create and queue grading task: {str(e)}")
            raise GradingError(f"Failed to create and queue grading task: {str(e)}")
    
    async def create_and_queue_batch_grading_tasks(
        self,
        batch_request: BatchGradingRequest,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> BatchGradingResponse:
        """Create batch grading tasks and queue them for async processing."""
        try:
            # Create individual grading tasks
            created_tasks = []
            failed_submissions = []
            
            for submission_id in batch_request.submission_ids:
                try:
                    task_data = GradingTaskCreate(
                        submission_id=submission_id,
                        task_type=batch_request.task_type
                    )
                    grading_task = await self.task_manager.create_grading_task(task_data)
                    created_tasks.append(grading_task.id)
                except Exception as e:
                    logger.warning(f"Failed to create grading task for submission {submission_id}: {str(e)}")
                    failed_submissions.append(submission_id)
            
            if not created_tasks:
                return BatchGradingResponse(
                    created_tasks=[],
                    failed_submissions=failed_submissions,
                    total_requested=len(batch_request.submission_ids),
                    total_created=0
                )
            
            # Decide on processing strategy based on batch size
            if len(created_tasks) <= 5:
                # Small batch: queue individual tasks
                for task_id in created_tasks:
                    await self.task_queue.enqueue_task(
                        task_name="grading_task",
                        payload={"task_id": str(task_id)},
                        priority=priority,
                        max_retries=3,
                        timeout=600
                    )
                
                logger.info(f"Queued {len(created_tasks)} individual grading tasks")
                
            else:
                # Large batch: queue as batch task for better efficiency
                queue_task_id = await self.task_queue.enqueue_task(
                    task_name="batch_grading_task",
                    payload={"task_ids": [str(tid) for tid in created_tasks]},
                    priority=priority,
                    max_retries=2,
                    timeout=1800,  # 30 minutes for batch
                    expires_at=datetime.utcnow() + timedelta(hours=4)
                )
                
                logger.info(f"Queued batch grading task {queue_task_id} for {len(created_tasks)} tasks")
            
            # Estimate completion time
            estimated_time = self._estimate_completion_time(len(created_tasks))
            
            return BatchGradingResponse(
                created_tasks=created_tasks,
                failed_submissions=failed_submissions,
                total_requested=len(batch_request.submission_ids),
                total_created=len(created_tasks),
                estimated_completion_time_minutes=estimated_time
            )
            
        except Exception as e:
            logger.error(f"Failed to create and queue batch grading tasks: {str(e)}")
            raise GradingError(f"Failed to create and queue batch grading tasks: {str(e)}")
    
    async def schedule_grading_task(
        self,
        task_data: GradingTaskCreate,
        scheduled_at: datetime,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> GradingTaskResponse:
        """Schedule a grading task for future execution."""
        if scheduled_at <= datetime.utcnow():
            raise GradingError("Scheduled time must be in the future")
        
        return await self.create_and_queue_grading_task(
            task_data, priority, scheduled_at
        )
    
    async def get_queue_status(self) -> Dict:
        """Get current queue status and statistics."""
        try:
            stats = await self.task_queue.get_queue_stats()
            
            # Add grading-specific information
            grading_stats = await self.task_manager.get_grading_stats()
            
            return {
                "queue_stats": stats,
                "grading_stats": grading_stats.__dict__,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {str(e)}")
            raise GradingError(f"Failed to get queue status: {str(e)}")
    
    async def cancel_queued_task(self, task_id: UUID) -> bool:
        """Cancel a queued grading task."""
        try:
            # Try to cancel from queue first
            cancelled_from_queue = await self.task_queue.cancel_task(task_id)
            
            if cancelled_from_queue:
                # Also cancel the grading task
                await self.task_manager.cancel_task(task_id)
                logger.info(f"Cancelled queued grading task {task_id}")
                return True
            else:
                # Task might already be processing, try to cancel grading task only
                try:
                    await self.task_manager.cancel_task(task_id)
                    logger.info(f"Cancelled processing grading task {task_id}")
                    return True
                except Exception:
                    logger.warning(f"Could not cancel grading task {task_id} - may already be completed")
                    return False
            
        except Exception as e:
            logger.error(f"Failed to cancel queued task {task_id}: {str(e)}")
            return False
    
    async def retry_failed_task(
        self,
        task_id: UUID,
        priority: TaskPriority = TaskPriority.HIGH
    ) -> bool:
        """Retry a failed grading task with higher priority."""
        try:
            # Reset the grading task
            await self.task_manager.retry_failed_task(task_id)
            
            # Queue for processing with higher priority
            queue_task_id = await self.task_queue.enqueue_task(
                task_name="grading_task",
                payload={"task_id": str(task_id)},
                priority=priority,
                max_retries=2,  # Fewer retries for manual retry
                timeout=600
            )
            
            logger.info(f"Retried grading task {task_id} as queue task {queue_task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to retry grading task {task_id}: {str(e)}")
            return False
    
    async def process_urgent_task(
        self,
        task_data: GradingTaskCreate
    ) -> GradingTaskResponse:
        """Process a grading task with urgent priority."""
        return await self.create_and_queue_grading_task(
            task_data,
            priority=TaskPriority.URGENT
        )
    
    async def get_task_queue_result(self, task_id: UUID) -> Optional[Dict]:
        """Get task queue result for a grading task."""
        try:
            result = await self.task_queue.get_task_result(task_id)
            return result.dict() if result else None
        except Exception as e:
            logger.error(f"Failed to get task queue result for {task_id}: {str(e)}")
            return None
    
    async def cleanup_old_queue_tasks(self, days_old: int = 7) -> int:
        """Clean up old completed/failed tasks from the queue."""
        # This would require additional Redis operations to clean up old results
        # For now, we rely on Redis TTL for automatic cleanup
        logger.info(f"Queue cleanup requested for tasks older than {days_old} days")
        return 0
    
    def _estimate_completion_time(self, task_count: int) -> int:
        """Estimate completion time for tasks in minutes."""
        # Base time per task (2 minutes average)
        base_time_per_task = 2
        
        # Account for queue processing and concurrency
        worker_count = self.task_queue.worker_count
        concurrent_processing = min(task_count, worker_count)
        
        # Calculate estimated time
        if concurrent_processing > 0:
            estimated_minutes = (task_count * base_time_per_task) / concurrent_processing
            # Add buffer for queue overhead
            estimated_minutes = int(estimated_minutes * 1.2)
        else:
            estimated_minutes = task_count * base_time_per_task
        
        return max(estimated_minutes, 1)  # At least 1 minute


# Service factory function
async def get_async_grading_service(db: AsyncSession) -> AsyncGradingService:
    """Get async grading service instance."""
    return AsyncGradingService(db)


class GradingTaskMonitor:
    """Monitor for grading task performance and health."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.task_manager = GradingTaskManager(db)
        self.task_queue = get_task_queue()
    
    async def get_performance_metrics(self) -> Dict:
        """Get performance metrics for grading tasks."""
        try:
            # Get queue stats
            queue_stats = await self.task_queue.get_queue_stats()
            
            # Get grading stats
            grading_stats = await self.task_manager.get_grading_stats()
            
            # Calculate performance metrics
            total_processed = queue_stats.get("tasks_processed", 0)
            total_failed = queue_stats.get("tasks_failed", 0)
            
            success_rate = (
                (total_processed - total_failed) / total_processed
                if total_processed > 0 else 0
            )
            
            return {
                "queue_performance": {
                    "tasks_processed": total_processed,
                    "tasks_failed": total_failed,
                    "success_rate": success_rate,
                    "workers_active": queue_stats.get("workers_active", 0),
                    "pending_tasks": queue_stats.get("pending_tasks", 0)
                },
                "grading_performance": {
                    "total_tasks": grading_stats.total_tasks,
                    "completed_tasks": grading_stats.completed_tasks,
                    "failed_tasks": grading_stats.failed_tasks,
                    "success_rate": grading_stats.success_rate,
                    "average_processing_time": grading_stats.average_processing_time_seconds
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {str(e)}")
            return {"error": str(e)}
    
    async def check_system_health(self) -> Dict:
        """Check system health for grading operations."""
        health_status = {
            "overall_status": "healthy",
            "issues": [],
            "warnings": []
        }
        
        try:
            # Check queue health
            queue_stats = await self.task_queue.get_queue_stats()
            
            # Check for stuck tasks
            processing_tasks = queue_stats.get("processing_tasks", 0)
            if processing_tasks > 10:
                health_status["warnings"].append(
                    f"High number of processing tasks: {processing_tasks}"
                )
            
            # Check for failed tasks
            failed_tasks = queue_stats.get("tasks_failed", 0)
            total_tasks = queue_stats.get("tasks_processed", 0)
            
            if total_tasks > 0:
                failure_rate = failed_tasks / total_tasks
                if failure_rate > 0.1:  # More than 10% failure rate
                    health_status["issues"].append(
                        f"High failure rate: {failure_rate:.2%}"
                    )
                    health_status["overall_status"] = "degraded"
            
            # Check worker status
            workers_running = queue_stats.get("workers_running", 0)
            if workers_running == 0:
                health_status["issues"].append("No workers running")
                health_status["overall_status"] = "unhealthy"
            
            # Check pending task backlog
            pending_tasks = queue_stats.get("pending_tasks", 0)
            if pending_tasks > 50:
                health_status["warnings"].append(
                    f"Large task backlog: {pending_tasks} pending tasks"
                )
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "overall_status": "unhealthy",
                "issues": [f"Health check failed: {str(e)}"],
                "warnings": []
            }


# Monitor factory function
async def get_grading_task_monitor(db: AsyncSession) -> GradingTaskMonitor:
    """Get grading task monitor instance."""
    return GradingTaskMonitor(db)