"""Assignment scheduler service for handling due date reminders and status updates."""

from datetime import datetime, timedelta
from typing import List

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment, AssignmentStatus
from app.services.notification_service import AssignmentNotificationService


class AssignmentSchedulerService:
    """Service for scheduling assignment-related tasks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_due_soon_assignments(self, hours_before: int = 24) -> List[Assignment]:
        """Check for assignments that are due soon and send reminders."""
        cutoff_time = datetime.utcnow() + timedelta(hours=hours_before)
        
        # Find assignments that are due within the specified hours
        query = (
            select(Assignment)
            .where(
                and_(
                    Assignment.status == AssignmentStatus.ACTIVE,
                    Assignment.due_date.isnot(None),
                    Assignment.due_date <= cutoff_time,
                    Assignment.due_date > datetime.utcnow()
                )
            )
        )
        
        result = await self.db.execute(query)
        assignments = result.scalars().all()
        
        notification_service = AssignmentNotificationService(self.db)
        
        for assignment in assignments:
            try:
                await notification_service.notify_assignment_due_soon(assignment, hours_before)
            except Exception:
                # Continue with other assignments if one fails
                continue
        
        return assignments

    async def check_overdue_assignments(self) -> List[Assignment]:
        """Check for overdue assignments and send notifications."""
        query = (
            select(Assignment)
            .where(
                and_(
                    Assignment.status == AssignmentStatus.ACTIVE,
                    Assignment.due_date.isnot(None),
                    Assignment.due_date < datetime.utcnow()
                )
            )
        )
        
        result = await self.db.execute(query)
        assignments = result.scalars().all()
        
        notification_service = AssignmentNotificationService(self.db)
        
        for assignment in assignments:
            try:
                await notification_service.notify_assignment_overdue(assignment)
            except Exception:
                # Continue with other assignments if one fails
                continue
        
        return assignments

    async def auto_close_overdue_assignments(self, days_after_due: int = 7) -> List[Assignment]:
        """Automatically close assignments that are significantly overdue."""
        cutoff_time = datetime.utcnow() - timedelta(days=days_after_due)
        
        query = (
            select(Assignment)
            .where(
                and_(
                    Assignment.status == AssignmentStatus.ACTIVE,
                    Assignment.due_date.isnot(None),
                    Assignment.due_date < cutoff_time,
                    Assignment.allow_late_submission == False
                )
            )
        )
        
        result = await self.db.execute(query)
        assignments = result.scalars().all()
        
        closed_assignments = []
        for assignment in assignments:
            try:
                assignment.status = AssignmentStatus.CLOSED
                assignment.updated_at = datetime.utcnow()
                closed_assignments.append(assignment)
            except Exception:
                # Continue with other assignments if one fails
                continue
        
        if closed_assignments:
            await self.db.commit()
        
        return closed_assignments

    async def get_assignment_summary(self) -> dict:
        """Get a summary of assignment statuses across the system."""
        from sqlalchemy import func
        
        # Count assignments by status
        status_query = (
            select(
                Assignment.status,
                func.count(Assignment.id).label('count')
            )
            .group_by(Assignment.status)
        )
        
        status_result = await self.db.execute(status_query)
        status_counts = {row.status: row.count for row in status_result}
        
        # Count overdue assignments
        overdue_query = (
            select(func.count(Assignment.id))
            .where(
                and_(
                    Assignment.status == AssignmentStatus.ACTIVE,
                    Assignment.due_date.isnot(None),
                    Assignment.due_date < datetime.utcnow()
                )
            )
        )
        
        overdue_result = await self.db.execute(overdue_query)
        overdue_count = overdue_result.scalar() or 0
        
        # Count assignments due soon (next 24 hours)
        due_soon_query = (
            select(func.count(Assignment.id))
            .where(
                and_(
                    Assignment.status == AssignmentStatus.ACTIVE,
                    Assignment.due_date.isnot(None),
                    Assignment.due_date <= datetime.utcnow() + timedelta(hours=24),
                    Assignment.due_date > datetime.utcnow()
                )
            )
        )
        
        due_soon_result = await self.db.execute(due_soon_query)
        due_soon_count = due_soon_result.scalar() or 0
        
        return {
            "status_counts": status_counts,
            "overdue_count": overdue_count,
            "due_soon_count": due_soon_count,
            "total_assignments": sum(status_counts.values()),
            "active_assignments": status_counts.get(AssignmentStatus.ACTIVE, 0)
        }

    async def run_daily_tasks(self) -> dict:
        """Run daily maintenance tasks for assignments."""
        results = {
            "due_soon_reminders": [],
            "overdue_notifications": [],
            "auto_closed": [],
            "summary": {}
        }
        
        try:
            # Send due soon reminders
            due_soon = await self.check_due_soon_assignments(24)
            results["due_soon_reminders"] = [str(a.id) for a in due_soon]
            
            # Send overdue notifications
            overdue = await self.check_overdue_assignments()
            results["overdue_notifications"] = [str(a.id) for a in overdue]
            
            # Auto-close significantly overdue assignments
            auto_closed = await self.auto_close_overdue_assignments(7)
            results["auto_closed"] = [str(a.id) for a in auto_closed]
            
            # Get system summary
            results["summary"] = await self.get_assignment_summary()
            
        except Exception as e:
            results["error"] = str(e)
        
        return results