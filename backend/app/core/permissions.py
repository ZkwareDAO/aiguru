"""Advanced permission system for role-based and resource-based access control."""

from enum import Enum
from typing import Dict, List, Set, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


class Permission(str, Enum):
    """System permissions."""
    
    # User management permissions
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_ADMIN = "user:admin"
    
    # Class management permissions
    CLASS_READ = "class:read"
    CLASS_WRITE = "class:write"
    CLASS_DELETE = "class:delete"
    CLASS_ADMIN = "class:admin"
    
    # Assignment permissions
    ASSIGNMENT_READ = "assignment:read"
    ASSIGNMENT_WRITE = "assignment:write"
    ASSIGNMENT_DELETE = "assignment:delete"
    ASSIGNMENT_GRADE = "assignment:grade"
    
    # File permissions
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    FILE_DELETE = "file:delete"
    
    # AI services permissions
    AI_GRADING_USE = "ai:grading:use"
    AI_AGENT_USE = "ai:agent:use"
    AI_ADMIN = "ai:admin"
    
    # Grading task permissions
    GRADING_TASK_READ = "grading_task:read"
    GRADING_TASK_WRITE = "grading_task:write"
    GRADING_TASK_DELETE = "grading_task:delete"
    
    # Analytics permissions
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_ADMIN = "analytics:admin"
    
    # System administration
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIG = "system:config"


class ResourceType(str, Enum):
    """Resource types for permission checking."""
    USER = "user"
    CLASS = "class"
    ASSIGNMENT = "assignment"
    FILE = "file"
    GRADING_TASK = "grading_task"
    CHAT_MESSAGE = "chat_message"
    NOTIFICATION = "notification"


# Role-based permission mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.STUDENT: {
        Permission.USER_READ,
        Permission.CLASS_READ,
        Permission.ASSIGNMENT_READ,
        Permission.FILE_READ,
        Permission.FILE_WRITE,
        Permission.AI_AGENT_USE,
        Permission.GRADING_TASK_READ,
        Permission.ANALYTICS_READ,
    },
    
    UserRole.TEACHER: {
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.CLASS_READ,
        Permission.CLASS_WRITE,
        Permission.CLASS_DELETE,
        Permission.ASSIGNMENT_READ,
        Permission.ASSIGNMENT_WRITE,
        Permission.ASSIGNMENT_DELETE,
        Permission.ASSIGNMENT_GRADE,
        Permission.FILE_READ,
        Permission.FILE_WRITE,
        Permission.FILE_DELETE,
        Permission.AI_GRADING_USE,
        Permission.AI_AGENT_USE,
        Permission.GRADING_TASK_READ,
        Permission.GRADING_TASK_WRITE,
        Permission.GRADING_TASK_DELETE,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_ADMIN,
    },
    
    UserRole.PARENT: {
        Permission.USER_READ,
        Permission.CLASS_READ,
        Permission.ASSIGNMENT_READ,
        Permission.FILE_READ,
        Permission.AI_AGENT_USE,
        Permission.ANALYTICS_READ,
    },
}


