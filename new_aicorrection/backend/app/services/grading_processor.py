"""Grading processor service that handles the actual grading workflow."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.core.exceptions import GradingError, NotFoundError
from app.models.ai import GradingTask, GradingTaskStatus
from app.models.assignment import Assignment, Submission, SubmissionStatus
from app.models.file import File
from app.schemas.grading import GradingRequest, GradingResult, GradingTaskUpdate
from app.services.ai_grading_api import get_ai_grading_api_client
from app.services.grading_service import GradingTaskManager

logger = logging.getLogger(__name__)


class GradingProcessor:
    """Service for processing grading tasks using AI grading API."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.task_manager = GradingTaskManager(db)
        self._processing_tasks: Dict[UUID, asyncio.Task] = {}
    
    async def process_grading_task(self, task_id: UUID) -> bool:
        """Process a single grading task."""
        try:
            # Get the grading task
            task = await self._get_grading_task(task_id)
            
            if task.status != GradingTaskStatus.PENDING:
                logger.warning(f"Task {task_id} is not in pending status: {task.status}")
                return False
            
            # Mark task as processing
            await self.task_manager.update_grading_task(
                task_id,
                GradingTaskUpdate(
                    status=GradingTaskStatus.PROCESSING,
                    progress=10,
                    started_at=datetime.utcnow()
                )
            )
            
            # Get submission data
            submission = await self._get_submission_with_details(task.submission_id)
            
            # Prepare grading request
            grading_request = await self._prepare_grading_request(submission, task)
            
            # Update progress
            await self.task_manager.update_grading_task(
                task_id,
                GradingTaskUpdate(progress=30)
            )
            
            # Call AI grading API
            ai_client = await get_ai_grading_api_client()
            grading_result = await ai_client.grade_submission(
                grading_request,
                ai_model=task.ai_model
            )
            
            # Update progress
            await self.task_manager.update_grading_task(
                task_id,
                GradingTaskUpdate(progress=80)
            )
            
            # Save grading result
            await self._save_grading_result(task, grading_result)
            
            # Mark task as completed
            await self.task_manager.update_grading_task(
                task_id,
                GradingTaskUpdate(
                    status=GradingTaskStatus.COMPLETED,
                    progress=100,
                    score=grading_result.score,
                    feedback=grading_result.feedback,
                    suggestions=grading_result.suggestions,
                    result=self._grading_result_to_dict(grading_result),
                    completed_at=datetime.utcnow()
                )
            )
            
            logger.info(f"Successfully processed grading task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process grading task {task_id}: {str(e)}")
            
            # Mark task as failed
            try:
                await self.task_manager.update_grading_task(
                    task_id,
                    GradingTaskUpdate(
                        status=GradingTaskStatus.FAILED,
                        error_message=str(e),
                        completed_at=datetime.utcnow()
                    )
                )
            except Exception as update_error:
                logger.error(f"Failed to update task status to failed: {str(update_error)}")
            
            return False
    
    async def process_batch_grading_tasks(self, task_ids: List[UUID]) -> Dict[UUID, bool]:
        """Process multiple grading tasks in batch."""
        results = {}
        
        try:
            # Get all tasks
            tasks = []
            for task_id in task_ids:
                try:
                    task = await self._get_grading_task(task_id)
                    if task.status == GradingTaskStatus.PENDING:
                        tasks.append(task)
                    else:
                        results[task_id] = False
                        logger.warning(f"Task {task_id} is not pending: {task.status}")
                except Exception as e:
                    results[task_id] = False
                    logger.error(f"Failed to get task {task_id}: {str(e)}")
            
            if not tasks:
                return results
            
            # Prepare grading requests
            grading_requests = []
            task_submission_map = {}
            
            for task in tasks:
                try:
                    submission = await self._get_submission_with_details(task.submission_id)
                    grading_request = await self._prepare_grading_request(submission, task)
                    grading_requests.append(grading_request)
                    task_submission_map[task.id] = submission
                    
                    # Mark as processing
                    await self.task_manager.update_grading_task(
                        task.id,
                        GradingTaskUpdate(
                            status=GradingTaskStatus.PROCESSING,
                            progress=10,
                            started_at=datetime.utcnow()
                        )
                    )
                    
                except Exception as e:
                    results[task.id] = False
                    logger.error(f"Failed to prepare grading request for task {task.id}: {str(e)}")
            
            if not grading_requests:
                return results
            
            # Call batch grading API
            ai_client = await get_ai_grading_api_client()
            grading_results = await ai_client.batch_grade_submissions(grading_requests)
            
            # Process results
            for i, (task, grading_result) in enumerate(zip(tasks, grading_results)):
                try:
                    # Save grading result
                    await self._save_grading_result(task, grading_result)
                    
                    # Mark task as completed
                    await self.task_manager.update_grading_task(
                        task.id,
                        GradingTaskUpdate(
                            status=GradingTaskStatus.COMPLETED,
                            progress=100,
                            score=grading_result.score,
                            feedback=grading_result.feedback,
                            suggestions=grading_result.suggestions,
                            result=self._grading_result_to_dict(grading_result),
                            completed_at=datetime.utcnow()
                        )
                    )
                    
                    results[task.id] = True
                    logger.info(f"Successfully processed batch grading task {task.id}")
                    
                except Exception as e:
                    results[task.id] = False
                    logger.error(f"Failed to save result for task {task.id}: {str(e)}")
                    
                    # Mark as failed
                    try:
                        await self.task_manager.update_grading_task(
                            task.id,
                            GradingTaskUpdate(
                                status=GradingTaskStatus.FAILED,
                                error_message=str(e),
                                completed_at=datetime.utcnow()
                            )
                        )
                    except Exception as update_error:
                        logger.error(f"Failed to update task status: {str(update_error)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Batch grading failed: {str(e)}")
            
            # Mark all remaining tasks as failed
            for task_id in task_ids:
                if task_id not in results:
                    results[task_id] = False
                    try:
                        await self.task_manager.update_grading_task(
                            task_id,
                            GradingTaskUpdate(
                                status=GradingTaskStatus.FAILED,
                                error_message=f"Batch processing failed: {str(e)}",
                                completed_at=datetime.utcnow()
                            )
                        )
                    except Exception as update_error:
                        logger.error(f"Failed to update task status: {str(update_error)}")
            
            return results
    
    async def start_background_processing(self, task_id: UUID) -> None:
        """Start processing a grading task in the background."""
        if task_id in self._processing_tasks:
            logger.warning(f"Task {task_id} is already being processed")
            return
        
        # Create background task
        background_task = asyncio.create_task(
            self._background_process_task(task_id)
        )
        self._processing_tasks[task_id] = background_task
        
        # Set up cleanup callback
        background_task.add_done_callback(
            lambda t: self._processing_tasks.pop(task_id, None)
        )
    
    async def _background_process_task(self, task_id: UUID) -> None:
        """Background task processing wrapper."""
        try:
            await self.process_grading_task(task_id)
        except Exception as e:
            logger.error(f"Background processing failed for task {task_id}: {str(e)}")
    
    async def _get_grading_task(self, task_id: UUID) -> GradingTask:
        """Get grading task by ID."""
        query = select(GradingTask).where(GradingTask.id == task_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise NotFoundError(f"Grading task {task_id} not found")
        
        return task
    
    async def _get_submission_with_details(self, submission_id: UUID) -> Submission:
        """Get submission with all related data."""
        query = select(Submission).options(
            selectinload(Submission.assignment),
            selectinload(Submission.student),
            selectinload(Submission.files)
        ).where(Submission.id == submission_id)
        
        result = await self.db.execute(query)
        submission = result.scalar_one_or_none()
        
        if not submission:
            raise NotFoundError(f"Submission {submission_id} not found")
        
        return submission
    
    async def _prepare_grading_request(
        self,
        submission: Submission,
        task: GradingTask
    ) -> GradingRequest:
        """Prepare grading request from submission and task data."""
        assignment = submission.assignment
        
        # Combine submission content with file content if available
        student_answer = submission.content or ""
        
        # Add file content if available
        if submission.files:
            file_contents = []
            for file in submission.files:
                if file.file_type in ["text/plain", "application/pdf", "text/markdown"]:
                    # In a real implementation, you would extract text from files
                    file_contents.append(f"[File: {file.original_name}]")
            
            if file_contents:
                student_answer += "\n\nAttached files:\n" + "\n".join(file_contents)
        
        # Prepare grading criteria based on assignment
        grading_criteria = []
        if assignment.instructions:
            grading_criteria.append("Follow assignment instructions")
        if assignment.total_points:
            grading_criteria.append(f"Maximum score: {assignment.total_points} points")
        
        # Create rubric if not provided in task
        rubric = None
        if task.task_type == "rubric_grade":
            rubric = {
                "content_quality": 40,
                "accuracy": 30,
                "presentation": 20,
                "creativity": 10
            }
        
        return GradingRequest(
            submission_id=submission.id,
            assignment_title=assignment.title,
            assignment_description=assignment.description,
            assignment_instructions=assignment.instructions,
            student_answer=student_answer,
            rubric=rubric,
            grading_criteria=grading_criteria,
            max_score=assignment.total_points or 100
        )
    
    async def _save_grading_result(
        self,
        task: GradingTask,
        grading_result: GradingResult
    ) -> None:
        """Save grading result to submission."""
        submission = await self._get_submission_with_details(task.submission_id)
        
        # Update submission with grading results
        submission.score = grading_result.score
        submission.max_score = grading_result.max_score
        submission.ai_feedback = grading_result.feedback
        submission.status = SubmissionStatus.GRADED
        submission.graded_at = datetime.utcnow()
        
        # If there are suggestions, add them to teacher comments
        if grading_result.suggestions:
            if submission.teacher_comments:
                submission.teacher_comments += f"\n\nAI Suggestions: {grading_result.suggestions}"
            else:
                submission.teacher_comments = f"AI Suggestions: {grading_result.suggestions}"
        
        await self.db.commit()
    
    def _grading_result_to_dict(self, grading_result: GradingResult) -> Dict:
        """Convert grading result to dictionary for storage."""
        return {
            "score": grading_result.score,
            "max_score": grading_result.max_score,
            "percentage": grading_result.percentage,
            "feedback": grading_result.feedback,
            "suggestions": grading_result.suggestions,
            "strengths": grading_result.strengths,
            "weaknesses": grading_result.weaknesses,
            "rubric_scores": grading_result.rubric_scores,
            "confidence": grading_result.confidence,
            "processing_time_ms": grading_result.processing_time_ms,
            "processed_at": datetime.utcnow().isoformat()
        }


# Service factory function
async def get_grading_processor() -> GradingProcessor:
    """Get grading processor instance."""
    async with get_db_session() as db:
        return GradingProcessor(db)


class GradingQueue:
    """Queue manager for grading tasks."""
    
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._max_workers = 3
    
    async def start(self) -> None:
        """Start the grading queue workers."""
        if self._running:
            return
        
        self._running = True
        
        # Start worker tasks
        for i in range(self._max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)
        
        logger.info(f"Started {self._max_workers} grading queue workers")
    
    async def stop(self) -> None:
        """Stop the grading queue workers."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all workers
        for worker in self._workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        
        logger.info("Stopped grading queue workers")
    
    async def enqueue_task(self, task_id: UUID) -> None:
        """Add a grading task to the queue."""
        await self._queue.put(task_id)
        logger.info(f"Enqueued grading task {task_id}")
    
    async def _worker(self, worker_name: str) -> None:
        """Worker coroutine that processes grading tasks."""
        logger.info(f"Grading worker {worker_name} started")
        
        while self._running:
            try:
                # Get task from queue with timeout
                task_id = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
                
                logger.info(f"Worker {worker_name} processing task {task_id}")
                
                # Process the task
                async with get_db_session() as db:
                    processor = GradingProcessor(db)
                    success = await processor.process_grading_task(task_id)
                    
                    if success:
                        logger.info(f"Worker {worker_name} completed task {task_id}")
                    else:
                        logger.error(f"Worker {worker_name} failed to process task {task_id}")
                
                # Mark task as done
                self._queue.task_done()
                
            except asyncio.TimeoutError:
                # No tasks in queue, continue
                continue
            except asyncio.CancelledError:
                # Worker was cancelled
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} encountered error: {str(e)}")
                # Continue processing other tasks
        
        logger.info(f"Grading worker {worker_name} stopped")


# Global grading queue instance
_grading_queue: Optional[GradingQueue] = None


def get_grading_queue() -> GradingQueue:
    """Get global grading queue instance."""
    global _grading_queue
    if _grading_queue is None:
        _grading_queue = GradingQueue()
    return _grading_queue