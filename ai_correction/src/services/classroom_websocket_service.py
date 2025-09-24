#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
班级作业批改WebSocket服务扩展
提供实时状态更新和通知推送
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from src.services.websocket_service import (
    WebSocketService, WebSocketMessage, MessageType, get_websocket_service
)
from src.models.assignment import Assignment
from src.models.submission import Submission, SubmissionStatus
from src.models.classroom_grading_task import ClassroomGradingTask
from src.infrastructure.logging import get_logger


class ClassroomMessageType(Enum):
    """班级消息类型"""
    ASSIGNMENT_PUBLISHED = "assignment_published"
    SUBMISSION_RECEIVED = "submission_received"
    GRADING_STARTED = "grading_started"
    GRADING_PROGRESS = "grading_progress"
    GRADING_COMPLETED = "grading_completed"
    GRADING_FAILED = "grading_failed"
    FEEDBACK_UPDATED = "feedback_updated"
    ASSIGNMENT_STATISTICS_UPDATED = "assignment_statistics_updated"
    CLASS_NOTIFICATION = "class_notification"


@dataclass
class ClassroomWebSocketMessage:
    """班级WebSocket消息"""
    type: ClassroomMessageType
    data: Dict[str, Any]
    timestamp: datetime
    class_id: Optional[int] = None
    assignment_id: Optional[int] = None
    student_username: Optional[str] = None
    teacher_username: Optional[str] = None
    
    def to_websocket_message(self) -> WebSocketMessage:
        """转换为标准WebSocket消息"""
        return WebSocketMessage(
            type=MessageType.SYSTEM_STATUS,  # 使用系统状态类型
            data={
                'classroom_type': self.type.value,
                'class_id': self.class_id,
                'assignment_id': self.assignment_id,
                'student_username': self.student_username,
                'teacher_username': self.teacher_username,
                **self.data
            },
            timestamp=self.timestamp
        )


