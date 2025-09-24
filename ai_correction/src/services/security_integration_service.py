#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全集成服务
整合权限控制、审计日志和数据加密功能
"""

from typing import Dict, List, Optional, Any, Callable
from functools import wraps
import logging
from datetime import datetime

from .permission_service import (
    PermissionService, Permission, UserRole, AccessContext,
    permission_service
)
from .audit_service import (
    AuditService, AuditEvent, AuditEventType, AuditLevel,
    audit_service
)
from .encryption_service import (
    EncryptionService, SensitiveDataManager,
    encryption_service, sensitive_data_manager
)

# 配置日志
logger = logging.getLogger(__name__)


class SecurityIntegrationService:
    """安全集成服务"""
    
    def __init__(self, 
                 permission_service: PermissionService = None,
                 audit_service: AuditService = None,
                 encryption_service: EncryptionService = None):
        """
        初始化安全集成服务
        
        Args:
            permission_service: 权限服务实例
            audit_service: 审计服务实例
            encryption_service: 加密服务实例
        """
        self.permission_service = permission_service or globals()['permission_service']
        self.audit_service = audit_service or globals()['audit_service']
        self.encryption_service = encryption_service or globals()['encryption_service']
        self.sensitive_data_manager = SensitiveDataManager(self.encryption_service)
    
    def secure_operation(self, user_id: str, user_role: str, operation: str,
                        resource_type: str, resource_id: str = None,
                        permission: Permission = None, 
                        operation_func: Callable = None,
                        operation_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行安全操作（权限检查 + 审计日志 + 数据保护）
        
        Args:
            user_id: 用户ID
            user_role: 用户角色
            operation: 操作类型
            resource_type: 资源类型
            resource_id: 资源ID
            permission: 需要的权限
            operation_func: 要执行的操作函数
            operation_data: 操作数据
            
        Returns:
            操作结果字典
        """
        result = {
            'success': False,
            'message': '',
            'data': None,
            'audit_logged': False
        }
        
        try:
            # 1. 权限检查
            if permission:
                context = AccessContext(
                    user_id=user_id,
                    user_role=UserRole(user_role),
                    resource_id=resource_id,
                    resource_type=resource_type
                )
                
                if not self.permission_service.has_permission(context, permission):
                    # 记录权限拒绝
                    self.audit_service.log_permission_denied(
                        user_id=user_id,
                        user_role=user_role,
                        resource_type=resource_type,
                        resource_id=resource_id or '',
                        action=operation,
                        reason=f"缺少权限: {permission.value}"
                    )
                    
                    result['message'] = f"权限不足，无法执行操作: {operation}"
                    result['audit_logged'] = True
                    return result
            
            # 2. 执行操作
            operation_result = None
            if operation_func:
                operation_result = operation_func(operation_data or {})
            
            # 3. 记录审计日志
            self._log_operation_audit(
                user_id=user_id,
                user_role=user_role,
                operation=operation,
                resource_type=resource_type,
                resource_id=resource_id,
                success=True,
                additional_data=operation_data
            )
            
            result['success'] = True
            result['message'] = f"操作 {operation} 执行成功"
            result['data'] = operation_result
            result['audit_logged'] = True
            
        except Exception as e:
            logger.error(f"安全操作执行失败: {e}")
            
            # 记录错误审计日志
            self.audit_service.log_system_error(
                error_message=f"操作 {operation} 执行失败: {str(e)}",
                user_id=user_id,
                additional_data={
                    'resource_type': resource_type,
                    'resource_id': resource_id,
                    'operation': operation
                }
            )
            
            result['message'] = f"操作执行失败: {str(e)}"
            result['audit_logged'] = True
        
        return result
    
    def _log_operation_audit(self, user_id: str, user_role: str, operation: str,
                           resource_type: str, resource_id: str = None,
                           success: bool = True, additional_data: Dict = None):
        """记录操作审计日志"""
        # 根据操作类型和资源类型选择合适的审计方法
        if resource_type == 'assignment':
            self.audit_service.log_assignment_operation(
                user_id=user_id,
                user_role=user_role,
                assignment_id=resource_id or '',
                action=operation,
                description=f"用户 {user_id} {operation} 作业 {resource_id}"
            )
        elif resource_type == 'submission':
            self.audit_service.log_submission_operation(
                user_id=user_id,
                user_role=user_role,
                submission_id=resource_id or '',
                action=operation,
                description=f"用户 {user_id} {operation} 提交 {resource_id}"
            )
        elif resource_type == 'grading':
            self.audit_service.log_grading_operation(
                user_id=user_id,
                user_role=user_role,
                submission_id=resource_id or '',
                action=operation,
                description=f"用户 {user_id} {operation} 批改 {resource_id}",
                additional_data=additional_data
            )
        else:
            # 通用审计日志
            event = AuditEvent(
                event_type=AuditEventType.SYSTEM_ERROR if not success else AuditEventType.USER_LOGIN,
                level=AuditLevel.ERROR if not success else AuditLevel.INFO,
                user_id=user_id,
                user_role=user_role,
                resource_type=resource_type,
                resource_id=resource_id,
                action=operation,
                description=f"用户 {user_id} {operation} {resource_type} {resource_id}",
                additional_data=additional_data or {}
            )
            self.audit_service.log_event(event)
    
    def secure_data_access(self, user_id: str, user_role: str, 
                          data_type: str, data_id: str,
                          access_type: str = 'read') -> Dict[str, Any]:
        """
        安全数据访问
        
        Args:
            user_id: 用户ID
            user_role: 用户角色
            data_type: 数据类型
            data_id: 数据ID
            access_type: 访问类型 ('read', 'write', 'delete')
            
        Returns:
            访问结果
        """
        # 检查访问权限
        can_access = self.permission_service.can_access_resource(
            user_id=user_id,
            user_role=user_role,
            resource_type=data_type,
            resource_id=data_id,
            action=access_type
        )
        
        if not can_access:
            # 记录未授权访问尝试
            self.audit_service.log_event(AuditEvent(
                event_type=AuditEventType.UNAUTHORIZED_ACCESS,
                level=AuditLevel.WARNING,
                user_id=user_id,
                user_role=user_role,
                resource_type=data_type,
                resource_id=data_id,
                action=access_type,
                description=f"用户 {user_id} 尝试未授权访问 {data_type} {data_id}"
            ))
            
            return {
                'success': False,
                'message': '访问被拒绝：权限不足',
                'data': None
            }
        
        # 记录数据访问
        self.audit_service.log_event(AuditEvent(
            event_type=AuditEventType.ASSIGNMENT_VIEW,  # 根据实际数据类型调整
            level=AuditLevel.INFO,
            user_id=user_id,
            user_role=user_role,
            resource_type=data_type,
            resource_id=data_id,
            action=access_type,
            description=f"用户 {user_id} {access_type} {data_type} {data_id}"
        ))
        
        return {
            'success': True,
            'message': '访问授权成功',
            'data': {'access_granted': True}
        }
    
    def encrypt_sensitive_data(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """
        加密敏感数据
        
        Args:
            data: 要加密的数据
            data_type: 数据类型
            
        Returns:
            加密后的数据
        """
        try:
            if data_type == 'user':
                return self.sensitive_data_manager.encrypt_user_data(data)
            elif data_type == 'submission':
                return self.sensitive_data_manager.encrypt_submission_data(data)
            elif data_type == 'assignment':
                return self.sensitive_data_manager.encrypt_assignment_data(data)
            else:
                logger.warning(f"未知的数据类型: {data_type}")
                return data
                
        except Exception as e:
            logger.error(f"数据加密失败: {e}")
            raise
    
    def decrypt_sensitive_data(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """
        解密敏感数据
        
        Args:
            data: 要解密的数据
            data_type: 数据类型
            
        Returns:
            解密后的数据
        """
        try:
            if data_type == 'user':
                return self.sensitive_data_manager.decrypt_user_data(data)
            elif data_type == 'submission':
                return self.sensitive_data_manager.decrypt_submission_data(data)
            elif data_type == 'assignment':
                return self.sensitive_data_manager.decrypt_assignment_data(data)
            else:
                logger.warning(f"未知的数据类型: {data_type}")
                return data
                
        except Exception as e:
            logger.error(f"数据解密失败: {e}")
            raise
    
    def get_security_summary(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """
        获取用户安全摘要
        
        Args:
            user_id: 用户ID
            days: 统计天数
            
        Returns:
            安全摘要信息
        """
        try:
            # 获取用户活动摘要
            activity_summary = self.audit_service.get_user_activity_summary(user_id, days)
            
            # 检测可疑活动
            suspicious_activities = self.audit_service.detect_suspicious_activities(hours=days*24)
            user_suspicious = [
                activity for activity in suspicious_activities 
                if activity.get('user_id') == user_id
            ]
            
            # 统计权限拒绝次数
            permission_denied_count = activity_summary['event_types'].get('permission_denied', 0)
            
            return {
                'user_id': user_id,
                'period_days': days,
                'total_activities': activity_summary['total_events'],
                'activity_types': activity_summary['event_types'],
                'daily_activity': activity_summary['daily_activity'],
                'permission_denied_count': permission_denied_count,
                'suspicious_activities_count': len(user_suspicious),
                'suspicious_activities': user_suspicious,
                'security_score': self._calculate_security_score(
                    activity_summary, user_suspicious, permission_denied_count
                )
            }
            
        except Exception as e:
            logger.error(f"获取安全摘要失败: {e}")
            return {
                'user_id': user_id,
                'error': str(e)
            }
    
    def _calculate_security_score(self, activity_summary: Dict, 
                                 suspicious_activities: List, 
                                 permission_denied_count: int) -> int:
        """
        计算安全评分（0-100）
        
        Args:
            activity_summary: 活动摘要
            suspicious_activities: 可疑活动列表
            permission_denied_count: 权限拒绝次数
            
        Returns:
            安全评分
        """
        base_score = 100
        
        # 可疑活动扣分
        base_score -= len(suspicious_activities) * 10
        
        # 权限拒绝扣分
        base_score -= min(permission_denied_count * 5, 30)
        
        # 异常时间活动扣分
        unusual_hours_activities = [
            activity for activity in suspicious_activities
            if activity.get('type') == 'unusual_hours'
        ]
        base_score -= len(unusual_hours_activities) * 5
        
        return max(0, min(100, base_score))
    
    def perform_security_audit(self, hours: int = 24) -> Dict[str, Any]:
        """
        执行安全审计
        
        Args:
            hours: 审计时间范围（小时）
            
        Returns:
            审计结果
        """
        try:
            # 检测可疑活动
            suspicious_activities = self.audit_service.detect_suspicious_activities(hours)
            
            # 统计各类安全事件
            security_events = self.audit_service.get_events(
                event_type=None,
                start_time=datetime.now() - timedelta(hours=hours),
                limit=1000
            )
            
            event_stats = {}
            for event in security_events:
                event_type = event.event_type.value
                event_stats[event_type] = event_stats.get(event_type, 0) + 1
            
            # 识别高风险用户
            high_risk_users = []
            user_risk_scores = {}
            
            for activity in suspicious_activities:
                user_id = activity.get('user_id')
                if user_id:
                    user_risk_scores[user_id] = user_risk_scores.get(user_id, 0) + 1
            
            # 风险评分超过阈值的用户
            for user_id, risk_score in user_risk_scores.items():
                if risk_score >= 3:  # 阈值可配置
                    high_risk_users.append({
                        'user_id': user_id,
                        'risk_score': risk_score,
                        'activities': [
                            a for a in suspicious_activities 
                            if a.get('user_id') == user_id
                        ]
                    })
            
            return {
                'audit_period_hours': hours,
                'total_events': len(security_events),
                'event_statistics': event_stats,
                'suspicious_activities_count': len(suspicious_activities),
                'suspicious_activities': suspicious_activities,
                'high_risk_users_count': len(high_risk_users),
                'high_risk_users': high_risk_users,
                'recommendations': self._generate_security_recommendations(
                    suspicious_activities, high_risk_users
                )
            }
            
        except Exception as e:
            logger.error(f"安全审计执行失败: {e}")
            return {
                'error': str(e),
                'audit_period_hours': hours
            }
    
    def _generate_security_recommendations(self, suspicious_activities: List,
                                         high_risk_users: List) -> List[str]:
        """生成安全建议"""
        recommendations = []
        
        if len(suspicious_activities) > 10:
            recommendations.append("检测到大量可疑活动，建议加强监控")
        
        if len(high_risk_users) > 0:
            recommendations.append(f"发现 {len(high_risk_users)} 个高风险用户，建议进行人工审核")
        
        # 检查特定类型的可疑活动
        rapid_access_count = len([a for a in suspicious_activities if a.get('type') == 'rapid_access'])
        if rapid_access_count > 5:
            recommendations.append("检测到多个快速访问异常，建议实施访问频率限制")
        
        bulk_download_count = len([a for a in suspicious_activities if a.get('type') == 'bulk_download'])
        if bulk_download_count > 3:
            recommendations.append("检测到批量下载异常，建议审查文件访问权限")
        
        if not recommendations:
            recommendations.append("当前安全状况良好，建议继续保持监控")
        
        return recommendations


def secure_endpoint(permission: Permission = None, resource_type: str = None,
                   audit_operation: str = None):
    """
    安全端点装饰器
    整合权限检查和审计日志
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 提取用户信息
            user_id = kwargs.get('user_id') or kwargs.get('username')
            user_role = kwargs.get('user_role')
            resource_id = kwargs.get('resource_id') or kwargs.get('assignment_id') or kwargs.get('submission_id')
            
            if not user_id or not user_role:
                raise ValueError("缺少用户身份信息")
            
            security_service = SecurityIntegrationService()
            
            # 执行安全操作
            def operation_func(data):
                return func(*args, **kwargs)
            
            result = security_service.secure_operation(
                user_id=user_id,
                user_role=user_role,
                operation=audit_operation or func.__name__,
                resource_type=resource_type or 'unknown',
                resource_id=str(resource_id) if resource_id else None,
                permission=permission,
                operation_func=operation_func,
                operation_data=kwargs
            )
            
            if not result['success']:
                raise PermissionError(result['message'])
            
            return result['data']
        
        return wrapper
    return decorator


# 全局安全集成服务实例
security_integration_service = SecurityIntegrationService()