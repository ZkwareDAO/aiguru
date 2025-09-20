"""Async task queue system for grading and other background tasks."""

import asyncio
import json
import logging
import traceback
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4

import redis.asyncio as redis
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.database import get_db_session

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(int, Enum):
    """Task priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class TaskDefinition(BaseModel):
    """Task definition model."""
    
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Task name/type")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task payload data")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: int = Field(default=60, ge=1, description="Retry delay in seconds")
    timeout: int = Field(default=300, ge=1, description="Task timeout in seconds")
    
    # Scheduling
    scheduled_at: Optional[datetime] = Field(None, description="When to execute the task")
    expires_at: Optional[datetime] = Field(None, description="When the task expires")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = Field(None, description="User who created the task")
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class TaskResult(BaseModel):
    """Task execution result."""
    
    task_id: UUID
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_traceback: Optional[str] = None
    
    # Execution info
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[int] = None
    retry_count: int = 0
    
    # Worker info
    worker_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class TaskHandler:
    """Base class for task handlers."""
    
    def __init__(self, name: str):
        self.name = name
    
    async def execute(self, task: TaskDefinition) -> Dict[str, Any]:
        """Execute the task and return result."""
        raise NotImplementedError("Subclasses must implement execute method")
    
    async def on_success(self, task: TaskDefinition, result: Dict[str, Any]) -> None:
        """Called when task completes successfully."""
        pass
    
    async def on_failure(self, task: TaskDefinition, error: Exception) -> None:
        """Called when task fails."""
        pass
    
    async def on_retry(self, task: TaskDefinition, retry_count: int, error: Exception) -> None:
        """Called when task is being retried."""
        pass


class AsyncTaskQueue:
    """Async task queue with Redis backend."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.settings = get_settings()
        self.redis_url = redis_url or self.settings.REDIS_URL
        self.redis_client: Optional[redis.Redis] = None
        
        # Queue configuration
        self.queue_name = "task_queue"
        self.processing_queue = "processing_queue"
        self.result_queue = "result_queue"
        self.scheduled_queue = "scheduled_queue"
        
        # Worker configuration
        self.workers: List[asyncio.Task] = []
        self.worker_count = 3
        self.running = False
        
        # Task handlers
        self.handlers: Dict[str, TaskHandler] = {}
        
        # Monitoring
        self.stats = {
            "tasks_processed": 0,
            "tasks_failed": 0,
            "tasks_retried": 0,
            "workers_active": 0
        }
    
    async def initialize(self) -> None:
        """Initialize the task queue."""
        if self.redis_url:
            self.redis_client = redis.from_url(self.redis_url)
            try:
                await self.redis_client.ping()
                logger.info("Connected to Redis for task queue")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.redis_client = None
        else:
            logger.warning("No Redis URL configured, using in-memory queue")
            self.redis_client = None
    
    async def start(self) -> None:
        """Start the task queue workers."""
        if self.running:
            return
        
        await self.initialize()
        self.running = True
        
        # Start worker tasks
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
        
        # Start scheduler task
        scheduler = asyncio.create_task(self._scheduler())
        self.workers.append(scheduler)
        
        logger.info(f"Started task queue with {self.worker_count} workers")
    
    async def stop(self) -> None:
        """Stop the task queue workers."""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Stopped task queue")
    
    def register_handler(self, handler: TaskHandler) -> None:
        """Register a task handler."""
        self.handlers[handler.name] = handler
        logger.info(f"Registered task handler: {handler.name}")
    
    async def enqueue_task(
        self,
        task_name: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        **kwargs
    ) -> UUID:
        """Enqueue a task for processing."""
        task = TaskDefinition(
            name=task_name,
            payload=payload,
            priority=priority,
            scheduled_at=scheduled_at,
            **kwargs
        )
        
        if scheduled_at and scheduled_at > datetime.utcnow():
            # Schedule for later execution
            await self._enqueue_scheduled_task(task)
        else:
            # Enqueue for immediate processing
            await self._enqueue_immediate_task(task)
        
        logger.info(f"Enqueued task {task.id} ({task_name}) with priority {priority}")
        return task.id
    
    async def get_task_result(self, task_id: UUID) -> Optional[TaskResult]:
        """Get task result by ID."""
        if self.redis_client:
            result_data = await self.redis_client.get(f"result:{task_id}")
            if result_data:
                return TaskResult(**json.loads(result_data))
        
        return None
    
    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a pending task."""
        if self.redis_client:
            # Remove from queue
            removed = await self.redis_client.lrem(self.queue_name, 0, str(task_id))
            if removed:
                # Mark as cancelled
                result = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.CANCELLED,
                    completed_at=datetime.utcnow()
                )
                await self._store_result(result)
                return True
        
        return False
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        stats = self.stats.copy()
        
        if self.redis_client:
            stats.update({
                "pending_tasks": await self.redis_client.llen(self.queue_name),
                "processing_tasks": await self.redis_client.llen(self.processing_queue),
                "scheduled_tasks": await self.redis_client.zcard(self.scheduled_queue)
            })
        
        stats["workers_running"] = len([w for w in self.workers if not w.done()])
        
        return stats
    
    async def _worker(self, worker_id: str) -> None:
        """Worker coroutine that processes tasks."""
        logger.info(f"Task worker {worker_id} started")
        
        while self.running:
            try:
                # Get next task
                task_id = await self._dequeue_task()
                if not task_id:
                    await asyncio.sleep(1)  # No tasks available
                    continue
                
                self.stats["workers_active"] += 1
                
                try:
                    # Process the task
                    await self._process_task(task_id, worker_id)
                    self.stats["tasks_processed"] += 1
                    
                except Exception as e:
                    logger.error(f"Worker {worker_id} failed to process task {task_id}: {e}")
                    self.stats["tasks_failed"] += 1
                
                finally:
                    self.stats["workers_active"] -= 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} encountered error: {e}")
                await asyncio.sleep(5)  # Back off on error
        
        logger.info(f"Task worker {worker_id} stopped")
    
    async def _scheduler(self) -> None:
        """Scheduler coroutine that moves scheduled tasks to the main queue."""
        logger.info("Task scheduler started")
        
        while self.running:
            try:
                if self.redis_client:
                    # Get tasks scheduled for now or earlier
                    now = datetime.utcnow().timestamp()
                    scheduled_tasks = await self.redis_client.zrangebyscore(
                        self.scheduled_queue, 0, now, withscores=True
                    )
                    
                    for task_data, score in scheduled_tasks:
                        task = TaskDefinition(**json.loads(task_data))
                        
                        # Move to main queue
                        await self._enqueue_immediate_task(task)
                        
                        # Remove from scheduled queue
                        await self.redis_client.zrem(self.scheduled_queue, task_data)
                        
                        logger.info(f"Moved scheduled task {task.id} to main queue")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler encountered error: {e}")
                await asyncio.sleep(30)  # Back off on error
        
        logger.info("Task scheduler stopped")
    
    async def _enqueue_immediate_task(self, task: TaskDefinition) -> None:
        """Enqueue task for immediate processing."""
        if self.redis_client:
            # Store task data
            await self.redis_client.set(
                f"task:{task.id}",
                task.json(),
                ex=3600  # Expire in 1 hour
            )
            
            # Add to priority queue (higher priority = higher score)
            await self.redis_client.zadd(
                self.queue_name,
                {str(task.id): task.priority.value}
            )
        else:
            # In-memory fallback (for testing)
            logger.warning(f"No Redis available, task {task.id} queued in memory")
    
    async def _enqueue_scheduled_task(self, task: TaskDefinition) -> None:
        """Enqueue task for scheduled execution."""
        if self.redis_client and task.scheduled_at:
            # Store task data
            await self.redis_client.set(
                f"task:{task.id}",
                task.json(),
                ex=86400  # Expire in 24 hours
            )
            
            # Add to scheduled queue with timestamp as score
            await self.redis_client.zadd(
                self.scheduled_queue,
                {task.json(): task.scheduled_at.timestamp()}
            )
    
    async def _dequeue_task(self) -> Optional[UUID]:
        """Dequeue next task for processing."""
        if self.redis_client:
            # Get highest priority task
            result = await self.redis_client.zpopmax(self.queue_name)
            if result:
                task_id_str, priority = result[0]
                task_id = UUID(task_id_str)
                
                # Move to processing queue
                await self.redis_client.lpush(self.processing_queue, str(task_id))
                
                return task_id
        
        return None
    
    async def _process_task(self, task_id: UUID, worker_id: str) -> None:
        """Process a single task."""
        start_time = datetime.utcnow()
        
        try:
            # Get task data
            if self.redis_client:
                task_data = await self.redis_client.get(f"task:{task_id}")
                if not task_data:
                    logger.error(f"Task {task_id} data not found")
                    return
                
                task = TaskDefinition(**json.loads(task_data))
            else:
                logger.error(f"Cannot process task {task_id} without Redis")
                return
            
            # Check if task has expired
            if task.expires_at and task.expires_at < datetime.utcnow():
                result = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error="Task expired",
                    started_at=start_time,
                    completed_at=datetime.utcnow(),
                    worker_id=worker_id
                )
                await self._store_result(result)
                return
            
            # Get task handler
            handler = self.handlers.get(task.name)
            if not handler:
                result = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error=f"No handler registered for task type: {task.name}",
                    started_at=start_time,
                    completed_at=datetime.utcnow(),
                    worker_id=worker_id
                )
                await self._store_result(result)
                return
            
            # Execute task with timeout
            try:
                task_result = await asyncio.wait_for(
                    handler.execute(task),
                    timeout=task.timeout
                )
                
                # Task completed successfully
                end_time = datetime.utcnow()
                execution_time = int((end_time - start_time).total_seconds() * 1000)
                
                result = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    result=task_result,
                    started_at=start_time,
                    completed_at=end_time,
                    execution_time_ms=execution_time,
                    worker_id=worker_id
                )
                
                await self._store_result(result)
                await handler.on_success(task, task_result)
                
                logger.info(f"Task {task_id} completed successfully in {execution_time}ms")
                
            except asyncio.TimeoutError:
                # Task timed out
                result = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error=f"Task timed out after {task.timeout} seconds",
                    started_at=start_time,
                    completed_at=datetime.utcnow(),
                    worker_id=worker_id
                )
                await self._store_result(result)
                await handler.on_failure(task, TimeoutError("Task timeout"))
                
            except Exception as e:
                # Task failed
                error_traceback = traceback.format_exc()
                
                # Check if we should retry
                current_result = await self.get_task_result(task_id)
                retry_count = current_result.retry_count if current_result else 0
                
                if retry_count < task.max_retries:
                    # Schedule retry
                    retry_count += 1
                    retry_at = datetime.utcnow() + timedelta(seconds=task.retry_delay)
                    
                    task.scheduled_at = retry_at
                    await self._enqueue_scheduled_task(task)
                    
                    result = TaskResult(
                        task_id=task_id,
                        status=TaskStatus.RETRYING,
                        error=str(e),
                        error_traceback=error_traceback,
                        started_at=start_time,
                        completed_at=datetime.utcnow(),
                        retry_count=retry_count,
                        worker_id=worker_id
                    )
                    
                    await self._store_result(result)
                    await handler.on_retry(task, retry_count, e)
                    
                    self.stats["tasks_retried"] += 1
                    logger.warning(f"Task {task_id} failed, scheduling retry {retry_count}/{task.max_retries}")
                    
                else:
                    # Max retries exceeded
                    result = TaskResult(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        error=str(e),
                        error_traceback=error_traceback,
                        started_at=start_time,
                        completed_at=datetime.utcnow(),
                        retry_count=retry_count,
                        worker_id=worker_id
                    )
                    
                    await self._store_result(result)
                    await handler.on_failure(task, e)
                    
                    logger.error(f"Task {task_id} failed permanently after {retry_count} retries: {e}")
        
        finally:
            # Remove from processing queue
            if self.redis_client:
                await self.redis_client.lrem(self.processing_queue, 0, str(task_id))
    
    async def _store_result(self, result: TaskResult) -> None:
        """Store task result."""
        if self.redis_client:
            await self.redis_client.set(
                f"result:{result.task_id}",
                result.json(),
                ex=86400  # Keep results for 24 hours
            )


# Global task queue instance
_task_queue: Optional[AsyncTaskQueue] = None


def get_task_queue() -> AsyncTaskQueue:
    """Get global task queue instance."""
    global _task_queue
    if _task_queue is None:
        _task_queue = AsyncTaskQueue()
    return _task_queue


# Grading task handler
class GradingTaskHandler(TaskHandler):
    """Handler for AI grading tasks."""
    
    def __init__(self):
        super().__init__("grading_task")
    
    async def execute(self, task: TaskDefinition) -> Dict[str, Any]:
        """Execute grading task."""
        from app.services.grading_processor import GradingProcessor
        
        task_id = UUID(task.payload["task_id"])
        
        async with get_db_session() as db:
            processor = GradingProcessor(db)
            success = await processor.process_grading_task(task_id)
            
            return {
                "task_id": str(task_id),
                "success": success,
                "processed_at": datetime.utcnow().isoformat()
            }
    
    async def on_success(self, task: TaskDefinition, result: Dict[str, Any]) -> None:
        """Handle successful grading."""
        logger.info(f"Grading task {task.payload['task_id']} completed successfully")
    
    async def on_failure(self, task: TaskDefinition, error: Exception) -> None:
        """Handle failed grading."""
        logger.error(f"Grading task {task.payload['task_id']} failed: {error}")
    
    async def on_retry(self, task: TaskDefinition, retry_count: int, error: Exception) -> None:
        """Handle grading retry."""
        logger.warning(f"Grading task {task.payload['task_id']} retry {retry_count}: {error}")


# Batch grading task handler
class BatchGradingTaskHandler(TaskHandler):
    """Handler for batch AI grading tasks."""
    
    def __init__(self):
        super().__init__("batch_grading_task")
    
    async def execute(self, task: TaskDefinition) -> Dict[str, Any]:
        """Execute batch grading task."""
        from app.services.grading_processor import GradingProcessor
        
        task_ids = [UUID(tid) for tid in task.payload["task_ids"]]
        
        async with get_db_session() as db:
            processor = GradingProcessor(db)
            results = await processor.process_batch_grading_tasks(task_ids)
            
            success_count = sum(1 for success in results.values() if success)
            
            return {
                "task_ids": [str(tid) for tid in task_ids],
                "total_tasks": len(task_ids),
                "successful_tasks": success_count,
                "failed_tasks": len(task_ids) - success_count,
                "results": {str(k): v for k, v in results.items()},
                "processed_at": datetime.utcnow().isoformat()
            }
    
    async def on_success(self, task: TaskDefinition, result: Dict[str, Any]) -> None:
        """Handle successful batch grading."""
        logger.info(f"Batch grading completed: {result['successful_tasks']}/{result['total_tasks']} successful")
    
    async def on_failure(self, task: TaskDefinition, error: Exception) -> None:
        """Handle failed batch grading."""
        logger.error(f"Batch grading failed: {error}")


# Initialize task queue with handlers
async def initialize_task_queue() -> AsyncTaskQueue:
    """Initialize task queue with default handlers."""
    queue = get_task_queue()
    
    # Register handlers
    queue.register_handler(GradingTaskHandler())
    queue.register_handler(BatchGradingTaskHandler())
    
    # Start the queue
    await queue.start()
    
    return queue


# Cleanup function
async def cleanup_task_queue() -> None:
    """Cleanup task queue."""
    queue = get_task_queue()
    await queue.stop()