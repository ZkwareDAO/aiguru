"""Comprehensive notification service with message queue support."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.assignment import Assignment, Submission
from app.models.class_model import ClassStudent
from app.models.notification import Notification, NotificationPriority, NotificationType
from app.models.user import User, UserRole
from app.services.task_queue import TaskHandler, get_task_queue
from app.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class NotificationService:
    """Comprehensive notification service with queue and real-time support."""

    def __init__(self, db: AsyncSession, websocket_manager: Optional[WebSocketManager] = None):
        self.db = db
        self.websocket_manager = websocket_manager
        self.settings = get_settings()
        self.task_queue = get_task_queue()

    async def create_notification(
        self,
        user_id: UUID,
        title: str,
        content: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[Dict[str, Any]] = None,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        send_email: bool = False,
        send_push: bool = True,
        expires_at: Optional[datetime] = None,
        send_immediately: bool = True
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=user_id,
            title=title,
            content=content,
            type=notification_type,
            priority=priority,
            data=data or {},
            action_url=action_url,
            action_text=action_text,
            send_email=send_email,
            send_push=send_push,
            expires_at=expires_at
        )
        
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        
        if send_immediately:
            await self._send_notification(notification)
        
        return notification

    async def create_bulk_notifications(
        self,
        user_ids: List[UUID],
        title: str,
        content: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[Dict[str, Any]] = None,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        send_email: bool = False,
        send_push: bool = True,
        expires_at: Optional[datetime] = None,
        send_immediately: bool = True
    ) -> List[Notification]:
        """Create notifications for multiple users."""
        notifications = []
        
        for user_id in user_ids:
            notification = Notification(
                user_id=user_id,
                title=title,
                content=content,
                type=notification_type,
                priority=priority,
                data=data or {},
                action_url=action_url,
                action_text=action_text,
                send_email=send_email,
                send_push=send_push,
                expires_at=expires_at
            )
            notifications.append(notification)
            self.db.add(notification)
        
        await self.db.commit()
        
        if send_immediately:
            # Send notifications in batches to avoid overwhelming the system
            await self._send_bulk_notifications(notifications)
        
        return notifications

    async def _send_notification(self, notification: Notification) -> None:
        """Send a single notification through appropriate channels."""
        try:
            # Send real-time notification via WebSocket
            if notification.send_push and self.websocket_manager:
                await self.websocket_manager.send_notification(
                    user_id=notification.user_id,
                    notification_data={
                        "id": str(notification.id),
                        "title": notification.title,
                        "content": notification.content,
                        "type": notification.type,
                        "priority": notification.priority,
                        "data": notification.data,
                        "action_url": notification.action_url,
                        "action_text": notification.action_text,
                        "created_at": notification.created_at.isoformat()
                    }
                )
            
            # Queue email notification if requested
            if notification.send_email:
                await self.task_queue.enqueue_task(
                    "send_email_notification",
                    {
                        "notification_id": str(notification.id),
                        "user_id": str(notification.user_id),
                        "title": notification.title,
                        "content": notification.content,
                        "type": notification.type,
                        "data": notification.data
                    },
                    priority=self._get_task_priority(notification.priority)
                )
            
            # Mark as sent
            notification.mark_as_sent()
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to send notification {notification.id}: {e}")

    async def _send_bulk_notifications(self, notifications: List[Notification]) -> None:
        """Send multiple notifications efficiently."""
        # Group notifications by type for batch processing
        websocket_notifications = []
        email_notifications = []
        
        for notification in notifications:
            if notification.send_push:
                websocket_notifications.append(notification)
            if notification.send_email:
                email_notifications.append(notification)
        
        # Send WebSocket notifications
        if websocket_notifications and self.websocket_manager:
            await self._send_bulk_websocket_notifications(websocket_notifications)
        
        # Queue email notifications in batches
        if email_notifications:
            await self._queue_bulk_email_notifications(email_notifications)
        
        # Mark all as sent
        notification_ids = [n.id for n in notifications]
        await self._mark_notifications_sent(notification_ids)

    async def _send_bulk_websocket_notifications(self, notifications: List[Notification]) -> None:
        """Send multiple WebSocket notifications."""
        tasks = []
        for notification in notifications:
            task = self.websocket_manager.send_notification(
                user_id=notification.user_id,
                notification_data={
                    "id": str(notification.id),
                    "title": notification.title,
                    "content": notification.content,
                    "type": notification.type,
                    "priority": notification.priority,
                    "data": notification.data,
                    "action_url": notification.action_url,
                    "action_text": notification.action_text,
                    "created_at": notification.created_at.isoformat()
                }
            )
            tasks.append(task)
        
        # Send all notifications concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _queue_bulk_email_notifications(self, notifications: List[Notification]) -> None:
        """Queue multiple email notifications for batch processing."""
        batch_size = 50  # Process emails in batches
        
        for i in range(0, len(notifications), batch_size):
            batch = notifications[i:i + batch_size]
            
            await self.task_queue.enqueue_task(
                "send_bulk_email_notifications",
                {
                    "notification_ids": [str(n.id) for n in batch]
                },
                priority=self._get_task_priority(batch[0].priority)
            )

    async def _mark_notifications_sent(self, notification_ids: List[UUID]) -> None:
        """Mark multiple notifications as sent."""
        stmt = (
            update(Notification)
            .where(Notification.id.in_(notification_ids))
            .values(is_sent=True, sent_at=datetime.utcnow())
        )
        await self.db.execute(stmt)
        await self.db.commit()

    def _get_task_priority(self, notification_priority: NotificationPriority) -> int:
        """Convert notification priority to task priority."""
        from app.services.task_queue import TaskPriority
        
        priority_map = {
            NotificationPriority.LOW: TaskPriority.LOW,
            NotificationPriority.NORMAL: TaskPriority.NORMAL,
            NotificationPriority.HIGH: TaskPriority.HIGH,
            NotificationPriority.URGENT: TaskPriority.URGENT
        }
        return priority_map.get(notification_priority, TaskPriority.NORMAL)

    async def get_user_notifications(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
        notification_types: Optional[List[NotificationType]] = None
    ) -> List[Notification]:
        """Get notifications for a user."""
        query = select(Notification).where(Notification.user_id == user_id)
        
        if unread_only:
            query = query.where(Notification.is_read == False)
        
        if notification_types:
            query = query.where(Notification.type.in_(notification_types))
        
        # Exclude expired notifications
        query = query.where(
            or_(
                Notification.expires_at.is_(None),
                Notification.expires_at > datetime.utcnow()
            )
        )
        
        query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def mark_notification_read(self, notification_id: UUID, user_id: UUID) -> bool:
        """Mark a notification as read."""
        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def mark_notifications_read(
        self,
        user_id: UUID,
        notification_ids: Optional[List[UUID]] = None
    ) -> int:
        """Mark multiple notifications as read."""
        query_conditions = [Notification.user_id == user_id]
        
        if notification_ids:
            query_conditions.append(Notification.id.in_(notification_ids))
        else:
            # Mark all unread notifications as read
            query_conditions.append(Notification.is_read == False)
        
        stmt = (
            update(Notification)
            .where(and_(*query_conditions))
            .values(is_read=True, read_at=datetime.utcnow())
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def get_unread_count(
        self,
        user_id: UUID,
        notification_types: Optional[List[NotificationType]] = None
    ) -> int:
        """Get count of unread notifications."""
        query = (
            select(func.count(Notification.id))
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                    or_(
                        Notification.expires_at.is_(None),
                        Notification.expires_at > datetime.utcnow()
                    )
                )
            )
        )
        
        if notification_types:
            query = query.where(Notification.type.in_(notification_types))
        
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def delete_notification(self, notification_id: UUID, user_id: UUID) -> bool:
        """Delete a notification."""
        query = select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        notification = result.scalar_one_or_none()
        
        if notification:
            await self.db.delete(notification)
            await self.db.commit()
            return True
        
        return False

    async def cleanup_expired_notifications(self) -> int:
        """Clean up expired notifications."""
        from sqlalchemy import delete
        
        stmt = delete(Notification).where(
            and_(
                Notification.expires_at.is_not(None),
                Notification.expires_at < datetime.utcnow()
            )
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def get_notification_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get notification statistics for a user."""
        # Total notifications
        total_query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id
        )
        total_result = await self.db.execute(total_query)
        total_count = total_result.scalar() or 0
        
        # Unread notifications
        unread_count = await self.get_unread_count(user_id)
        
        # Notifications by type
        type_query = (
            select(Notification.type, func.count(Notification.id))
            .where(Notification.user_id == user_id)
            .group_by(Notification.type)
        )
        type_result = await self.db.execute(type_query)
        type_counts = dict(type_result.fetchall())
        
        # Recent activity (last 7 days)
        recent_query = (
            select(func.count(Notification.id))
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.created_at >= datetime.utcnow() - timedelta(days=7)
                )
            )
        )
        recent_result = await self.db.execute(recent_query)
        recent_count = recent_result.scalar() or 0
        
        return {
            "total_notifications": total_count,
            "unread_notifications": unread_count,
            "read_notifications": total_count - unread_count,
            "notifications_by_type": type_counts,
            "recent_notifications": recent_count
        }


