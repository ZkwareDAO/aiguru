"""Database models."""

# Import all models to ensure they are registered with SQLAlchemy
from .user import User, UserRole, ParentStudentRelation
from .class_model import Class, ClassStudent
from .assignment import Assignment, AssignmentStatus, Submission, SubmissionStatus
from .file import File, FileType, FileStatus
from .ai import GradingTask, GradingTaskStatus, ChatMessage, MessageType
from .notification import Notification, NotificationType, NotificationPriority
from .analytics import LearningAnalytics

# Export all models
__all__ = [
    # User models
    "User",
    "UserRole",
    "ParentStudentRelation",
    
    # Class models
    "Class",
    "ClassStudent",
    
    # Assignment models
    "Assignment",
    "AssignmentStatus",
    "Submission",
    "SubmissionStatus",
    
    # File models
    "File",
    "FileType",
    "FileStatus",
    
    # AI models
    "GradingTask",
    "GradingTaskStatus",
    "ChatMessage",
    "MessageType",
    
    # Notification models
    "Notification",
    "NotificationType",
    "NotificationPriority",
    
    # Analytics models
    "LearningAnalytics",
]