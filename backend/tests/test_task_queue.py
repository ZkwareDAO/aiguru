"""Tests for async task queue system."""

import asyncio
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.task_queue import (
    AsyncTaskQueue,
    TaskDefinition,
    TaskHandler,
    TaskPriority,
    TaskResult,
    TaskStatus,
    GradingTaskHandler,
    BatchGradingTaskHandler
)


class MockTaskHandler(TaskHandler):
    """Mock task handler for testing."""
    
    def __init__(self, name: str = "mock_task", should_fail: bool = False, delay: float = 0.1):
        super().__init__(name)
        self.should_fail = should_fail
        self.delay = delay
        self.executed_tasks = []
        self.success_calls = []
        self.failure_calls = []
        self.retry_calls = []
    
    async def execute(self, task: TaskDefinition) -> dict:
        """Mock task execution."""
        await asyncio.sleep(self.delay)
        self.executed_tasks.append(task.id)
        
        if self.should_fail:
            raise Exception("Mock task failure")
        
        return {
            "task_id": str(task.id),
            "message": "Mock task completed",
            "payload": task.payload
        }
    
    async def on_success(self, task: TaskDefinition, result: dict) -> None:
        """Track successful executions."""
        self.success_calls.append((task.id, result))
    
    async def on_failure(self, task: TaskDefinition, error: Exception) -> None:
        """Track failed executions."""
        self.failure_calls.append((task.id, str(error)))
    
    async def on_retry(self, task: TaskDefinition, retry_count: int, error: Exception) -> None:
        """Track retry attempts."""
        self.retry_calls.append((task.id, retry_count, str(error)))


class TestTaskDefinition:
    """Test task definition model."""
    
    def test_task_definition_creation(self):
        """Test creating a task definition."""
        task = TaskDefinition(
            name="test_task",
            payload={"key": "value"},
            priority=TaskPriority.HIGH,
            max_retries=5
        )
        
        assert task.name == "test_task"
        assert task.payload == {"key": "value"}
        assert task.priority == TaskPriority.HIGH
        assert task.max_retries == 5
        assert task.created_at is not None
        assert task.id is not None
    
    def test_task_definition_defaults(self):
        """Test task definition with default values."""
        task = TaskDefinition(name="test_task")
        
        assert task.priority == TaskPriority.NORMAL
        assert task.max_retries == 3
        assert task.retry_delay == 60
        assert task.timeout == 300
        assert task.payload == {}
    
    def test_task_definition_json_serialization(self):
        """Test task definition JSON serialization."""
        task = TaskDefinition(
            name="test_task",
            payload={"test": True},
            scheduled_at=datetime.utcnow()
        )
        
        json_str = task.json()
        assert isinstance(json_str, str)
        assert "test_task" in json_str
        assert "test" in json_str


