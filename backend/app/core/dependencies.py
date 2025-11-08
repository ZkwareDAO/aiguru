"""FastAPI dependencies for authentication and authorization."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import auth_manager, TokenData
from app.core.database import get_db
from app.core.permissions import Permission, PermissionManager, ResourceType
from app.models.user import User, UserRole
from app.services.user_service import UserService


# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """Get current user token data from JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token = credentials.credentials
    
    # Check if token is blacklisted
    if await auth_manager.is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已失效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    token_data = auth_manager.verify_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception
    
    return token_data


async def get_current_user(
    token_data: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    user_service = UserService(db)
    
    try:
        user_id = UUID(token_data.user_id)
        user = await user_service.get_user_by_id(user_id)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户账户已被禁用",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的用户ID",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户未激活"
        )
    return current_user


def require_role(required_role: UserRole):
    """Dependency factory for role-based access control."""
    
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要{required_role.value}角色权限"
            )
        return current_user
    
    return role_checker


def require_roles(*required_roles: UserRole):
    """Dependency factory for multiple role-based access control."""
    
    def roles_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in required_roles:
            roles_str = "或".join([role.value for role in required_roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要{roles_str}角色权限"
            )
        return current_user
    
    return roles_checker


# Common role dependencies
require_student = require_role(UserRole.STUDENT)
require_teacher = require_role(UserRole.TEACHER)
require_parent = require_role(UserRole.PARENT)
require_teacher_or_parent = require_roles(UserRole.TEACHER, UserRole.PARENT)


class PermissionChecker:
    """Permission checker for resource-based access control."""
    
    @staticmethod
    async def can_access_user_data(
        target_user_id: UUID,
        current_user: User,
        db: AsyncSession
    ) -> bool:
        """Check if current user can access target user's data."""
        # Users can always access their own data
        if current_user.id == target_user_id:
            return True
        
        # Teachers can access their students' data
        if current_user.is_teacher:
            user_service = UserService(db)
            return await user_service.is_teacher_of_student(
                current_user.id, target_user_id
            )
        
        # Parents can access their children's data
        if current_user.is_parent:
            user_service = UserService(db)
            return await user_service.is_parent_of_student(
                current_user.id, target_user_id
            )
        
        return False
    
    @staticmethod
    async def can_access_class_data(
        class_id: UUID,
        current_user: User,
        db: AsyncSession
    ) -> bool:
        """Check if current user can access class data."""
        from app.services.class_service import ClassService
        
        class_service = ClassService(db)
        
        # Teachers can access classes they teach
        if current_user.is_teacher:
            return await class_service.is_class_teacher(class_id, current_user.id)
        
        # Students can access classes they're enrolled in
        if current_user.is_student:
            return await class_service.is_student_in_class(class_id, current_user.id)
        
        # Parents can access classes their children are in
        if current_user.is_parent:
            return await class_service.is_parent_child_in_class(class_id, current_user.id)
        
        return False
    
    @staticmethod
    async def can_access_assignment_data(
        assignment_id: UUID,
        current_user: User,
        db: AsyncSession
    ) -> bool:
        """Check if current user can access assignment data."""
        from app.services.assignment_service import AssignmentService
        
        assignment_service = AssignmentService(db)
        
        # Teachers can access assignments they created
        if current_user.is_teacher:
            return await assignment_service.is_assignment_teacher(
                assignment_id, current_user.id
            )
        
        # Students can access assignments in their classes
        if current_user.is_student:
            return await assignment_service.can_student_access_assignment(
                assignment_id, current_user.id
            )
        
        # Parents can access assignments their children have
        if current_user.is_parent:
            return await assignment_service.can_parent_access_assignment(
                assignment_id, current_user.id
            )
        
        return False


def require_permission(permission_func):
    """Decorator for permission-based access control."""
    
    def permission_decorator(*args, **kwargs):
        async def permission_checker(
            current_user: User = Depends(get_current_active_user),
            db: AsyncSession = Depends(get_db)
        ) -> User:
            # Extract resource ID from kwargs or args
            resource_id = kwargs.get('resource_id') or (args[0] if args else None)
            
            if resource_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="缺少资源ID"
                )
            
            has_permission = await permission_func(resource_id, current_user, db)
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="没有访问此资源的权限"
                )
            
            return current_user
        
        return permission_checker
    
    return permission_decorator


# Permission-based dependencies
def require_permission_dep(permission: Permission):
    """Dependency factory for permission-based access control."""
    
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        permission_manager = PermissionManager(db)
        
        if not permission_manager.has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要{permission.value}权限"
            )
        
        return current_user
    
    return permission_checker


def require_resource_permission_dep(
    resource_type: ResourceType,
    permission: Permission,
    resource_id_param: str = "resource_id"
):
    """Dependency factory for resource-based permission checking."""
    
    async def resource_permission_checker(
        resource_id: UUID,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        permission_manager = PermissionManager(db)
        
        has_permission = await permission_manager.can_access_resource(
            current_user, resource_type, resource_id, permission
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"没有访问此{resource_type.value}的{permission.value}权限"
            )
        
        return current_user
    
    return resource_permission_checker


# Common permission dependencies
require_user_read = require_permission_dep(Permission.USER_READ)
require_user_write = require_permission_dep(Permission.USER_WRITE)
require_user_admin = require_permission_dep(Permission.USER_ADMIN)

require_class_read = require_permission_dep(Permission.CLASS_READ)
require_class_write = require_permission_dep(Permission.CLASS_WRITE)
require_class_admin = require_permission_dep(Permission.CLASS_ADMIN)

require_assignment_read = require_permission_dep(Permission.ASSIGNMENT_READ)
require_assignment_write = require_permission_dep(Permission.ASSIGNMENT_WRITE)
require_assignment_grade = require_permission_dep(Permission.ASSIGNMENT_GRADE)

require_ai_grading = require_permission_dep(Permission.AI_GRADING_USE)
require_ai_agent = require_permission_dep(Permission.AI_AGENT_USE)

require_analytics_read = require_permission_dep(Permission.ANALYTICS_READ)
require_analytics_admin = require_permission_dep(Permission.ANALYTICS_ADMIN)

require_system_admin = require_permission_dep(Permission.SYSTEM_ADMIN)

# Resource-based permission dependencies
require_user_access = require_resource_permission_dep(ResourceType.USER, Permission.USER_READ)
require_class_access = require_resource_permission_dep(ResourceType.CLASS, Permission.CLASS_READ)
require_assignment_access = require_resource_permission_dep(ResourceType.ASSIGNMENT, Permission.ASSIGNMENT_READ)