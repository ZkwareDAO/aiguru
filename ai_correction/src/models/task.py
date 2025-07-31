#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后台任务相关数据模型
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import uuid
from datetime import datetime, timedelta
import json


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"          # 等待中
    RUNNING = "running"          # 运行中
    PAUSED = "paused"           # 已暂停
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消
    RETRYING = "retrying"       # 重试中


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TaskType(Enum):
    """任务类型"""
    GRADING = "grading"                    # 批改任务
    FILE_PROCESSING = "file_processing"    # 文件处理
    REPORT_GENERATION = "report_generation" # 报告生成
    DATA_EXPORT = "data_export"            # 数据导出
    SYSTEM_MAINTENANCE = "system_maintenance" # 系统维护


@dataclass
class TaskError:
    """任务错误信息"""
    timestamp: datetime = field(default_factory=datetime.now)
    error_type: str = ""
    error_message: str = ""
    stack_trace: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'error_type': self.error_type,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace,
            'retry_count': self.retry_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskError':
        return cls(
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            error_type=data.get('error_type', ''),
            error_message=data.get('error_message', ''),
            stack_trace=data.get('stack_trace'),
            retry_count=data.get('retry_count', 0)
        )


@dataclass
class TaskProgress:
    """任务进度信息"""
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    percentage: float = 0.0
    estimated_remaining_time: Optional[timedelta] = None
    current_operation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'completed_steps': self.completed_steps,
            'percentage': self.percentage,
            'estimated_remaining_time': self.estimated_remaining_time.total_seconds() if self.estimated_remaining_time else None,
            'current_operation': self.current_operation
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskProgress':
        remaining_time = data.get('estimated_remaining_time')
        return cls(
            current_step=data.get('current_step', ''),
            total_steps=data.get('total_steps', 0),
            completed_steps=data.get('completed_steps', 0),
            percentage=data.get('percentage', 0.0),
            estimated_remaining_time=timedelta(seconds=remaining_time) if remaining_time else None,
            current_operation=data.get('current_operation', '')
        )


@dataclass
class TaskConfig:
    """任务配置"""
    max_retries: int = 3
    retry_delay: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    timeout: Optional[timedelta] = None
    auto_cleanup: bool = True
    cleanup_after: timedelta = field(default_factory=lambda: timedelta(days=7))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay.total_seconds(),
            'timeout': self.timeout.total_seconds() if self.timeout else None,
            'auto_cleanup': self.auto_cleanup,
            'cleanup_after': self.cleanup_after.total_seconds()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskConfig':
        timeout = data.get('timeout')
        return cls(
            max_retries=data.get('max_retries', 3),
            retry_delay=timedelta(seconds=data.get('retry_delay', 30)),
            timeout=timedelta(seconds=timeout) if timeout else None,
            auto_cleanup=data.get('auto_cleanup', True),
            cleanup_after=timedelta(seconds=data.get('cleanup_after', 7 * 24 * 3600))
        )


@dataclass
class Task:
    """后台任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    task_type: TaskType = TaskType.GRADING
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    
    # 任务数据
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    
    # 进度和状态
    progress: TaskProgress = field(default_factory=TaskProgress)
    errors: List[TaskError] = field(default_factory=list)
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)
    
    # 配置
    config: TaskConfig = field(default_factory=TaskConfig)
    
    # 用户信息
    created_by: Optional[str] = None
    
    # 依赖关系
    depends_on: List[str] = field(default_factory=list)  # 依赖的任务ID列表
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'task_type': self.task_type.value,
            'status': self.status.value,
            'priority': self.priority.value,
            'input_data': self.input_data,
            'output_data': self.output_data,
            'progress': self.progress.to_dict(),
            'errors': [error.to_dict() for error in self.errors],
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_updated': self.last_updated.isoformat(),
            'config': self.config.to_dict(),
            'created_by': self.created_by,
            'depends_on': self.depends_on
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """从字典创建"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            description=data.get('description', ''),
            task_type=TaskType(data.get('task_type', 'grading')),
            status=TaskStatus(data.get('status', 'pending')),
            priority=TaskPriority(data.get('priority', 2)),
            input_data=data.get('input_data', {}),
            output_data=data.get('output_data', {}),
            progress=TaskProgress.from_dict(data.get('progress', {})),
            errors=[TaskError.from_dict(error) for error in data.get('errors', [])],
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            last_updated=datetime.fromisoformat(data.get('last_updated', datetime.now().isoformat())),
            config=TaskConfig.from_dict(data.get('config', {})),
            created_by=data.get('created_by'),
            depends_on=data.get('depends_on', [])
        )
    
    def update_progress(self, current_step: str, completed_steps: int, total_steps: int, 
                       current_operation: str = "", estimated_remaining_time: Optional[timedelta] = None):
        """更新任务进度"""
        self.progress.current_step = current_step
        self.progress.completed_steps = completed_steps
        self.progress.total_steps = total_steps
        self.progress.percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        self.progress.current_operation = current_operation
        if estimated_remaining_time:
            self.progress.estimated_remaining_time = estimated_remaining_time
        self.last_updated = datetime.now()
    
    def add_error(self, error_type: str, error_message: str, stack_trace: Optional[str] = None):
        """添加错误信息"""
        error = TaskError(
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            retry_count=len([e for e in self.errors if e.error_type == error_type])
        )
        self.errors.append(error)
        self.last_updated = datetime.now()
    
    def can_retry(self) -> bool:
        """检查是否可以重试"""
        if self.status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        
        # 计算执行失败的次数（排除用户取消和系统错误）
        execution_failures = len([e for e in self.errors if e.error_type in ['execution_error', 'start_error']])
        return execution_failures < self.config.max_retries
    
    def get_duration(self) -> Optional[timedelta]:
        """获取任务执行时长"""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.now()
        return end_time - self.started_at
    
    def is_expired(self) -> bool:
        """检查任务是否已过期（用于清理）"""
        if not self.config.auto_cleanup:
            return False
        
        if self.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PAUSED, TaskStatus.RETRYING]:
            return False
        
        end_time = self.completed_at or self.last_updated
        return datetime.now() - end_time > self.config.cleanup_after


@dataclass
class TaskHistory:
    """任务历史记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    action: str = ""  # created, started, paused, resumed, completed, failed, cancelled
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'task_id': self.task_id,
            'action': self.action,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details,
            'user_id': self.user_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskHistory':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            task_id=data.get('task_id', ''),
            action=data.get('action', ''),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            details=data.get('details', {}),
            user_id=data.get('user_id')
        )