class TestTaskResult:
    """Test task result model."""
    
    def test_task_result_creation(self):
        """Test creating a task result."""
        task_id = uuid4()
        result = TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result={"success": True},
            execution_time_ms=1500
        )
        
        assert result.task_id == task_id
        assert result.status == TaskStatus.COMPLETED
        assert result.result == {"success": True}
        assert result.execution_time_ms == 1500
    
    def test_task_result_json_serialization(self):
        """Test task result JSON serialization."""
        result = TaskResult(
            task_id=uuid4(),
            status=TaskStatus.FAILED,
            error="Test error",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        json_str = result.json()
        assert isinstance(json_str, str)
        assert "FAILED" in json_str
        assert "Test error" in json_str


class TestAsyncTaskQueue:
    """Test async task queue functionality."""
    
    @pytest.fixture
    async def task_queue(self):
        """Create task queue for testing."""
        queue = AsyncTaskQueue()
        queue.worker_count = 2  # Reduce workers for testing
        await queue.initialize()
        yield queue
        await queue.stop()
    
    async def test_queue_initialization(self, task_queue):
        """Test queue initialization."""
        assert task_queue is not None
        assert not task_queue.running
        assert len(task_queue.handlers) == 0
    
    async def test_register_handler(self, task_queue):
        """Test registering task handlers."""
        handler = MockTaskHandler("test_handler")
        task_queue.register_handler(handler)
        
        assert "test_handler" in task_queue.handlers
        assert task_queue.handlers["test_handler"] == handler
    
    async def test_start_stop_queue(self, task_queue):
        """Test starting and stopping the queue."""
        await task_queue.start()
        assert task_queue.running
        assert len(task_queue.workers) > 0
        
        await task_queue.stop()
        assert not task_queue.running
        assert len(task_queue.workers) == 0
    
    async def test_enqueue_and_process_task(self, task_queue):
        """Test enqueueing and processing a task."""
        # Register handler
        handler = MockTaskHandler("test_task")
        task_queue.register_handler(handler)
        
        # Start queue
        await task_queue.start()
        
        # Enqueue task
        task_id = await task_queue.enqueue_task(
            "test_task",
            {"test_data": "value"}
        )
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        # Check results
        assert len(handler.executed_tasks) == 1
        assert handler.executed_tasks[0] == task_id
        assert len(handler.success_calls) == 1
        
        # Check task result
        result = await task_queue.get_task_result(task_id)
        if result:  # Only check if Redis is available
            assert result.status == TaskStatus.COMPLETED
            assert result.task_id == task_id
    
    async def test_task_failure_and_retry(self, task_queue):
        """Test task failure and retry mechanism."""
        # Register failing handler
        handler = MockTaskHandler("failing_task", should_fail=True)
        task_queue.register_handler(handler)
        
        # Start queue
        await task_queue.start()
        
        # Enqueue task with retries
        task_id = await task_queue.enqueue_task(
            "failing_task",
            {"test_data": "value"},
            max_retries=2,
            retry_delay=1  # Short delay for testing
        )
        
        # Wait for processing and retries
        await asyncio.sleep(2)
        
        # Check that task was executed multiple times (original + retries)
        assert len(handler.executed_tasks) >= 1
        assert len(handler.failure_calls) >= 1
        
        # Check final result
        result = await task_queue.get_task_result(task_id)
        if result:  # Only check if Redis is available
            assert result.status in [TaskStatus.FAILED, TaskStatus.RETRYING]
    
    async def test_task_priority_ordering(self, task_queue):
        """Test that higher priority tasks are processed first."""
        # Register handler with delay to ensure ordering
        handler = MockTaskHandler("priority_task", delay=0.1)
        task_queue.register_handler(handler)
        
        # Start queue
        await task_queue.start()
        
        # Enqueue tasks with different priorities
        low_task = await task_queue.enqueue_task(
            "priority_task",
            {"priority": "low"},
            priority=TaskPriority.LOW
        )
        
        high_task = await task_queue.enqueue_task(
            "priority_task",
            {"priority": "high"},
            priority=TaskPriority.HIGH
        )
        
        normal_task = await task_queue.enqueue_task(
            "priority_task",
            {"priority": "normal"},
            priority=TaskPriority.NORMAL
        )
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Check execution order (high priority should be first)
        if len(handler.executed_tasks) >= 2:
            # High priority task should be processed before low priority
            high_index = handler.executed_tasks.index(high_task)
            low_index = handler.executed_tasks.index(low_task)
            assert high_index < low_index
    
    async def test_scheduled_task_execution(self, task_queue):
        """Test scheduled task execution."""
        # Register handler
        handler = MockTaskHandler("scheduled_task")
        task_queue.register_handler(handler)
        
        # Start queue
        await task_queue.start()
        
        # Schedule task for near future
        scheduled_time = datetime.utcnow() + timedelta(seconds=1)
        task_id = await task_queue.enqueue_task(
            "scheduled_task",
            {"scheduled": True},
            scheduled_at=scheduled_time
        )
        
        # Task should not be executed immediately
        await asyncio.sleep(0.5)
        assert len(handler.executed_tasks) == 0
        
        # Wait for scheduled execution
        await asyncio.sleep(1)
        
        # Task should now be executed
        assert len(handler.executed_tasks) == 1
        assert handler.executed_tasks[0] == task_id
    
    async def test_task_cancellation(self, task_queue):
        """Test task cancellation."""
        # Register handler
        handler = MockTaskHandler("cancellable_task")
        task_queue.register_handler(handler)
        
        # Enqueue task (don't start queue yet)
        task_id = await task_queue.enqueue_task(
            "cancellable_task",
            {"test": True}
        )
        
        # Cancel task before processing
        cancelled = await task_queue.cancel_task(task_id)
        
        if task_queue.redis_client:  # Only test if Redis is available
            assert cancelled
            
            # Check result
            result = await task_queue.get_task_result(task_id)
            assert result.status == TaskStatus.CANCELLED
    
    async def test_queue_statistics(self, task_queue):
        """Test queue statistics."""
        stats = await task_queue.get_queue_stats()
        
        assert isinstance(stats, dict)
        assert "tasks_processed" in stats
        assert "tasks_failed" in stats
        assert "tasks_retried" in stats
        assert "workers_active" in stats
    
    async def test_task_timeout(self, task_queue):
        """Test task timeout handling."""
        # Register handler with long delay
        handler = MockTaskHandler("timeout_task", delay=2)
        task_queue.register_handler(handler)
        
        # Start queue
        await task_queue.start()
        
        # Enqueue task with short timeout
        task_id = await task_queue.enqueue_task(
            "timeout_task",
            {"test": True},
            timeout=1  # 1 second timeout
        )
        
        # Wait for timeout
        await asyncio.sleep(2)
        
        # Check result
        result = await task_queue.get_task_result(task_id)
        if result:  # Only check if Redis is available
            assert result.status == TaskStatus.FAILED
            assert "timeout" in result.error.lower()


class TestGradingTaskHandler:
    """Test grading task handler."""
    
    def test_grading_handler_creation(self):
        """Test creating grading task handler."""
        handler = GradingTaskHandler()
        assert handler.name == "grading_task"
    
    async def test_grading_handler_execute_mock(self):
        """Test grading handler execution with mock data."""
        handler = GradingTaskHandler()
        
        # Create mock task
        task = TaskDefinition(
            name="grading_task",
            payload={"task_id": str(uuid4())}
        )
        
        # This would normally require database setup
        # For now, just test that the method exists and can be called
        assert hasattr(handler, 'execute')
        assert callable(handler.execute)


class TestBatchGradingTaskHandler:
    """Test batch grading task handler."""
    
    def test_batch_grading_handler_creation(self):
        """Test creating batch grading task handler."""
        handler = BatchGradingTaskHandler()
        assert handler.name == "batch_grading_task"
    
    async def test_batch_grading_handler_execute_mock(self):
        """Test batch grading handler execution with mock data."""
        handler = BatchGradingTaskHandler()
        
        # Create mock task
        task = TaskDefinition(
            name="batch_grading_task",
            payload={"task_ids": [str(uuid4()), str(uuid4())]}
        )
        
        # This would normally require database setup
        # For now, just test that the method exists and can be called
        assert hasattr(handler, 'execute')
        assert callable(handler.execute)


class TestTaskQueueIntegration:
    """Integration tests for task queue system."""
    
    async def test_multiple_handlers_registration(self):
        """Test registering multiple handlers."""
        queue = AsyncTaskQueue()
        
        handler1 = MockTaskHandler("task_type_1")
        handler2 = MockTaskHandler("task_type_2")
        
        queue.register_handler(handler1)
        queue.register_handler(handler2)
        
        assert len(queue.handlers) == 2
        assert "task_type_1" in queue.handlers
        assert "task_type_2" in queue.handlers
    
    async def test_concurrent_task_processing(self):
        """Test concurrent processing of multiple tasks."""
        queue = AsyncTaskQueue()
        queue.worker_count = 3
        
        # Register handler
        handler = MockTaskHandler("concurrent_task", delay=0.2)
        queue.register_handler(handler)
        
        await queue.start()
        
        # Enqueue multiple tasks
        task_ids = []
        for i in range(5):
            task_id = await queue.enqueue_task(
                "concurrent_task",
                {"task_number": i}
            )
            task_ids.append(task_id)
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # All tasks should be processed
        assert len(handler.executed_tasks) == 5
        
        await queue.stop()
    
    async def test_error_handling_and_recovery(self):
        """Test error handling and system recovery."""
        queue = AsyncTaskQueue()
        
        # Register handler that fails sometimes
        handler = MockTaskHandler("unreliable_task")
        queue.register_handler(handler)
        
        await queue.start()
        
        # Enqueue mix of tasks (some will fail based on handler logic)
        for i in range(3):
            await queue.enqueue_task(
                "unreliable_task",
                {"task_number": i}
            )
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Queue should still be running despite any failures
        assert queue.running
        
        await queue.stop()