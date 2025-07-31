#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket服务
提供实时进度更新和通知功能
"""

import asyncio
import json
import logging
import threading
import time
from typing import Dict, Set, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from src.models.task import Task, TaskStatus
from src.services.task_service import get_task_service
from src.infrastructure.logging import get_logger


class MessageType(Enum):
    """消息类型"""
    TASK_UPDATE = "task_update"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_STARTED = "task_started"
    TASK_PAUSED = "task_paused"
    TASK_RESUMED = "task_resumed"
    TASK_CANCELLED = "task_cancelled"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class WebSocketMessage:
    """WebSocket消息"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: datetime
    client_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type.value,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'client_id': self.client_id
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class WebSocketClient:
    """WebSocket客户端连接"""
    
    def __init__(self, client_id: str, websocket=None):
        self.client_id = client_id
        self.websocket = websocket
        self.subscribed_tasks: Set[str] = set()
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.is_active = True
    
    async def send_message(self, message: WebSocketMessage):
        """发送消息给客户端"""
        if self.websocket and self.is_active:
            try:
                await self.websocket.send(message.to_json())
                return True
            except Exception as e:
                logging.error(f"发送消息失败 {self.client_id}: {e}")
                self.is_active = False
                return False
        return False
    
    def subscribe_task(self, task_id: str):
        """订阅任务更新"""
        self.subscribed_tasks.add(task_id)
    
    def unsubscribe_task(self, task_id: str):
        """取消订阅任务更新"""
        self.subscribed_tasks.discard(task_id)
    
    def is_subscribed_to(self, task_id: str) -> bool:
        """检查是否订阅了指定任务"""
        return task_id in self.subscribed_tasks