class ClassroomWebSocketService:
    """班级WebSocket服务"""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.ClassroomWebSocketService")
        self.websocket_service = get_websocket_service()
        
        # 订阅管理
        self.class_subscriptions: Dict[int, List[str]] = {}  # class_id -> [client_ids]
        self.assignment_subscriptions: Dict[int, List[str]] = {}  # assignment_id -> [client_ids]
        self.student_subscriptions: Dict[str, List[str]] = {}  # student_username -> [client_ids]
        self.teacher_subscriptions: Dict[str, List[str]] = {}  # teacher_username -> [client_ids]
        
        self.logger.info("班级WebSocket服务已初始化")
    
    def subscribe_to_class(self, client_id: str, class_id: int):
        """订阅班级更新"""
        if class_id not in self.class_subscriptions:
            self.class_subscriptions[class_id] = []
        
        if client_id not in self.class_subscriptions[class_id]:
            self.class_subscriptions[class_id].append(client_id)
            self.logger.info(f"客户端 {client_id} 订阅班级 {class_id}")
    
    def unsubscribe_from_class(self, client_id: str, class_id: int):
        """取消订阅班级更新"""
        if class_id in self.class_subscriptions:
            if client_id in self.class_subscriptions[class_id]:
                self.class_subscriptions[class_id].remove(client_id)
                self.logger.info(f"客户端 {client_id} 取消订阅班级 {class_id}")
    
    def subscribe_to_assignment(self, client_id: str, assignment_id: int):
        """订阅作业更新"""
        if assignment_id not in self.assignment_subscriptions:
            self.assignment_subscriptions[assignment_id] = []
        
        if client_id not in self.assignment_subscriptions[assignment_id]:
            self.assignment_subscriptions[assignment_id].append(client_id)
            self.logger.info(f"客户端 {client_id} 订阅作业 {assignment_id}")
    
    def unsubscribe_from_assignment(self, client_id: str, assignment_id: int):
        """取消订阅作业更新"""
        if assignment_id in self.assignment_subscriptions:
            if client_id in self.assignment_subscriptions[assignment_id]:
                self.assignment_subscriptions[assignment_id].remove(client_id)
                self.logger.info(f"客户端 {client_id} 取消订阅作业 {assignment_id}")
    
    def subscribe_to_student_updates(self, client_id: str, student_username: str):
        """订阅学生更新"""
        if student_username not in self.student_subscriptions:
            self.student_subscriptions[student_username] = []
        
        if client_id not in self.student_subscriptions[student_username]:
            self.student_subscriptions[student_username].append(client_id)
            self.logger.info(f"客户端 {client_id} 订阅学生 {student_username}")
    
    def subscribe_to_teacher_updates(self, client_id: str, teacher_username: str):
        """订阅教师更新"""
        if teacher_username not in self.teacher_subscriptions:
            self.teacher_subscriptions[teacher_username] = []
        
        if client_id not in self.teacher_subscriptions[teacher_username]:
            self.teacher_subscriptions[teacher_username].append(client_id)
            self.logger.info(f"客户端 {client_id} 订阅教师 {teacher_username}")
    
    def broadcast_assignment_published(self, assignment: Assignment, teacher_name: str):
        """广播作业发布消息"""
        message = ClassroomWebSocketMessage(
            type=ClassroomMessageType.ASSIGNMENT_PUBLISHED,
            data={
                'assignment': {
                    'id': assignment.id,
                    'title': assignment.title,
                    'description': assignment.description,
                    'deadline': assignment.deadline.isoformat() if assignment.deadline else None,
                    'created_at': assignment.created_at.isoformat()
                },
                'teacher_name': teacher_name
            },
            timestamp=datetime.now(),
            class_id=assignment.class_id,
            assignment_id=assignment.id
        )
        
        self._broadcast_to_class(assignment.class_id, message)
        self.logger.info(f"广播作业发布消息: {assignment.title}")
    
    def broadcast_submission_received(self, submission: Submission, assignment: Assignment, 
                                    student_name: str):
        """广播学生提交消息"""
        message = ClassroomWebSocketMessage(
            type=ClassroomMessageType.SUBMISSION_RECEIVED,
            data={
                'submission': {
                    'id': submission.id,
                    'assignment_id': submission.assignment_id,
                    'student_username': submission.student_username,
                    'submitted_at': submission.submitted_at.isoformat(),
                    'status': submission.status.value
                },
                'assignment_title': assignment.title,
                'student_name': student_name
            },
            timestamp=datetime.now(),
            class_id=assignment.class_id,
            assignment_id=assignment.id,
            student_username=submission.student_username
        )
        
        # 通知教师和班级
        self._broadcast_to_assignment(assignment.id, message)
        self.logger.info(f"广播学生提交消息: {student_name} -> {assignment.title}")
    
    def broadcast_grading_started(self, task: ClassroomGradingTask, assignment: Assignment):
        """广播批改开始消息"""
        message = ClassroomWebSocketMessage(
            type=ClassroomMessageType.GRADING_STARTED,
            data={
                'task_id': task.submission_id,  # 使用submission_id作为任务标识
                'assignment_id': task.assignment_id,
                'student_username': task.student_username,
                'assignment_title': assignment.title,
                'started_at': datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            class_id=assignment.class_id,
            assignment_id=assignment.id,
            student_username=task.student_username
        )
        
        # 通知学生和教师
        self._broadcast_to_student(task.student_username, message)
        self._broadcast_to_assignment(assignment.id, message)
        self.logger.info(f"广播批改开始消息: {task.student_username} -> {assignment.title}")
    
    def broadcast_grading_progress(self, submission_id: int, assignment: Assignment,
                                 student_username: str, progress: Dict[str, Any]):
        """广播批改进度消息"""
        message = ClassroomWebSocketMessage(
            type=ClassroomMessageType.GRADING_PROGRESS,
            data={
                'submission_id': submission_id,
                'assignment_id': assignment.id,
                'student_username': student_username,
                'assignment_title': assignment.title,
                'progress': progress,
                'updated_at': datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            class_id=assignment.class_id,
            assignment_id=assignment.id,
            student_username=student_username
        )
        
        # 通知学生和教师
        self._broadcast_to_student(student_username, message)
        self._broadcast_to_assignment(assignment.id, message)
        self.logger.info(f"广播批改进度消息: {student_username} -> {assignment.title}, 进度: {progress}")
    
    def broadcast_grading_completed(self, submission: Submission, assignment: Assignment,
                                  score: Optional[float] = None):
        """广播批改完成消息"""
        message = ClassroomWebSocketMessage(
            type=ClassroomMessageType.GRADING_COMPLETED,
            data={
                'submission': {
                    'id': submission.id,
                    'assignment_id': submission.assignment_id,
                    'student_username': submission.student_username,
                    'status': submission.status.value,
                    'score': score,
                    'graded_at': submission.graded_at.isoformat() if submission.graded_at else None
                },
                'assignment_title': assignment.title,
                'completed_at': datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            class_id=assignment.class_id,
            assignment_id=assignment.id,
            student_username=submission.student_username
        )
        
        # 通知学生和教师
        self._broadcast_to_student(submission.student_username, message)
        self._broadcast_to_assignment(assignment.id, message)
        self.logger.info(f"广播批改完成消息: {submission.student_username} -> {assignment.title}")
    
    def broadcast_grading_failed(self, submission_id: int, assignment: Assignment,
                               student_username: str, error_message: str):
        """广播批改失败消息"""
        message = ClassroomWebSocketMessage(
            type=ClassroomMessageType.GRADING_FAILED,
            data={
                'submission_id': submission_id,
                'assignment_id': assignment.id,
                'student_username': student_username,
                'assignment_title': assignment.title,
                'error_message': error_message,
                'failed_at': datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            class_id=assignment.class_id,
            assignment_id=assignment.id,
            student_username=student_username
        )
        
        # 通知学生和教师
        self._broadcast_to_student(student_username, message)
        self._broadcast_to_assignment(assignment.id, message)
        self.logger.info(f"广播批改失败消息: {student_username} -> {assignment.title}, 错误: {error_message}")
    
    def broadcast_feedback_updated(self, submission: Submission, assignment: Assignment):
        """广播反馈更新消息"""
        message = ClassroomWebSocketMessage(
            type=ClassroomMessageType.FEEDBACK_UPDATED,
            data={
                'submission': {
                    'id': submission.id,
                    'assignment_id': submission.assignment_id,
                    'student_username': submission.student_username,
                    'score': submission.score,
                    'teacher_feedback': submission.teacher_feedback
                },
                'assignment_title': assignment.title,
                'updated_at': datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            class_id=assignment.class_id,
            assignment_id=assignment.id,
            student_username=submission.student_username
        )
        
        # 通知学生
        self._broadcast_to_student(submission.student_username, message)
        self.logger.info(f"广播反馈更新消息: {submission.student_username} -> {assignment.title}")
    
    def broadcast_assignment_statistics_updated(self, assignment: Assignment, 
                                              statistics: Dict[str, Any]):
        """广播作业统计更新消息"""
        message = ClassroomWebSocketMessage(
            type=ClassroomMessageType.ASSIGNMENT_STATISTICS_UPDATED,
            data={
                'assignment_id': assignment.id,
                'assignment_title': assignment.title,
                'statistics': statistics,
                'updated_at': datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            class_id=assignment.class_id,
            assignment_id=assignment.id
        )
        
        # 通知班级所有订阅者
        self._broadcast_to_assignment(assignment.id, message)
        self.logger.info(f"广播作业统计更新消息: {assignment.title}")
    
    def broadcast_class_notification(self, class_id: int, title: str, content: str,
                                   sender_name: str, notification_type: str = "info"):
        """广播班级通知消息"""
        message = ClassroomWebSocketMessage(
            type=ClassroomMessageType.CLASS_NOTIFICATION,
            data={
                'title': title,
                'content': content,
                'sender_name': sender_name,
                'notification_type': notification_type,
                'sent_at': datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            class_id=class_id
        )
        
        self._broadcast_to_class(class_id, message)
        self.logger.info(f"广播班级通知消息: {title} -> 班级 {class_id}")
    
    def _broadcast_to_class(self, class_id: int, message: ClassroomWebSocketMessage):
        """向班级广播消息"""
        client_ids = self.class_subscriptions.get(class_id, [])
        self._send_to_clients(client_ids, message)
    
    def _broadcast_to_assignment(self, assignment_id: int, message: ClassroomWebSocketMessage):
        """向作业订阅者广播消息"""
        client_ids = self.assignment_subscriptions.get(assignment_id, [])
        self._send_to_clients(client_ids, message)
    
    def _broadcast_to_student(self, student_username: str, message: ClassroomWebSocketMessage):
        """向学生广播消息"""
        client_ids = self.student_subscriptions.get(student_username, [])
        self._send_to_clients(client_ids, message)
    
    def _broadcast_to_teacher(self, teacher_username: str, message: ClassroomWebSocketMessage):
        """向教师广播消息"""
        client_ids = self.teacher_subscriptions.get(teacher_username, [])
        self._send_to_clients(client_ids, message)
    
    def _send_to_clients(self, client_ids: List[str], message: ClassroomWebSocketMessage):
        """向指定客户端发送消息"""
        websocket_message = message.to_websocket_message()
        
        for client_id in client_ids:
            client = self.websocket_service.get_client(client_id)
            if client and client.is_active:
                try:
                    import asyncio
                    asyncio.create_task(client.send_message(websocket_message))
                except Exception as e:
                    self.logger.error(f"发送消息到客户端 {client_id} 失败: {e}")
    
    def cleanup_client_subscriptions(self, client_id: str):
        """清理客户端订阅"""
        # 清理班级订阅
        for class_id, clients in self.class_subscriptions.items():
            if client_id in clients:
                clients.remove(client_id)
        
        # 清理作业订阅
        for assignment_id, clients in self.assignment_subscriptions.items():
            if client_id in clients:
                clients.remove(client_id)
        
        # 清理学生订阅
        for student_username, clients in self.student_subscriptions.items():
            if client_id in clients:
                clients.remove(client_id)
        
        # 清理教师订阅
        for teacher_username, clients in self.teacher_subscriptions.items():
            if client_id in clients:
                clients.remove(client_id)
        
        self.logger.info(f"已清理客户端 {client_id} 的所有订阅")
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """获取订阅统计信息"""
        return {
            'class_subscriptions': {
                class_id: len(clients) 
                for class_id, clients in self.class_subscriptions.items()
            },
            'assignment_subscriptions': {
                assignment_id: len(clients)
                for assignment_id, clients in self.assignment_subscriptions.items()
            },
            'student_subscriptions': {
                student: len(clients)
                for student, clients in self.student_subscriptions.items()
            },
            'teacher_subscriptions': {
                teacher: len(clients)
                for teacher, clients in self.teacher_subscriptions.items()
            },
            'total_subscriptions': (
                len(self.class_subscriptions) +
                len(self.assignment_subscriptions) +
                len(self.student_subscriptions) +
                len(self.teacher_subscriptions)
            )
        }


# 全局班级WebSocket服务实例
_classroom_websocket_service: Optional[ClassroomWebSocketService] = None


def get_classroom_websocket_service() -> ClassroomWebSocketService:
    """获取班级WebSocket服务实例"""
    global _classroom_websocket_service
    if _classroom_websocket_service is None:
        _classroom_websocket_service = ClassroomWebSocketService()
    return _classroom_websocket_service


# Streamlit集成辅助类
class StreamlitClassroomWebSocketAdapter:
    """Streamlit班级WebSocket适配器"""
    
    def __init__(self):
        self.classroom_service = get_classroom_websocket_service()
        self.client_id = self._get_or_create_client_id()
        
        # 确保WebSocket客户端已注册
        websocket_service = get_websocket_service()
        if not websocket_service.get_client(self.client_id):
            websocket_service.add_client(self.client_id)
    
    def _get_or_create_client_id(self) -> str:
        """获取或创建客户端ID"""
        import streamlit as st
        
        if 'classroom_websocket_client_id' not in st.session_state:
            import uuid
            st.session_state.classroom_websocket_client_id = str(uuid.uuid4())
        
        return st.session_state.classroom_websocket_client_id
    
    def subscribe_to_class(self, class_id: int):
        """订阅班级更新"""
        self.classroom_service.subscribe_to_class(self.client_id, class_id)
    
    def subscribe_to_assignment(self, assignment_id: int):
        """订阅作业更新"""
        self.classroom_service.subscribe_to_assignment(self.client_id, assignment_id)
    
    def subscribe_to_student_updates(self, student_username: str):
        """订阅学生更新"""
        self.classroom_service.subscribe_to_student_updates(self.client_id, student_username)
    
    def subscribe_to_teacher_updates(self, teacher_username: str):
        """订阅教师更新"""
        self.classroom_service.subscribe_to_teacher_updates(self.client_id, teacher_username)
    
    def unsubscribe_all(self):
        """取消所有订阅"""
        self.classroom_service.cleanup_client_subscriptions(self.client_id)


def get_streamlit_classroom_websocket_adapter() -> StreamlitClassroomWebSocketAdapter:
    """获取Streamlit班级WebSocket适配器"""
    return StreamlitClassroomWebSocketAdapter()