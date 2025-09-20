"""AI grading service for managing grading tasks and processing."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.core.exceptions import (
    GradingError,
    NotFoundError,
    ValidationError
)
from app.models.ai import GradingTask, GradingTaskStatus
from app.models.assignment import Assignment, Submission, SubmissionStatus
from app.models.file import File
from app.models.user import User
from app.schemas.grading import (
    BatchGradingRequest,
    BatchGradingResponse,
    GradingRequest,
    GradingResult,
    GradingStats,
    GradingTaskCreate,
    GradingTaskFilter,
    GradingTaskList,
    GradingTaskResponse,
    GradingTaskUpdate
)

logger = logging.getLogger(__name__)


class GradingTaskManager:
    """Manager for AI grading tasks with queue management and retry logic."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._processing_tasks: Dict[UUID, asyncio.Task] = {}
        self._max_concurrent_tasks = 5
        self._task_timeout_minutes = 30
    
    async def create_grading_task(
        self,
        task_data: GradingTaskCreate
    ) -> GradingTaskResponse:
        """Create a new grading task."""
        try:
            # Verify submission exists and is valid for grading
            submission = await self._get_submission_for_grading(task_data.submission_id)
            
            # Check if there's already a pending/processing task for this submission
            existing_task = await self._get_active_task_for_submission(task_data.submission_id)
            if existing_task:
                logger.warning(f"Active grading task already exists for submission {task_data.submission_id}")
                return GradingTaskResponse.from_orm(existing_task)
            
            # Create new grading task
            grading_task = GradingTask(
                submission_id=task_data.submission_id,
                task_type=task_data.task_type,
                ai_model=task_data.ai_model,
                prompt_template=task_data.prompt_template,
                max_retries=task_data.max_retries,
                status=GradingTaskStatus.PENDING
            )
            
            self.db.add(grading_task)
            await self.db.commit()
            await self.db.refresh(grading_task)
            
            # Update submission status
            submission.status = SubmissionStatus.GRADING
            await self.db.commit()
            
            logger.info(f"Created grading task {grading_task.id} for submission {task_data.submission_id}")
            
            return GradingTaskResponse.from_orm(grading_task)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create grading task: {str(e)}")
            raise GradingError(f"Failed to create grading task: {str(e)}")
    
    async def get_grading_task(self, task_id: UUID) -> GradingTaskResponse:
        """Get a grading task by ID."""
        task = await self._get_task_by_id(task_id)
        return GradingTaskResponse.from_orm(task)
    
    async def update_grading_task(
        self,
        task_id: UUID,
        update_data: GradingTaskUpdate
    ) -> GradingTaskResponse:
        """Update a grading task."""
        try:
            task = await self._get_task_by_id(task_id)
            
            # Update fields
            for field, value in update_data.dict(exclude_unset=True).items():
                setattr(task, field, value)
            
            # Update timestamp
            task.updated_at = datetime.utcnow()
            
            # If task is completed, update submission
            if update_data.status == GradingTaskStatus.COMPLETED:
                await self._complete_grading_task(task, update_data)
            elif update_data.status == GradingTaskStatus.FAILED:
                await self._handle_failed_task(task)
            
            await self.db.commit()
            await self.db.refresh(task)
            
            logger.info(f"Updated grading task {task_id} with status {update_data.status}")
            
            return GradingTaskResponse.from_orm(task)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update grading task {task_id}: {str(e)}")
            raise GradingError(f"Failed to update grading task: {str(e)}")
    
    async def list_grading_tasks(
        self,
        filters: GradingTaskFilter
    ) -> GradingTaskList:
        """List grading tasks with filtering and pagination."""
        try:
            # Build query
            query = select(GradingTask).options(
                selectinload(GradingTask.submission).selectinload(Submission.assignment),
                selectinload(GradingTask.submission).selectinload(Submission.student)
            )
            
            # Apply filters
            conditions = []
            
            if filters.status:
                conditions.append(GradingTask.status == filters.status)
            
            if filters.task_type:
                conditions.append(GradingTask.task_type == filters.task_type)
            
            if filters.submission_id:
                conditions.append(GradingTask.submission_id == filters.submission_id)
            
            if filters.created_after:
                conditions.append(GradingTask.created_at >= filters.created_after)
            
            if filters.created_before:
                conditions.append(GradingTask.created_at <= filters.created_before)
            
            if filters.has_errors is not None:
                if filters.has_errors:
                    conditions.append(GradingTask.error_message.isnot(None))
                else:
                    conditions.append(GradingTask.error_message.is_(None))
            
            # Join with submission and assignment for additional filters
            if any([filters.student_id, filters.assignment_id, filters.class_id]):
                query = query.join(Submission).join(Assignment)
                
                if filters.student_id:
                    conditions.append(Submission.student_id == filters.student_id)
                
                if filters.assignment_id:
                    conditions.append(Submission.assignment_id == filters.assignment_id)
                
                if filters.class_id:
                    conditions.append(Assignment.class_id == filters.class_id)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Apply sorting
            sort_column = getattr(GradingTask, filters.sort_by)
            if filters.sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination
            offset = (filters.page - 1) * filters.size
            query = query.offset(offset).limit(filters.size)
            
            # Execute query
            result = await self.db.execute(query)
            tasks = result.scalars().all()
            
            # Calculate pagination info
            pages = (total + filters.size - 1) // filters.size
            
            return GradingTaskList(
                tasks=[GradingTaskResponse.from_orm(task) for task in tasks],
                total=total,
                page=filters.page,
                size=filters.size,
                pages=pages
            )
            
        except Exception as e:
            logger.error(f"Failed to list grading tasks: {str(e)}")
            raise GradingError(f"Failed to list grading tasks: {str(e)}")
    
    async def retry_failed_task(self, task_id: UUID) -> GradingTaskResponse:
        """Retry a failed grading task."""
        try:
            task = await self._get_task_by_id(task_id)
            
            if not task.can_retry:
                raise ValidationError("Task cannot be retried")
            
            # Reset task state
            task.status = GradingTaskStatus.PENDING
            task.error_message = None
            task.retry_count += 1
            task.started_at = None
            task.completed_at = None
            task.progress = 0
            task.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(task)
            
            logger.info(f"Retrying grading task {task_id} (attempt {task.retry_count})")
            
            return GradingTaskResponse.from_orm(task)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to retry grading task {task_id}: {str(e)}")
            raise GradingError(f"Failed to retry grading task: {str(e)}")
    
    async def cancel_task(self, task_id: UUID) -> GradingTaskResponse:
        """Cancel a pending or processing grading task."""
        try:
            task = await self._get_task_by_id(task_id)
            
            if task.status not in [GradingTaskStatus.PENDING, GradingTaskStatus.PROCESSING]:
                raise ValidationError("Only pending or processing tasks can be cancelled")
            
            # Cancel the task
            task.status = GradingTaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            
            # Cancel asyncio task if running
            if task.id in self._processing_tasks:
                self._processing_tasks[task.id].cancel()
                del self._processing_tasks[task.id]
            
            # Reset submission status
            submission = await self._get_submission_for_grading(task.submission_id)
            submission.status = SubmissionStatus.SUBMITTED
            
            await self.db.commit()
            await self.db.refresh(task)
            
            logger.info(f"Cancelled grading task {task_id}")
            
            return GradingTaskResponse.from_orm(task)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to cancel grading task {task_id}: {str(e)}")
            raise GradingError(f"Failed to cancel grading task: {str(e)}")
    
    async def create_batch_grading_tasks(
        self,
        batch_request: BatchGradingRequest
    ) -> BatchGradingResponse:
        """Create multiple grading tasks in batch."""
        created_tasks = []
        failed_submissions = []
        
        try:
            for submission_id in batch_request.submission_ids:
                try:
                    task_data = GradingTaskCreate(
                        submission_id=submission_id,
                        task_type=batch_request.task_type
                    )
                    task = await self.create_grading_task(task_data)
                    created_tasks.append(task.id)
                except Exception as e:
                    logger.warning(f"Failed to create grading task for submission {submission_id}: {str(e)}")
                    failed_submissions.append(submission_id)
            
            # Estimate completion time (rough calculation)
            estimated_time = len(created_tasks) * 2  # 2 minutes per task average
            
            return BatchGradingResponse(
                created_tasks=created_tasks,
                failed_submissions=failed_submissions,
                total_requested=len(batch_request.submission_ids),
                total_created=len(created_tasks),
                estimated_completion_time_minutes=estimated_time if created_tasks else None
            )
            
        except Exception as e:
            logger.error(f"Failed to create batch grading tasks: {str(e)}")
            raise GradingError(f"Failed to create batch grading tasks: {str(e)}")
    
    async def get_grading_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> GradingStats:
        """Get grading statistics."""
        try:
            # Build base query
            query = select(GradingTask)
            
            if start_date:
                query = query.where(GradingTask.created_at >= start_date)
            if end_date:
                query = query.where(GradingTask.created_at <= end_date)
            
            result = await self.db.execute(query)
            tasks = result.scalars().all()
            
            if not tasks:
                return GradingStats(
                    total_tasks=0,
                    pending_tasks=0,
                    processing_tasks=0,
                    completed_tasks=0,
                    failed_tasks=0,
                    success_rate=0.0,
                    retry_rate=0.0
                )
            
            # Calculate statistics
            total_tasks = len(tasks)
            pending_tasks = sum(1 for t in tasks if t.status == GradingTaskStatus.PENDING)
            processing_tasks = sum(1 for t in tasks if t.status == GradingTaskStatus.PROCESSING)
            completed_tasks = sum(1 for t in tasks if t.status == GradingTaskStatus.COMPLETED)
            failed_tasks = sum(1 for t in tasks if t.status == GradingTaskStatus.FAILED)
            
            # Calculate success rate
            finished_tasks = completed_tasks + failed_tasks
            success_rate = completed_tasks / finished_tasks if finished_tasks > 0 else 0.0
            
            # Calculate retry rate
            retried_tasks = sum(1 for t in tasks if t.retry_count > 0)
            retry_rate = retried_tasks / total_tasks if total_tasks > 0 else 0.0
            
            # Calculate average processing time
            completed_with_duration = [
                t for t in tasks 
                if t.status == GradingTaskStatus.COMPLETED and t.duration_seconds
            ]
            avg_processing_time = (
                sum(t.duration_seconds for t in completed_with_duration) / len(completed_with_duration)
                if completed_with_duration else None
            )
            
            return GradingStats(
                total_tasks=total_tasks,
                pending_tasks=pending_tasks,
                processing_tasks=processing_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                average_processing_time_seconds=avg_processing_time,
                success_rate=success_rate,
                retry_rate=retry_rate
            )
            
        except Exception as e:
            logger.error(f"Failed to get grading stats: {str(e)}")
            raise GradingError(f"Failed to get grading stats: {str(e)}")
    
    async def cleanup_old_tasks(self, days_old: int = 30) -> int:
        """Clean up old completed/failed tasks."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Find old tasks to delete
            query = select(GradingTask).where(
                and_(
                    GradingTask.updated_at < cutoff_date,
                    or_(
                        GradingTask.status == GradingTaskStatus.COMPLETED,
                        GradingTask.status == GradingTaskStatus.FAILED,
                        GradingTask.status == GradingTaskStatus.CANCELLED
                    )
                )
            )
            
            result = await self.db.execute(query)
            old_tasks = result.scalars().all()
            
            # Delete old tasks
            for task in old_tasks:
                await self.db.delete(task)
            
            await self.db.commit()
            
            logger.info(f"Cleaned up {len(old_tasks)} old grading tasks")
            return len(old_tasks)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to cleanup old tasks: {str(e)}")
            raise GradingError(f"Failed to cleanup old tasks: {str(e)}")
    
    # Private helper methods
    
    async def _get_task_by_id(self, task_id: UUID) -> GradingTask:
        """Get grading task by ID or raise NotFoundError."""
        query = select(GradingTask).where(GradingTask.id == task_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise NotFoundError(f"Grading task {task_id} not found")
        
        return task
    
    async def _get_submission_for_grading(self, submission_id: UUID) -> Submission:
        """Get submission and validate it's ready for grading."""
        query = select(Submission).options(
            selectinload(Submission.assignment),
            selectinload(Submission.files)
        ).where(Submission.id == submission_id)
        
        result = await self.db.execute(query)
        submission = result.scalar_one_or_none()
        
        if not submission:
            raise NotFoundError(f"Submission {submission_id} not found")
        
        if submission.status == SubmissionStatus.PENDING:
            raise ValidationError("Cannot grade pending submission")
        
        return submission
    
    async def _get_active_task_for_submission(self, submission_id: UUID) -> Optional[GradingTask]:
        """Get active grading task for submission if exists."""
        query = select(GradingTask).where(
            and_(
                GradingTask.submission_id == submission_id,
                or_(
                    GradingTask.status == GradingTaskStatus.PENDING,
                    GradingTask.status == GradingTaskStatus.PROCESSING
                )
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _complete_grading_task(self, task: GradingTask, update_data: GradingTaskUpdate):
        """Complete a grading task and update submission."""
        # Update submission with grading results
        submission = await self._get_submission_for_grading(task.submission_id)
        
        if update_data.score is not None:
            submission.score = update_data.score
        
        if update_data.feedback:
            submission.ai_feedback = update_data.feedback
        
        submission.status = SubmissionStatus.GRADED
        submission.graded_at = datetime.utcnow()
        
        # Set completion timestamp
        task.completed_at = datetime.utcnow()
        task.progress = 100
    
    async def _handle_failed_task(self, task: GradingTask):
        """Handle a failed grading task."""
        # If task can be retried, keep submission in grading status
        # Otherwise, reset to submitted status
        if not task.can_retry:
            submission = await self._get_submission_for_grading(task.submission_id)
            submission.status = SubmissionStatus.SUBMITTED
            task.completed_at = datetime.utcnow()


# Service factory function
async def get_grading_task_manager() -> GradingTaskManager:
    """Get grading task manager instance."""
    async with get_db_session() as db:
        return GradingTaskManager(db)