class WebSocketService:
    """WebSocket服务"""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.WebSocketService")
        self.clients: Dict[str, WebSocketClient] = {}
        self.task_service = get_task_service()
        
        # 监控线程
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        self._last_task_states: Dict[str, Dict[str, Any]] = {}
        
        # 配置
        self.heartbeat_interval = 30  # 心跳间隔（秒）
        self.update_interval = 1      # 更新检查间隔（秒）
        
        self.logger.info("WebSocket服务已初始化")
    
    def start_monitoring(self):
        """启动监控线程"""
        if self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            self._stop_monitoring.clear()
            self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self._monitoring_thread.start()
            self.logger.info("WebSocket监控线程已启动")
    
    def stop_monitoring(self):
        """停止监控线程"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._stop_monitoring.set()
            self._monitoring_thread.join(timeout=5)
            self.logger.info("WebSocket监控线程已停止")
    
    def _monitoring_loop(self):
        """监控循环"""
        while not self._stop_monitoring.is_set():
            try:
                # 检查任务状态变化
                self._check_task_updates()
                
                # 发送心跳
                self._send_heartbeat()
                
                # 清理断开的连接
                self._cleanup_disconnected_clients()
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
                time.sleep(5)  # 错误后等待更长时间
    
    def _check_task_updates(self):
        """检查任务更新"""
        # 获取所有活跃任务
        active_statuses = [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PAUSED, 
                          TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        
        current_tasks = {}
        for status in active_statuses:
            for task in self.task_service.get_tasks_by_status(status):
                current_tasks[task.id] = self._task_to_update_data(task)
        
        # 检查变化
        for task_id, current_data in current_tasks.items():
            last_data = self._last_task_states.get(task_id)
            
            if last_data is None:
                # 新任务
                self._broadcast_task_message(MessageType.TASK_STARTED, task_id, current_data)
            elif self._has_task_changed(last_data, current_data):
                # 任务状态变化
                message_type = self._get_message_type_for_status(current_data['status'])
                self._broadcast_task_message(message_type, task_id, current_data)
        
        # 更新状态缓存
        self._last_task_states = current_tasks
    
    def _task_to_update_data(self, task: Task) -> Dict[str, Any]:
        """将任务转换为更新数据"""
        return {
            'id': task.id,
            'name': task.name,
            'status': task.status.value,
            'progress': task.progress.to_dict(),
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'duration': task.get_duration().total_seconds() if task.get_duration() else None,
            'errors': [error.to_dict() for error in task.errors[-3:]]  # 只发送最近3个错误
        }
    
    def _has_task_changed(self, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> bool:
        """检查任务是否有变化"""
        # 检查关键字段
        key_fields = ['status', 'progress', 'completed_at', 'errors']
        
        for field in key_fields:
            if old_data.get(field) != new_data.get(field):
                return True
        
        return False
    
    def _get_message_type_for_status(self, status: str) -> MessageType:
        """根据状态获取消息类型"""
        status_map = {
            'completed': MessageType.TASK_COMPLETED,
            'failed': MessageType.TASK_FAILED,
            'paused': MessageType.TASK_PAUSED,
            'cancelled': MessageType.TASK_CANCELLED,
            'running': MessageType.TASK_UPDATE
        }
        return status_map.get(status, MessageType.TASK_UPDATE)
    
    def _broadcast_task_message(self, message_type: MessageType, task_id: str, data: Dict[str, Any]):
        """广播任务消息"""
        message = WebSocketMessage(
            type=message_type,
            data=data,
            timestamp=datetime.now()
        )
        
        # 发送给订阅了该任务的客户端
        for client in self.clients.values():
            if client.is_subscribed_to(task_id) and client.is_active:
                asyncio.create_task(client.send_message(message))
    
    def _send_heartbeat(self):
        """发送心跳消息"""
        current_time = datetime.now()
        
        for client in self.clients.values():
            if client.is_active and (current_time - client.last_heartbeat).total_seconds() > self.heartbeat_interval:
                message = WebSocketMessage(
                    type=MessageType.HEARTBEAT,
                    data={'timestamp': current_time.isoformat()},
                    timestamp=current_time,
                    client_id=client.client_id
                )
                asyncio.create_task(client.send_message(message))
    
    def _cleanup_disconnected_clients(self):
        """清理断开的连接"""
        disconnected_clients = [
            client_id for client_id, client in self.clients.items()
            if not client.is_active
        ]
        
        for client_id in disconnected_clients:
            self.remove_client(client_id)
    
    def add_client(self, client_id: str, websocket=None) -> WebSocketClient:
        """添加客户端连接"""
        client = WebSocketClient(client_id, websocket)
        self.clients[client_id] = client
        
        self.logger.info(f"客户端连接: {client_id}")
        
        # 如果这是第一个客户端，启动监控
        if len(self.clients) == 1:
            self.start_monitoring()
        
        return client
    
    def remove_client(self, client_id: str):
        """移除客户端连接"""
        if client_id in self.clients:
            del self.clients[client_id]
            self.logger.info(f"客户端断开: {client_id}")
            
            # 如果没有客户端了，停止监控
            if not self.clients:
                self.stop_monitoring()
    
    def get_client(self, client_id: str) -> Optional[WebSocketClient]:
        """获取客户端"""
        return self.clients.get(client_id)
    
    def subscribe_client_to_task(self, client_id: str, task_id: str):
        """订阅客户端到任务"""
        client = self.get_client(client_id)
        if client:
            client.subscribe_task(task_id)
            
            # 立即发送当前任务状态
            task = self.task_service.get_task(task_id)
            if task:
                data = self._task_to_update_data(task)
                message = WebSocketMessage(
                    type=MessageType.TASK_UPDATE,
                    data=data,
                    timestamp=datetime.now(),
                    client_id=client_id
                )
                asyncio.create_task(client.send_message(message))
    
    def unsubscribe_client_from_task(self, client_id: str, task_id: str):
        """取消客户端任务订阅"""
        client = self.get_client(client_id)
        if client:
            client.unsubscribe_task(task_id)
    
    def broadcast_system_status(self):
        """广播系统状态"""
        try:
            status = self.task_service.get_system_stats()
            message = WebSocketMessage(
                type=MessageType.SYSTEM_STATUS,
                data=status,
                timestamp=datetime.now()
            )
            
            for client in self.clients.values():
                if client.is_active:
                    asyncio.create_task(client.send_message(message))
                    
        except Exception as e:
            self.logger.error(f"广播系统状态失败: {e}")
    
    def send_error_message(self, client_id: str, error_message: str):
        """发送错误消息"""
        client = self.get_client(client_id)
        if client:
            message = WebSocketMessage(
                type=MessageType.ERROR,
                data={'message': error_message},
                timestamp=datetime.now(),
                client_id=client_id
            )
            asyncio.create_task(client.send_message(message))
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        active_clients = sum(1 for client in self.clients.values() if client.is_active)
        
        return {
            'total_clients': len(self.clients),
            'active_clients': active_clients,
            'monitoring_active': self._monitoring_thread and self._monitoring_thread.is_alive(),
            'tracked_tasks': len(self._last_task_states)
        }
    
    def shutdown(self):
        """关闭服务"""
        self.logger.info("正在关闭WebSocket服务...")
        
        # 停止监控
        self.stop_monitoring()
        
        # 关闭所有连接
        for client in self.clients.values():
            client.is_active = False
        
        self.clients.clear()
        self._last_task_states.clear()
        
        self.logger.info("WebSocket服务已关闭")


# 全局WebSocket服务实例
_websocket_service: Optional[WebSocketService] = None


def get_websocket_service() -> WebSocketService:
    """获取WebSocket服务实例"""
    global _websocket_service
    if _websocket_service is None:
        _websocket_service = WebSocketService()
    return _websocket_service


def shutdown_websocket_service():
    """关闭WebSocket服务"""
    global _websocket_service
    if _websocket_service:
        _websocket_service.shutdown()
        _websocket_service = None


# Streamlit集成辅助函数
class StreamlitWebSocketAdapter:
    """Streamlit WebSocket适配器"""
    
    def __init__(self):
        self.websocket_service = get_websocket_service()
        self.client_id = self._get_or_create_client_id()
        
        # 确保客户端已注册
        if not self.websocket_service.get_client(self.client_id):
            self.websocket_service.add_client(self.client_id)
    
    def _get_or_create_client_id(self) -> str:
        """获取或创建客户端ID"""
        import streamlit as st
        
        if 'websocket_client_id' not in st.session_state:
            import uuid
            st.session_state.websocket_client_id = str(uuid.uuid4())
        
        return st.session_state.websocket_client_id
    
    def subscribe_to_task(self, task_id: str):
        """订阅任务更新"""
        self.websocket_service.subscribe_client_to_task(self.client_id, task_id)
    
    def unsubscribe_from_task(self, task_id: str):
        """取消订阅任务更新"""
        self.websocket_service.unsubscribe_client_from_task(self.client_id, task_id)
    
    def get_task_updates(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务更新（模拟实时更新）"""
        # 在实际的WebSocket实现中，这里会从消息队列获取更新
        # 这里我们直接从任务服务获取最新状态
        task_service = get_task_service()
        task = task_service.get_task(task_id)
        
        if task:
            return {
                'id': task.id,
                'name': task.name,
                'status': task.status.value,
                'progress': task.progress.to_dict(),
                'errors': [error.to_dict() for error in task.errors[-3:]]
            }
        
        return None


def get_streamlit_websocket_adapter() -> StreamlitWebSocketAdapter:
    """获取Streamlit WebSocket适配器"""
    return StreamlitWebSocketAdapter()