class PermissionManager:
    """Permission manager for checking user permissions."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        user_permissions = ROLE_PERMISSIONS.get(user.role, set())
        return permission in user_permissions
    
    def has_any_permission(self, user: User, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(self.has_permission(user, perm) for perm in permissions)
    
    def has_all_permissions(self, user: User, permissions: List[Permission]) -> bool:
        """Check if user has all of the specified permissions."""
        return all(self.has_permission(user, perm) for perm in permissions)
    
    def get_user_permissions(self, user: User) -> Set[Permission]:
        """Get all permissions for a user."""
        return ROLE_PERMISSIONS.get(user.role, set())
    
    async def can_access_resource(
        self,
        user: User,
        resource_type: ResourceType,
        resource_id: UUID,
        permission: Permission
    ) -> bool:
        """Check if user can access a specific resource with given permission."""
        # First check if user has the base permission
        if not self.has_permission(user, permission):
            return False
        
        # Then check resource-specific access
        return await self._check_resource_access(user, resource_type, resource_id)
    
    async def _check_resource_access(
        self,
        user: User,
        resource_type: ResourceType,
        resource_id: UUID
    ) -> bool:
        """Check resource-specific access rules."""
        if resource_type == ResourceType.USER:
            return await self._check_user_access(user, resource_id)
        elif resource_type == ResourceType.CLASS:
            return await self._check_class_access(user, resource_id)
        elif resource_type == ResourceType.ASSIGNMENT:
            return await self._check_assignment_access(user, resource_id)
        elif resource_type == ResourceType.FILE:
            return await self._check_file_access(user, resource_id)
        elif resource_type == ResourceType.GRADING_TASK:
            return await self._check_grading_task_access(user, resource_id)
        elif resource_type == ResourceType.CHAT_MESSAGE:
            return await self._check_chat_message_access(user, resource_id)
        elif resource_type == ResourceType.NOTIFICATION:
            return await self._check_notification_access(user, resource_id)
        
        return False
    
    async def _check_user_access(self, user: User, target_user_id: UUID) -> bool:
        """Check if user can access another user's data."""
        # Users can always access their own data
        if user.id == target_user_id:
            return True
        
        # Teachers can access their students' data
        if user.is_teacher:
            from app.services.user_service import UserService
            user_service = UserService(self.db)
            return await user_service.is_teacher_of_student(user.id, target_user_id)
        
        # Parents can access their children's data
        if user.is_parent:
            from app.services.user_service import UserService
            user_service = UserService(self.db)
            return await user_service.is_parent_of_student(user.id, target_user_id)
        
        return False
    
    async def _check_class_access(self, user: User, class_id: UUID) -> bool:
        """Check if user can access class data."""
        from app.services.class_service import ClassService
        
        class_service = ClassService(self.db)
        
        # Teachers can access classes they teach
        if user.is_teacher:
            return await class_service.is_class_teacher(class_id, user.id)
        
        # Students can access classes they're enrolled in
        if user.is_student:
            return await class_service.is_student_in_class(class_id, user.id)
        
        # Parents can access classes their children are in
        if user.is_parent:
            return await class_service.is_parent_child_in_class(class_id, user.id)
        
        return False
    
    async def _check_assignment_access(self, user: User, assignment_id: UUID) -> bool:
        """Check if user can access assignment data."""
        from app.services.assignment_service import AssignmentService
        
        assignment_service = AssignmentService(self.db)
        
        # Teachers can access assignments they created
        if user.is_teacher:
            return await assignment_service.is_assignment_teacher(assignment_id, user.id)
        
        # Students can access assignments in their classes
        if user.is_student:
            return await assignment_service.can_student_access_assignment(
                assignment_id, user.id
            )
        
        # Parents can access assignments their children have
        if user.is_parent:
            return await assignment_service.can_parent_access_assignment(
                assignment_id, user.id
            )
        
        return False
    
    async def _check_file_access(self, user: User, file_id: UUID) -> bool:
        """Check if user can access file data."""
        from app.services.file_service import FileService
        
        file_service = FileService(self.db)
        
        # Users can access files they uploaded
        if await file_service.is_file_owner(file_id, user.id):
            return True
        
        # Teachers can access files in their assignments/classes
        if user.is_teacher:
            return await file_service.can_teacher_access_file(file_id, user.id)
        
        # Parents can access their children's files
        if user.is_parent:
            return await file_service.can_parent_access_file(file_id, user.id)
        
        return False
    
    async def _check_grading_task_access(self, user: User, task_id: UUID) -> bool:
        """Check if user can access grading task data."""
        from app.services.grading_service import GradingService
        
        grading_service = GradingService(self.db)
        
        # Teachers can access grading tasks for their assignments
        if user.is_teacher:
            return await grading_service.can_teacher_access_task(task_id, user.id)
        
        # Students can access their own grading tasks
        if user.is_student:
            return await grading_service.can_student_access_task(task_id, user.id)
        
        # Parents can access their children's grading tasks
        if user.is_parent:
            return await grading_service.can_parent_access_task(task_id, user.id)
        
        return False
    
    async def _check_chat_message_access(self, user: User, message_id: UUID) -> bool:
        """Check if user can access chat message data."""
        from app.services.ai_service import AIService
        
        ai_service = AIService(self.db)
        
        # Users can access their own chat messages
        return await ai_service.is_message_owner(message_id, user.id)
    
    async def _check_notification_access(self, user: User, notification_id: UUID) -> bool:
        """Check if user can access notification data."""
        from app.services.notification_service import NotificationService
        
        notification_service = NotificationService(self.db)
        
        # Users can access their own notifications
        return await notification_service.is_notification_owner(notification_id, user.id)