class AssignmentNotificationService:
    """Service for managing assignment-related notifications."""

    def __init__(self, db: AsyncSession, notification_service: Optional[NotificationService] = None):
        self.db = db
        self.notification_service = notification_service or NotificationService(db)

    async def notify_assignment_published(
        self,
        assignment: Assignment
    ) -> List[Notification]:
        """Notify students when an assignment is published."""
        # Get all students in the class
        students_query = (
            select(User)
            .join(ClassStudent)
            .where(
                and_(
                    ClassStudent.class_id == assignment.class_id,
                    ClassStudent.is_active == True,
                    User.role == UserRole.STUDENT,
                    User.is_active == True
                )
            )
        )
        students_result = await self.db.execute(students_query)
        students = students_result.scalars().all()

        student_ids = [student.id for student in students]
        
        notifications = await self.notification_service.create_bulk_notifications(
            user_ids=student_ids,
            title="新作业发布",
            content=f"教师发布了新作业：{assignment.title}",
            notification_type=NotificationType.ASSIGNMENT_PUBLISHED,
            priority=NotificationPriority.NORMAL,
            data={
                "assignment_id": str(assignment.id),
                "assignment_title": assignment.title,
                "class_id": str(assignment.class_id),
                "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                "total_points": assignment.total_points
            },
            action_url=f"/assignments/{assignment.id}",
            action_text="查看作业",
            send_email=True,  # Send email for new assignments
            send_push=True
        )

        return notifications

    async def notify_assignment_due_soon(
        self,
        assignment: Assignment,
        hours_before: int = 24
    ) -> List[Notification]:
        """Notify students when assignment is due soon."""
        if not assignment.due_date:
            return []

        # Get students who haven't submitted yet
        students_query = (
            select(User)
            .join(ClassStudent)
            .outerjoin(
                Submission,
                and_(
                    Submission.assignment_id == assignment.id,
                    Submission.student_id == User.id
                )
            )
            .where(
                and_(
                    ClassStudent.class_id == assignment.class_id,
                    ClassStudent.is_active == True,
                    User.role == UserRole.STUDENT,
                    User.is_active == True,
                    Submission.id.is_(None)  # No submission yet
                )
            )
        )
        students_result = await self.db.execute(students_query)
        students = students_result.scalars().all()

        student_ids = [student.id for student in students]
        
        if not student_ids:
            return []
        
        notifications = await self.notification_service.create_bulk_notifications(
            user_ids=student_ids,
            title="作业即将截止",
            content=f"作业"{assignment.title}"将在{hours_before}小时后截止，请及时提交。",
            notification_type=NotificationType.ASSIGNMENT_DUE_SOON,
            priority=NotificationPriority.HIGH,
            data={
                "assignment_id": str(assignment.id),
                "assignment_title": assignment.title,
                "due_date": assignment.due_date.isoformat(),
                "hours_before": hours_before
            },
            action_url=f"/assignments/{assignment.id}",
            action_text="立即提交",
            send_email=True,
            send_push=True
        )

        return notifications

    async def notify_assignment_overdue(
        self,
        assignment: Assignment
    ) -> List[Notification]:
        """Notify students when assignment is overdue."""
        if not assignment.due_date or not assignment.is_overdue:
            return []

        # Get students who haven't submitted yet
        students_query = (
            select(User)
            .join(ClassStudent)
            .outerjoin(
                Submission,
                and_(
                    Submission.assignment_id == assignment.id,
                    Submission.student_id == User.id
                )
            )
            .where(
                and_(
                    ClassStudent.class_id == assignment.class_id,
                    ClassStudent.is_active == True,
                    User.role == UserRole.STUDENT,
                    User.is_active == True,
                    Submission.id.is_(None)  # No submission yet
                )
            )
        )
        students_result = await self.db.execute(students_query)
        students = students_result.scalars().all()

        student_ids = [student.id for student in students]
        
        if not student_ids:
            return []
        
        overdue_hours = int((datetime.utcnow() - assignment.due_date.replace(tzinfo=None)).total_seconds() / 3600)
        
        notifications = await self.notification_service.create_bulk_notifications(
            user_ids=student_ids,
            title="作业已逾期",
            content=f"作业"{assignment.title}"已逾期，请尽快联系教师。",
            notification_type=NotificationType.ASSIGNMENT_OVERDUE,
            priority=NotificationPriority.URGENT,
            data={
                "assignment_id": str(assignment.id),
                "assignment_title": assignment.title,
                "due_date": assignment.due_date.isoformat(),
                "overdue_hours": overdue_hours
            },
            action_url=f"/assignments/{assignment.id}",
            action_text="联系教师",
            send_email=True,
            send_push=True
        )

        return notifications

    async def notify_submission_received(
        self,
        submission: Submission
    ) -> Optional[Notification]:
        """Notify teacher when a submission is received."""
        # Get the assignment and teacher
        assignment_query = (
            select(Assignment)
            .where(Assignment.id == submission.assignment_id)
        )
        assignment_result = await self.db.execute(assignment_query)
        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
            return None

        # Get student name
        student_query = select(User).where(User.id == submission.student_id)
        student_result = await self.db.execute(student_query)
        student = student_result.scalar_one_or_none()

        if not student:
            return None

        notification = await self.notification_service.create_notification(
            user_id=assignment.teacher_id,
            title="收到新的作业提交",
            content=f"学生 {student.name} 提交了作业"{assignment.title}"。",
            notification_type=NotificationType.SUBMISSION_RECEIVED,
            priority=NotificationPriority.NORMAL,
            data={
                "assignment_id": str(assignment.id),
                "assignment_title": assignment.title,
                "submission_id": str(submission.id),
                "student_id": str(student.id),
                "student_name": student.name,
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                "is_late": submission.is_late
            },
            action_url=f"/submissions/{submission.id}",
            action_text="查看提交",
            send_email=False,  # Teachers might not want email for every submission
            send_push=True
        )
        
        return notification

    async def notify_submission_graded(
        self,
        submission: Submission
    ) -> Optional[Notification]:
        """Notify student when their submission is graded."""
        # Get the assignment
        assignment_query = (
            select(Assignment)
            .where(Assignment.id == submission.assignment_id)
        )
        assignment_result = await self.db.execute(assignment_query)
        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
            return None

        notification = await self.notification_service.create_notification(
            user_id=submission.student_id,
            title="作业已批改",
            content=f"您的作业"{assignment.title}"已批改完成，得分：{submission.score}/{submission.max_score}。",
            notification_type=NotificationType.SUBMISSION_GRADED,
            priority=NotificationPriority.HIGH,
            data={
                "assignment_id": str(assignment.id),
                "assignment_title": assignment.title,
                "submission_id": str(submission.id),
                "score": submission.score,
                "max_score": submission.max_score,
                "grade_percentage": submission.grade_percentage,
                "feedback": submission.feedback,
                "graded_at": submission.graded_at.isoformat() if submission.graded_at else None
            },
            action_url=f"/submissions/{submission.id}/results",
            action_text="查看结果",
            send_email=True,  # Students want to know about grades
            send_push=True
        )
        
        return notification

    async def notify_submission_returned(
        self,
        submission: Submission
    ) -> Optional[Notification]:
        """Notify student when their graded submission is returned."""
        # Get the assignment
        assignment_query = (
            select(Assignment)
            .where(Assignment.id == submission.assignment_id)
        )
        assignment_result = await self.db.execute(assignment_query)
        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
            return None

        notification = await self.notification_service.create_notification(
            user_id=submission.student_id,
            title="作业已返还",
            content=f"您的作业"{assignment.title}"已返还，请查看批改结果和反馈。",
            notification_type=NotificationType.SUBMISSION_RETURNED,
            priority=NotificationPriority.HIGH,
            data={
                "assignment_id": str(assignment.id),
                "assignment_title": assignment.title,
                "submission_id": str(submission.id),
                "score": submission.score,
                "max_score": submission.max_score,
                "grade_percentage": submission.grade_percentage,
                "feedback": submission.feedback,
                "teacher_comments": submission.teacher_comments,
                "returned_at": submission.returned_at.isoformat() if submission.returned_at else None
            },
            action_url=f"/submissions/{submission.id}/results",
            action_text="查看详情",
            send_email=True,
            send_push=True
        )
        
        return notification

    async def get_assignment_notifications(
        self,
        user_id: UUID,
        assignment_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[Notification]:
        """Get assignment-related notifications for a user."""
        assignment_types = [
            NotificationType.ASSIGNMENT_PUBLISHED,
            NotificationType.ASSIGNMENT_DUE_SOON,
            NotificationType.ASSIGNMENT_OVERDUE,
            NotificationType.SUBMISSION_RECEIVED,
            NotificationType.SUBMISSION_GRADED,
            NotificationType.SUBMISSION_RETURNED
        ]
        
        notifications = await self.notification_service.get_user_notifications(
            user_id=user_id,
            limit=limit,
            notification_types=assignment_types
        )
        
        if assignment_id:
            # Filter by assignment_id in the data field
            filtered_notifications = []
            for notification in notifications:
                if (notification.data and 
                    notification.data.get("assignment_id") == str(assignment_id)):
                    filtered_notifications.append(notification)
            return filtered_notifications
        
        return notifications

    async def mark_notifications_read(
        self,
        user_id: UUID,
        notification_ids: List[UUID]
    ) -> int:
        """Mark multiple notifications as read."""
        return await self.notification_service.mark_notifications_read(
            user_id=user_id,
            notification_ids=notification_ids
        )

    async def get_unread_count(
        self,
        user_id: UUID,
        assignment_related_only: bool = True
    ) -> int:
        """Get count of unread notifications."""
        if assignment_related_only:
            assignment_types = [
                NotificationType.ASSIGNMENT_PUBLISHED,
                NotificationType.ASSIGNMENT_DUE_SOON,
                NotificationType.ASSIGNMENT_OVERDUE,
                NotificationType.SUBMISSION_RECEIVED,
                NotificationType.SUBMISSION_GRADED,
                NotificationType.SUBMISSION_RETURNED
            ]
            return await self.notification_service.get_unread_count(
                user_id=user_id,
                notification_types=assignment_types
            )
        else:
            return await self.notification_service.get_unread_count(user_id=user_id)

# Ema
il notification task handlers
class EmailNotificationHandler(TaskHandler):
    """Handler for sending individual email notifications."""
    
    def __init__(self):
        super().__init__("send_email_notification")
    
    async def execute(self, task: TaskDefinition) -> Dict[str, Any]:
        """Send a single email notification."""
        from app.services.email_service import EmailService
        
        notification_id = UUID(task.payload["notification_id"])
        user_id = UUID(task.payload["user_id"])
        title = task.payload["title"]
        content = task.payload["content"]
        notification_type = task.payload["type"]
        data = task.payload.get("data", {})
        
        async with get_db_session() as db:
            # Get user email
            user_query = select(User).where(User.id == user_id)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user or not user.email:
                return {
                    "success": False,
                    "error": "User not found or no email address"
                }
            
            # Send email
            email_service = EmailService()
            success = await email_service.send_notification_email(
                to_email=user.email,
                user_name=user.name,
                title=title,
                content=content,
                notification_type=notification_type,
                data=data
            )
            
            return {
                "notification_id": str(notification_id),
                "user_id": str(user_id),
                "email": user.email,
                "success": success,
                "sent_at": datetime.utcnow().isoformat()
            }
    
    async def on_success(self, task: TaskDefinition, result: Dict[str, Any]) -> None:
        """Handle successful email sending."""
        if result.get("success"):
            logger.info(f"Email notification sent successfully to {result.get('email')}")
    
    async def on_failure(self, task: TaskDefinition, error: Exception) -> None:
        """Handle failed email sending."""
        logger.error(f"Failed to send email notification: {error}")


class BulkEmailNotificationHandler(TaskHandler):
    """Handler for sending bulk email notifications."""
    
    def __init__(self):
        super().__init__("send_bulk_email_notifications")
    
    async def execute(self, task: TaskDefinition) -> Dict[str, Any]:
        """Send multiple email notifications."""
        from app.services.email_service import EmailService
        
        notification_ids = [UUID(nid) for nid in task.payload["notification_ids"]]
        
        async with get_db_session() as db:
            # Get notifications with user data
            notifications_query = (
                select(Notification, User)
                .join(User, Notification.user_id == User.id)
                .where(
                    and_(
                        Notification.id.in_(notification_ids),
                        User.email.is_not(None),
                        User.is_active == True
                    )
                )
            )
            
            result = await db.execute(notifications_query)
            notification_user_pairs = result.fetchall()
            
            email_service = EmailService()
            results = []
            
            for notification, user in notification_user_pairs:
                try:
                    success = await email_service.send_notification_email(
                        to_email=user.email,
                        user_name=user.name,
                        title=notification.title,
                        content=notification.content,
                        notification_type=notification.type,
                        data=notification.data or {}
                    )
                    
                    results.append({
                        "notification_id": str(notification.id),
                        "user_id": str(user.id),
                        "email": user.email,
                        "success": success
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to send email to {user.email}: {e}")
                    results.append({
                        "notification_id": str(notification.id),
                        "user_id": str(user.id),
                        "email": user.email,
                        "success": False,
                        "error": str(e)
                    })
            
            successful_count = sum(1 for r in results if r.get("success"))
            
            return {
                "total_notifications": len(notification_ids),
                "processed_notifications": len(results),
                "successful_notifications": successful_count,
                "failed_notifications": len(results) - successful_count,
                "results": results,
                "processed_at": datetime.utcnow().isoformat()
            }
    
    async def on_success(self, task: TaskDefinition, result: Dict[str, Any]) -> None:
        """Handle successful bulk email sending."""
        logger.info(f"Bulk email notifications completed: {result['successful_notifications']}/{result['total_notifications']} successful")
    
    async def on_failure(self, task: TaskDefinition, error: Exception) -> None:
        """Handle failed bulk email sending."""
        logger.error(f"Bulk email notification task failed: {error}")


# Notification cleanup task handler
class NotificationCleanupHandler(TaskHandler):
    """Handler for cleaning up expired notifications."""
    
    def __init__(self):
        super().__init__("cleanup_expired_notifications")
    
    async def execute(self, task: TaskDefinition) -> Dict[str, Any]:
        """Clean up expired notifications."""
        async with get_db_session() as db:
            notification_service = NotificationService(db)
            deleted_count = await notification_service.cleanup_expired_notifications()
            
            return {
                "deleted_notifications": deleted_count,
                "cleaned_at": datetime.utcnow().isoformat()
            }
    
    async def on_success(self, task: TaskDefinition, result: Dict[str, Any]) -> None:
        """Handle successful cleanup."""
        logger.info(f"Cleaned up {result['deleted_notifications']} expired notifications")


# Scheduled notification task handler
class ScheduledNotificationHandler(TaskHandler):
    """Handler for sending scheduled notifications."""
    
    def __init__(self):
        super().__init__("send_scheduled_notification")
    
    async def execute(self, task: TaskDefinition) -> Dict[str, Any]:
        """Send a scheduled notification."""
        user_ids = [UUID(uid) for uid in task.payload["user_ids"]]
        title = task.payload["title"]
        content = task.payload["content"]
        notification_type = NotificationType(task.payload["type"])
        priority = NotificationPriority(task.payload.get("priority", NotificationPriority.NORMAL))
        data = task.payload.get("data", {})
        send_email = task.payload.get("send_email", False)
        
        async with get_db_session() as db:
            notification_service = NotificationService(db)
            
            notifications = await notification_service.create_bulk_notifications(
                user_ids=user_ids,
                title=title,
                content=content,
                notification_type=notification_type,
                priority=priority,
                data=data,
                send_email=send_email,
                send_push=True,
                send_immediately=True
            )
            
            return {
                "scheduled_notification_id": task.payload.get("scheduled_id"),
                "created_notifications": len(notifications),
                "notification_ids": [str(n.id) for n in notifications],
                "sent_at": datetime.utcnow().isoformat()
            }
    
    async def on_success(self, task: TaskDefinition, result: Dict[str, Any]) -> None:
        """Handle successful scheduled notification."""
        logger.info(f"Scheduled notification sent to {result['created_notifications']} users")


# Register notification handlers with task queue
def register_notification_handlers(task_queue):
    """Register all notification-related task handlers."""
    task_queue.register_handler(EmailNotificationHandler())
    task_queue.register_handler(BulkEmailNotificationHandler())
    task_queue.register_handler(NotificationCleanupHandler())
    task_queue.register_handler(ScheduledNotificationHandler())