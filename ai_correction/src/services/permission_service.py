#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
权限控制服务
实现基于角色的权限控制系统
"""

from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass
from functools import wraps
import logging
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)


class UserRole(Enum):
    """用户角色"""
    TEACHER = "teacher"
    STUDENT = "student"
    ADMIN = "admin"


class Permission(Enum):
    """权限类型"""
    # 作业相关权限
    CREATE_ASSIGNMENT = "create_assignment"
    VIEW_ASSIGNMENT = "view_assignment"
    EDIT_ASSIGNMENT = "edit_assignment"
    DELETE_ASSIGNMENT = "delete_assignment"
    
    # 提交相关权限
    SUBMIT_ASSIGNMENT = "submit_assignment"
    VIEW_SUBMISSION = "view_submission"
    EDIT_SUBMISSION = "edit_submission"
    DELETE_SUBMISSION = "delete_submission"
    
    # 批改相关权限
    GRADE_SUBMISSION = "grade_submission"
    VIEW_GRADING_RESULT = "view_grading_result"
    MODIFY_GRADING_RESULT = "modify_grading_result"
    
    # 班级相关权限
    CREATE_CLASS = "create_class"
    VIEW_CLASS = "view_class"
    MANAGE_CLASS = "manage_class"
    JOIN_CLASS = "join_class"
    LEAVE_CLASS = "leave_class"
    
    # 用户相关权限
    VIEW_USER_INFO = "view_user_info"
    MANAGE_USERS = "manage_users"
    
    # 系统相关权限
    VIEW_SYSTEM_LOGS = "view_system_logs"
    MANAGE_SYSTEM = "manage_system"


@dataclass
class AccessContext:
    """访问上下文"""
    user_id: str
    user_role: UserRole
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    additional_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}


class PermissionService:
    """权限控制服务"""
    
    def __init__(self):
        self._role_permissions = self._initialize_role_permissions()
        self._resource_checkers = self._initialize_resource_checkers()
    
    def _initialize_role_permissions(self) -> Dict[UserRole, List[Permission]]:
        """初始化角色权限映射"""
        return {
            UserRole.TEACHER: [
                # 作业权限
                Permission.CREATE_ASSIGNMENT,
                Permission.VIEW_ASSIGNMENT,
                Permission.EDIT_ASSIGNMENT,
                Permission.DELETE_ASSIGNMENT,
                
                # 提交权限（查看学生提交）
                Permission.VIEW_SUBMISSION,
                
                # 批改权限
                Permission.GRADE_SUBMISSION,
                Permission.VIEW_GRADING_RESULT,
                Permission.MODIFY_GRADING_RESULT,
                
                # 班级权限
                Permission.CREATE_CLASS,
                Permission.VIEW_CLASS,
                Permission.MANAGE_CLASS,
                
                # 用户权限
                Permission.VIEW_USER_INFO,
            ],
            
            UserRole.STUDENT: [
                # 作业权限（查看）
                Permission.VIEW_ASSIGNMENT,
                
                # 提交权限
                Permission.SUBMIT_ASSIGNMENT,
                Permission.VIEW_SUBMISSION,
                Permission.EDIT_SUBMISSION,
                
                # 批改权限（查看自己的结果）
                Permission.VIEW_GRADING_RESULT,
                
                # 班级权限
                Permission.VIEW_CLASS,
                Permission.JOIN_CLASS,
                Permission.LEAVE_CLASS,
                
                # 用户权限
                Permission.VIEW_USER_INFO,
            ],
            
            UserRole.ADMIN: [
                # 管理员拥有所有权限
                *list(Permission)
            ]
        }
    
    def _initialize_resource_checkers(self) -> Dict[str, Callable]:
        """初始化资源检查器"""
        return {
            'assignment': self._check_assignment_access,
            'submission': self._check_submission_access,
            'class': self._check_class_access,
            'grading_result': self._check_grading_result_access,
        }
    
    def has_permission(self, context: AccessContext, permission: Permission) -> bool:
        """检查用户是否有指定权限"""
        try:
            # 检查角色是否有该权限
            role_permissions = self._role_permissions.get(context.user_role, [])
            if permission not in role_permissions:
                logger.warning(f"用户 {context.user_id} 角色 {context.user_role.value} 没有权限 {permission.value}")
                return False
            
            # 如果有资源相关的检查，执行资源级别的权限检查
            if context.resource_type and context.resource_id:
                resource_checker = self._resource_checkers.get(context.resource_type)
                if resource_checker:
                    return resource_checker(context, permission)
            
            return True
            
        except Exception as e:
            logger.error(f"权限检查失败: {e}")
            return False
    
    def _check_assignment_access(self, context: AccessContext, permission: Permission) -> bool:
        """检查作业访问权限"""
        try:
            from database import get_assignment_by_id, get_user_classes
        except ImportError:
            # 如果无法导入数据库函数，返回False以确保安全
            logger.error("无法导入数据库函数")
            return False
        
        try:
            assignment = get_assignment_by_id(int(context.resource_id))
            if not assignment:
                return False
            
            # 教师只能管理自己创建的作业
            if context.user_role == UserRole.TEACHER:
                if permission in [Permission.EDIT_ASSIGNMENT, Permission.DELETE_ASSIGNMENT]:
                    # 检查是否是作业所属班级的教师
                    teacher_classes = get_user_classes(context.user_id, 'teacher')
                    class_ids = [cls['id'] for cls in teacher_classes]
                    return assignment['class_id'] in class_ids
                
                elif permission == Permission.VIEW_ASSIGNMENT:
                    # 教师可以查看自己班级的作业
                    teacher_classes = get_user_classes(context.user_id, 'teacher')
                    class_ids = [cls['id'] for cls in teacher_classes]
                    return assignment['class_id'] in class_ids
            
            # 学生只能查看自己班级的作业
            elif context.user_role == UserRole.STUDENT:
                if permission == Permission.VIEW_ASSIGNMENT:
                    student_classes = get_user_classes(context.user_id, 'student')
                    class_ids = [cls['id'] for cls in student_classes]
                    return assignment['class_id'] in class_ids
                
                elif permission == Permission.SUBMIT_ASSIGNMENT:
                    # 检查学生是否在作业所属班级中
                    student_classes = get_user_classes(context.user_id, 'student')
                    class_ids = [cls['id'] for cls in student_classes]
                    return assignment['class_id'] in class_ids
            
            return True
            
        except Exception as e:
            logger.error(f"作业权限检查失败: {e}")
            return False
    
    def _check_submission_access(self, context: AccessContext, permission: Permission) -> bool:
        """检查提交访问权限"""
        try:
            from database import get_db_connection
        except ImportError:
            logger.error("无法导入数据库函数")
            return False
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 获取提交信息
            cursor.execute('''
                SELECT s.*, a.class_id, c.teacher_username
                FROM submissions s
                JOIN assignments a ON s.assignment_id = a.id
                JOIN classes c ON a.class_id = c.id
                WHERE s.id = ?
            ''', (int(context.resource_id),))
            
            submission = cursor.fetchone()
            conn.close()
            
            if not submission:
                return False
            
            # 学生只能访问自己的提交
            if context.user_role == UserRole.STUDENT:
                if permission in [Permission.VIEW_SUBMISSION, Permission.EDIT_SUBMISSION]:
                    return submission['student_username'] == context.user_id
            
            # 教师只能访问自己班级学生的提交
            elif context.user_role == UserRole.TEACHER:
                if permission in [Permission.VIEW_SUBMISSION, Permission.GRADE_SUBMISSION]:
                    return submission['teacher_username'] == context.user_id
            
            return True
            
        except Exception as e:
            logger.error(f"提交权限检查失败: {e}")
            return False
    
    def _check_class_access(self, context: AccessContext, permission: Permission) -> bool:
        """检查班级访问权限"""
        try:
            from database import get_db_connection
        except ImportError:
            logger.error("无法导入数据库函数")
            return False
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 获取班级信息
            cursor.execute('''
                SELECT teacher_username FROM classes WHERE id = ?
            ''', (int(context.resource_id),))
            
            class_info = cursor.fetchone()
            if not class_info:
                conn.close()
                return False
            
            # 教师只能管理自己创建的班级
            if context.user_role == UserRole.TEACHER:
                if permission == Permission.MANAGE_CLASS:
                    result = class_info['teacher_username'] == context.user_id
                    conn.close()
                    return result
                elif permission == Permission.VIEW_CLASS:
                    # 教师可以查看自己的班级
                    result = class_info['teacher_username'] == context.user_id
                    conn.close()
                    return result
            
            # 学生只能查看自己加入的班级
            elif context.user_role == UserRole.STUDENT:
                if permission in [Permission.VIEW_CLASS, Permission.LEAVE_CLASS]:
                    cursor.execute('''
                        SELECT id FROM class_members 
                        WHERE class_id = ? AND student_username = ? AND is_active = 1
                    ''', (int(context.resource_id), context.user_id))
                    
                    result = cursor.fetchone() is not None
                    conn.close()
                    return result
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"班级权限检查失败: {e}")
            return False
    
    def _check_grading_result_access(self, context: AccessContext, permission: Permission) -> bool:
        """检查批改结果访问权限"""
        try:
            from database import get_db_connection
        except ImportError:
            logger.error("无法导入数据库函数")
            return False
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 获取批改结果信息
            cursor.execute('''
                SELECT s.student_username, a.class_id, c.teacher_username
                FROM submissions s
                JOIN assignments a ON s.assignment_id = a.id
                JOIN classes c ON a.class_id = c.id
                WHERE s.id = ?
            ''', (int(context.resource_id),))
            
            result_info = cursor.fetchone()
            conn.close()
            
            if not result_info:
                return False
            
            # 学生只能查看自己的批改结果
            if context.user_role == UserRole.STUDENT:
                if permission == Permission.VIEW_GRADING_RESULT:
                    return result_info['student_username'] == context.user_id
            
            # 教师可以查看和修改自己班级学生的批改结果
            elif context.user_role == UserRole.TEACHER:
                if permission in [Permission.VIEW_GRADING_RESULT, Permission.MODIFY_GRADING_RESULT]:
                    return result_info['teacher_username'] == context.user_id
            
            return True
            
        except Exception as e:
            logger.error(f"批改结果权限检查失败: {e}")
            return False
    
    def check_assignment_access(self, user_id: str, user_role: str, assignment_id: int, permission: Permission) -> bool:
        """检查作业访问权限的便捷方法"""
        context = AccessContext(
            user_id=user_id,
            user_role=UserRole(user_role),
            resource_id=str(assignment_id),
            resource_type='assignment'
        )
        return self.has_permission(context, permission)
    
    def check_submission_access(self, user_id: str, user_role: str, submission_id: int, permission: Permission) -> bool:
        """检查提交访问权限的便捷方法"""
        context = AccessContext(
            user_id=user_id,
            user_role=UserRole(user_role),
            resource_id=str(submission_id),
            resource_type='submission'
        )
        return self.has_permission(context, permission)
    
    def check_class_access(self, user_id: str, user_role: str, class_id: int, permission: Permission) -> bool:
        """检查班级访问权限的便捷方法"""
        context = AccessContext(
            user_id=user_id,
            user_role=UserRole(user_role),
            resource_id=str(class_id),
            resource_type='class'
        )
        return self.has_permission(context, permission)
    
    def check_grading_result_access(self, user_id: str, user_role: str, submission_id: int, permission: Permission) -> bool:
        """检查批改结果访问权限的便捷方法"""
        context = AccessContext(
            user_id=user_id,
            user_role=UserRole(user_role),
            resource_id=str(submission_id),
            resource_type='grading_result'
        )
        return self.has_permission(context, permission)
    
    def get_user_permissions(self, user_role: UserRole) -> List[Permission]:
        """获取用户角色的所有权限"""
        return self._role_permissions.get(user_role, [])
    
    def can_access_resource(self, user_id: str, user_role: str, resource_type: str, 
                           resource_id: str, action: str) -> bool:
        """通用资源访问检查"""
        try:
            # 将action映射到Permission
            action_permission_map = {
                'view': {
                    'assignment': Permission.VIEW_ASSIGNMENT,
                    'submission': Permission.VIEW_SUBMISSION,
                    'class': Permission.VIEW_CLASS,
                    'grading_result': Permission.VIEW_GRADING_RESULT,
                },
                'edit': {
                    'assignment': Permission.EDIT_ASSIGNMENT,
                    'submission': Permission.EDIT_SUBMISSION,
                    'class': Permission.MANAGE_CLASS,
                    'grading_result': Permission.MODIFY_GRADING_RESULT,
                },
                'delete': {
                    'assignment': Permission.DELETE_ASSIGNMENT,
                    'submission': Permission.DELETE_SUBMISSION,
                    'class': Permission.MANAGE_CLASS,
                },
                'create': {
                    'assignment': Permission.CREATE_ASSIGNMENT,
                    'class': Permission.CREATE_CLASS,
                },
                'submit': {
                    'assignment': Permission.SUBMIT_ASSIGNMENT,
                },
                'grade': {
                    'submission': Permission.GRADE_SUBMISSION,
                }
            }
            
            permission = action_permission_map.get(action, {}).get(resource_type)
            if not permission:
                logger.warning(f"未知的操作或资源类型: {action}, {resource_type}")
                return False
            
            context = AccessContext(
                user_id=user_id,
                user_role=UserRole(user_role),
                resource_id=resource_id,
                resource_type=resource_type
            )
            
            return self.has_permission(context, permission)
            
        except Exception as e:
            logger.error(f"资源访问检查失败: {e}")
            return False


def require_permission(permission: Permission, resource_type: str = None):
    """权限装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从参数中提取用户信息
            user_id = kwargs.get('user_id') or kwargs.get('username')
            user_role = kwargs.get('user_role')
            resource_id = kwargs.get('resource_id') or kwargs.get('assignment_id') or kwargs.get('submission_id') or kwargs.get('class_id')
            
            if not user_id or not user_role:
                raise PermissionError("缺少用户身份信息")
            
            permission_service = PermissionService()
            context = AccessContext(
                user_id=user_id,
                user_role=UserRole(user_role),
                resource_id=str(resource_id) if resource_id else None,
                resource_type=resource_type
            )
            
            if not permission_service.has_permission(context, permission):
                raise PermissionError(f"用户 {user_id} 没有权限执行操作 {permission.value}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*allowed_roles: UserRole):
    """角色装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_role = kwargs.get('user_role')
            if not user_role:
                raise PermissionError("缺少用户角色信息")
            
            if UserRole(user_role) not in allowed_roles:
                raise PermissionError(f"用户角色 {user_role} 无权限访问")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# 全局权限服务实例
permission_service = PermissionService()