class PermissionDecorator:
    """Decorator for permission-based access control."""
    
    @staticmethod
    def require_permission(permission: Permission):
        """Decorator to require a specific permission."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # This would be used with FastAPI dependencies
                # Implementation depends on how it's integrated with the endpoint
                pass
            return wrapper
        return decorator
    
    @staticmethod
    def require_resource_access(
        resource_type: ResourceType,
        permission: Permission,
        resource_id_param: str = "resource_id"
    ):
        """Decorator to require resource-specific access."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # This would be used with FastAPI dependencies
                # Implementation depends on how it's integrated with the endpoint
                pass
            return wrapper
        return decorator


# Permission checking utilities
async def check_permission(
    user: User,
    permission: Permission,
    db: AsyncSession
) -> bool:
    """Utility function to check user permission."""
    permission_manager = PermissionManager(db)
    return permission_manager.has_permission(user, permission)


async def check_resource_permission(
    user: User,
    resource_type: ResourceType,
    resource_id: UUID,
    permission: Permission,
    db: AsyncSession
) -> bool:
    """Utility function to check resource-specific permission."""
    permission_manager = PermissionManager(db)
    return await permission_manager.can_access_resource(
        user, resource_type, resource_id, permission
    )


def get_role_permissions(role: UserRole) -> Set[Permission]:
    """Get all permissions for a role."""
    return ROLE_PERMISSIONS.get(role, set())


def can_role_access_permission(role: UserRole, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    role_permissions = ROLE_PERMISSIONS.get(role, set())
    return permission in role_permissions


def require_permission(user: User, permission_name: str) -> None:
    """Simple permission check that raises exception if user lacks permission."""
    from app.core.exceptions import InsufficientPermissionError
    
    # Map permission names to Permission enum values
    permission_map = {
        "create_grading_task": Permission.GRADING_TASK_WRITE,
        "update_grading_task": Permission.GRADING_TASK_WRITE,
        "retry_grading_task": Permission.GRADING_TASK_WRITE,
        "cancel_grading_task": Permission.GRADING_TASK_WRITE,
        "create_batch_grading_tasks": Permission.GRADING_TASK_WRITE,
        "view_grading_stats": Permission.GRADING_TASK_READ,
        "cleanup_grading_tasks": Permission.SYSTEM_ADMIN,
        "view_grading_analysis": Permission.GRADING_TASK_READ,
        "view_grading_quality": Permission.GRADING_TASK_READ,
        "detect_grading_anomalies": Permission.GRADING_TASK_READ,
        "view_grading_insights": Permission.GRADING_TASK_READ,
    }
    
    permission = permission_map.get(permission_name)
    if not permission:
        raise InsufficientPermissionError(f"Unknown permission: {permission_name}")
    
    user_permissions = ROLE_PERMISSIONS.get(user.role, set())
    if permission not in user_permissions:
        raise InsufficientPermissionError(
            f"User role {user.role} does not have permission: {permission_name}"
        )