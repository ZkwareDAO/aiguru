#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖注入容器
简单的依赖注入容器实现
"""

from typing import Dict, Any, Type, TypeVar
import logging

T = TypeVar('T')


class DIContainer:
    """依赖注入容器"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
    
    def register(self, service_type: Type[T], instance: T, singleton: bool = True):
        """注册服务"""
        service_name = service_type.__name__
        
        if singleton:
            self._singletons[service_name] = instance
        else:
            self._services[service_name] = instance
        
        self.logger.info(f"服务已注册: {service_name}")
    
    def get(self, service_type: Type[T]) -> T:
        """获取服务"""
        service_name = service_type.__name__
        
        # 先检查单例
        if service_name in self._singletons:
            return self._singletons[service_name]
        
        # 再检查普通服务
        if service_name in self._services:
            return self._services[service_name]
        
        # 如果没有找到，尝试创建
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
        return service_name in self._singletons or service_name in self._services


def configure_services() -> DIContainer:
    """配置服务容器"""
    container = DIContainer()
    
    # 这里可以注册各种服务
    # 目前保持简单，让容器自动创建服务
    
    return container