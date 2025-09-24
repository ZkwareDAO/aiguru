#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖注入容器
简单的依赖注入容器实现
"""

from typing import Dict, Any, Type, TypeVar, Optional, Callable
import logging
from pathlib import Path

T = TypeVar('T')


class DIContainer:
    """依赖注入容器"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._singleton_factories: Dict[str, Callable[[], Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    def register(self, service_type: Type[T], instance: T, singleton: bool = True):
        """注册服务实例"""
        service_name = service_type.__name__
        
        if singleton:
            self._singletons[service_name] = instance
        else:
            self._services[service_name] = instance
        
        self.logger.info(f"服务已注册: {service_name}")
    
    def register_factory(self, service_type: Type[T], factory: Callable[[], T], singleton: bool = True):
        """注册服务工厂函数"""
        service_name = service_type.__name__
        
        if singleton:
            self._singleton_factories[service_name] = factory
        else:
            self._factories[service_name] = factory
        
        self.logger.info(f"服务工厂已注册: {service_name}")
    
    def get(self, service_type: Type[T]) -> T:
        """获取服务"""
        service_name = service_type.__name__
        
        # 先检查单例实例
        if service_name in self._singletons:
            return self._singletons[service_name]
        
        # 检查单例工厂
        if service_name in self._singleton_factories:
            instance = self._singleton_factories[service_name]()
            self._singletons[service_name] = instance
            self.logger.info(f"通过工厂创建单例服务: {service_name}")
            return instance
        
        # 检查普通服务实例
        if service_name in self._services:
            return self._services[service_name]
        
        # 检查普通工厂
        if service_name in self._factories:
            instance = self._factories[service_name]()
            self.logger.info(f"通过工厂创建服务: {service_name}")
            return instance
        
        # 如果没有找到，尝试自动创建
        try:
            instance = service_type()
            self._singletons[service_name] = instance
            self.logger.info(f"自动创建服务: {service_name}")
            return instance
        except Exception as e:
            self.logger.error(f"无法创建服务 {service_name}: {e}")
            raise
    
    def has(self, service_type: Type[T]) -> bool:
        """检查是否有服务"""
        service_name = service_type.__name__
        return (service_name in self._singletons or 
                service_name in self._services or
                service_name in self._singleton_factories or
                service_name in self._factories)
    
    def clear(self):
        """清空容器"""
        self._services.clear()
        self._singletons.clear()
        self._factories.clear()
        self._singleton_factories.clear()
        self.logger.info("容器已清空")


def configure_services() -> DIContainer:
    """配置服务容器"""
    container = DIContainer()
    
    # 导入所有需要注册的服务
    from src.services.assignment_service import AssignmentService
    from src.services.submission_service import SubmissionService
    from src.services.classroom_grading_service import ClassroomGradingService
    from src.services.task_service import TaskService, get_task_service
    from src.services.grading_config_service import GradingConfigService
    from src.services.notification_service import NotificationService
    from src.services.permission_service import PermissionService
    from src.services.audit_service import AuditService
    from src.services.encryption_service import EncryptionService
    from src.services.file_manager import FileManager
    from src.services.file_security import FileSecurityValidator
    from src.services.file_storage_manager import FileStorageManager
    from src.services.websocket_service import WebSocketService
    from src.services.classroom_websocket_service import ClassroomWebSocketService
    from src.services.task_queue_integration import TaskQueueIntegration
    from src.config.settings import get_settings
    
    # 获取配置
    settings = get_settings()
    
    # 注册核心服务工厂
    container.register_factory(TaskService, lambda: get_task_service())
    
    # 注册文件管理服务
    container.register_factory(FileSecurityValidator, lambda: FileSecurityValidator())
    container.register_factory(FileStorageManager, lambda: FileStorageManager())
    container.register_factory(FileManager, lambda: FileManager())
    
    # 注册安全服务
    container.register_factory(EncryptionService, lambda: EncryptionService())
    container.register_factory(AuditService, lambda: AuditService())
    container.register_factory(PermissionService, lambda: PermissionService())
    
    # 注册通信服务
    container.register_factory(WebSocketService, lambda: WebSocketService())
    container.register_factory(ClassroomWebSocketService, lambda: ClassroomWebSocketService())
    container.register_factory(NotificationService, lambda: NotificationService())
    
    # 注册批改配置服务
    container.register_factory(GradingConfigService, lambda: GradingConfigService())
    
    # 注册班级批改核心服务
    container.register_factory(AssignmentService, lambda: AssignmentService())
    container.register_factory(SubmissionService, lambda: SubmissionService())
    
    container.register_factory(ClassroomGradingService, lambda: ClassroomGradingService(
        grading_config_service=container.get(GradingConfigService)
    ))
    
    # 注册任务队列集成服务
    container.register_factory(TaskQueueIntegration, lambda: TaskQueueIntegration(
        task_service=container.get(TaskService),
        grading_service=container.get(ClassroomGradingService)
    ))
    
    container.logger.info("所有班级批改服务已注册到依赖注入容器")
    return container


# 全局容器实例
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """获取全局依赖注入容器"""
    global _container
    if _container is None:
        _container = configure_services()
    return _container


def reset_container():
    """重置容器（主要用于测试）"""
    global _container
    if _container:
        _container.clear()
    _container = None