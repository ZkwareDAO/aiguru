"""Notification service for assignment-related notifications."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment, Submission
from app.models.class_model import ClassStudent
from app.models.notification import Notification, NotificationType
from app.models.user import User, UserRole


class AssignmentNotificationService:
    """Service for managing assignment-related notifications."""

    def __init__(self, db: AsyncSession):
        self.db = db

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

        notifications = []
        for student in students:
            notification = Notification(
                user_id=student.id,
                type=NotificationType.ASSIGNMENT_PUBLISHED,
                title="新作业发布",
                content=f"教师发布了新作业：{assignment.title}",
                data={
                    "assignment_id": str(assignment.id),
                    "assignment_title": assignment.title,
                    "class_id": str(assignment.class_id),
                    "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                    "total_points": assignment.total_points
                },
                is_read=False
            )
            self.db.add(notification)
            notifications.append(notification)

        await self.db.commit()
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

        notifications = []
        for student in students:
            notification = Notification(
                user_id=student.id,
                type=NotificationType.ASSIGNMENT_DUE_SOON,
                title="作业即将截止",
                content=f"作业"{assignment.title}"将在{hours_before}小时后截止，请及时提交。",
                data={
                    "assignment_id": str(assignment.id),
                    "assignment_title": assignment.title,
                    "due_date": assignment.due_date.isoformat(),
                    "hours_before": hours_before
                },
                is_read=False
            )
            self.db.add(notification)
            notifications.append(notification)

        await self.db.commit()
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

        notifications = []
        for student in students:
            notification = Notification(
                user_id=student.id,
                type=NotificationType.ASSIGNMENT_OVERDUE,
                title="作业已逾期",
                content=f"作业"{assignment.title}"已逾期，请尽快联系教师。",
                data={
                    "assignment_id": str(assignment.id),
                    "assignment_title": assignment.title,
                    "due_date": assignment.due_date.isoformat(),
                    "overdue_hours": int((datetime.utcnow() - assignment.due_date.replace(tzinfo=None)).total_seconds() / 3600)
                },
                is_read=False
            )
            self.db.add(notification)
            notifications.append(notification)

        await self.db.commit()
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

        notification = Notification(
            user_id=assignment.teacher_id,
            type=NotificationType.SUBMISSION_RECEIVED,
            title="收到新的作业提交",
            content=f"学生 {student.name} 提交了作业"{assignment.title}"。",
            data={
                "assignment_id": str(assignment.id),
                "assignment_title": assignment.title,
                "submission_id": str(submission.id),
                "student_id": str(student.id),
                "student_name": student.name,
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                "is_late": submission.is_late
            },
            is_read=False
        )
        self.db.add(notification)
        await self.db.commit()
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

        notification = Notification(
            user_id=submission.student_id,
            type=NotificationType.SUBMISSION_GRADED,
            title="作业已批改",
            content=f"您的作业"{assignment.title}"已批改完成，得分：{submission.score}/{submission.max_score}。",
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
            is_read=False
        )
        self.db.add(notification)
        await self.db.commit()
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

        notification = Notification(
            user_id=submission.student_id,
            type=NotificationType.SUBMISSION_RETURNED,
            title="作业已返还",
            content=f"您的作业"{assignment.title}"已返还，请查看批改结果和反馈。",
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
            is_read=False
        )
        self.db.add(notification)
        await self.db.commit()
        return notification

    async def get_assignment_notifications(
        self,
        user_id: UUID,
        assignment_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[Notification]:
        """Get assignment-related notifications for a user."""
        query = (
            select(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.type.in_([
                        NotificationType.ASSIGNMENT_PUBLISHED,
                        NotificationType.ASSIGNMENT_DUE_SOON,
                        NotificationType.ASSIGNMENT_OVERDUE,
                        NotificationType.SUBMISSION_RECEIVED,
                        NotificationType.SUBMISSION_GRADED,
                        NotificationType.SUBMISSION_RETURNED
                    ])
                )
            )
        )

        if assignment_id:
            # Filter by assignment_id in the data field
            # This is a simplified approach - in production you might want to use JSON operators
            query = query.where(
                Notification.data.contains(f'"assignment_id": "{assignment_id}"')
            )

        query = query.order_by(Notification.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def mark_notifications_read(
        self,
        user_id: UUID,
        notification_ids: List[UUID]
    ) -> int:
        """Mark multiple notifications as read."""
        from sqlalchemy import update

        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.id.in_(notification_ids)
                )
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def get_unread_count(
        self,
        user_id: UUID,
        assignment_related_only: bool = True
    ) -> int:
        """Get count of unread notifications."""
        from sqlalchemy import func

        query = (
            select(func.count(Notification.id))
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                )
            )
        )

        if assignment_related_only:
            query = query.where(
                Notification.type.in_([
                    NotificationType.ASSIGNMENT_PUBLISHED,
                    NotificationType.ASSIGNMENT_DUE_SOON,
                    NotificationType.ASSIGNMENT_OVERDUE,
                    NotificationType.SUBMISSION_RECEIVED,
                    NotificationType.SUBMISSION_GRADED,
                    NotificationType.SUBMISSION_RETURNED
                ])
            )

        result = await self.db.execute(query)
        return result.scalar() or 0