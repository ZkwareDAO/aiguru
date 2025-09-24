#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
班级批改任务相关数据模型
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid

from .task import TaskPriority
from .grading_config import GradingConfig


class ClassroomTaskStatus(Enum):
    """班级批改任务状态"""
    PENDING = "pending"          # 等待中
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消
    RETRYING = "retrying"       # 重试中


@dataclass
class ClassroomGradingTask:
    """班级批改任务数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    submission_id: int = 0
    assignment_id: int = 0
    student_username: str = ""
    answer_files: List[str] = field(default_factory=list)
    marking_files: List[str] = field(default_factory=list)
    grading_config: Optional[GradingConfig] = None
    priority: TaskPriority = TaskPriority.NORMAL
    status: ClassroomTaskStatus = ClassroomTaskStatus.PENDING
    
    # 任务执行信息
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)
    
    # 结果信息
    result_score: Optional[float] = None
    result_feedback: Optional[str] = None
    confidence_score: Optional[float] = None
    criteria_scores: Dict[str, float] = field(default_factory=dict)
    improvement_suggestions: List[str] = field(default_factory=list)
    
    # 错误信息
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # 元数据
    created_by: Optional[str] = None
    processing_node: Optional[str] = None  # 处理节点标识
    estimated_duration: Optional[int] = None  # 预估处理时间（秒）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'submission_id': self.submission_id,
            'assignment_id': self.assignment_id,
            'student_username': self.student_username,
            'answer_files': self.answer_files,
            'marking_files': self.marking_files,
            'grading_config': self.grading_config.to_dict() if self.grading_config else None,
            'priority': self.priority.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_updated': self.last_updated.isoformat(),
            'result_score': self.result_score,
            'result_feedback': self.result_feedback,
            'confidence_score': self.confidence_score,
            'criteria_scores': self.criteria_scores,
            'improvement_suggestions': self.improvement_suggestions,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'created_by': self.created_by,
            'processing_node': self.processing_node,
            'estimated_duration': self.estimated_duration
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClassroomGradingTask':
        """从字典创建"""
        grading_config = None
        if data.get('grading_config'):
            grading_config = GradingConfig.from_dict(data['grading_config'])
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            submission_id=data.get('submission_id', 0),
            assignment_id=data.get('assignment_id', 0),
            student_username=data.get('student_username', ''),
            answer_files=data.get('answer_files', []),
            marking_files=data.get('marking_files', []),
            grading_config=grading_config,
            priority=TaskPriority(data.get('priority', 2)),
            status=ClassroomTaskStatus(data.get('status', 'pending')),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            last_updated=datetime.fromisoformat(data.get('last_updated', datetime.now().isoformat())),
            result_score=data.get('result_score'),
            result_feedback=data.get('result_feedback'),
            confidence_score=data.get('confidence_score'),
            criteria_scores=data.get('criteria_scores', {}),
            improvement_suggestions=data.get('improvement_suggestions', []),
            error_message=data.get('error_message'),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            created_by=data.get('created_by'),
            processing_node=data.get('processing_node'),
            estimated_duration=data.get('estimated_duration')
        )
    
    def validate(self) -> List[str]:
        """验证任务数据"""
        errors = []
        
        if self.submission_id <= 0:
            errors.append("提交ID必须大于0")
        
        if self.assignment_id <= 0:
            errors.append("作业ID必须大于0")
        
        if not self.student_username.strip():
            errors.append("学生用户名不能为空")
        
        if not self.answer_files:
            errors.append("至少需要一个答案文件")
        
        # 验证文件路径格式
        for file_path in self.answer_files:
            if not isinstance(file_path, str) or not file_path.strip():
                errors.append("答案文件路径格式无效")
                break
        
        for file_path in self.marking_files:
            if not isinstance(file_path, str) or not file_path.strip():
                errors.append("批改标准文件路径格式无效")
                break
        
        # 验证分数范围
        if self.result_score is not None and (self.result_score < 0 or self.result_score > 100):
            errors.append("结果分数必须在0-100之间")
        
        # 验证置信度范围
        if self.confidence_score is not None and (self.confidence_score < 0 or self.confidence_score > 1):
            errors.append("置信度分数必须在0-1之间")
        
        # 验证重试次数
        if self.retry_count < 0:
            errors.append("重试次数不能为负数")
        
        if self.max_retries < 0:
            errors.append("最大重试次数不能为负数")
        
        return errors
    
    def start_processing(self, processing_node: Optional[str] = None):
        """开始处理任务"""
        if self.status != ClassroomTaskStatus.PENDING:
            return False
        
        self.status = ClassroomTaskStatus.PROCESSING
        self.started_at = datetime.now()
        self.last_updated = datetime.now()
        if processing_node:
            self.processing_node = processing_node
        
        return True
    
    def complete_with_result(self, score: float, feedback: str, confidence: Optional[float] = None,
                           criteria_scores: Optional[Dict[str, float]] = None,
                           suggestions: Optional[List[str]] = None):
        """完成任务并设置结果"""
        if self.status != ClassroomTaskStatus.PROCESSING:
            return False
        
        self.status = ClassroomTaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.last_updated = datetime.now()
        
        self.result_score = score
        self.result_feedback = feedback
        if confidence is not None:
            self.confidence_score = confidence
        if criteria_scores:
            self.criteria_scores = criteria_scores
        if suggestions:
            self.improvement_suggestions = suggestions
        
        return True
    
    def fail_with_error(self, error_message: str):
        """任务失败并设置错误信息"""
        if self.status not in [ClassroomTaskStatus.PROCESSING, ClassroomTaskStatus.RETRYING]:
            return False
        
        self.status = ClassroomTaskStatus.FAILED
        self.last_updated = datetime.now()
        self.error_message = error_message
        
        return True
    
    def cancel(self):
        """取消任务"""
        if self.status in [ClassroomTaskStatus.COMPLETED, ClassroomTaskStatus.CANCELLED]:
            return False
        
        self.status = ClassroomTaskStatus.CANCELLED
        self.last_updated = datetime.now()
        
        return True
    
    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return (self.status == ClassroomTaskStatus.FAILED and 
                self.retry_count < self.max_retries)
    
    def retry(self) -> bool:
        """重试任务"""
        if not self.can_retry():
            return False
        
        self.status = ClassroomTaskStatus.RETRYING
        self.retry_count += 1
        self.last_updated = datetime.now()
        self.error_message = None
        
        return True
    
    def reset_for_retry(self):
        """重置任务状态以便重试"""
        if self.status == ClassroomTaskStatus.RETRYING:
            self.status = ClassroomTaskStatus.PENDING
            self.started_at = None
            self.processing_node = None
            self.last_updated = datetime.now()
    
    def get_duration(self) -> Optional[float]:
        """获取任务执行时长（秒）"""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    def get_wait_time(self) -> float:
        """获取任务等待时长（秒）"""
        start_time = self.started_at or datetime.now()
        return (start_time - self.created_at).total_seconds()
    
    def is_overdue(self, timeout_seconds: int = 3600) -> bool:
        """检查任务是否超时"""
        if self.status not in [ClassroomTaskStatus.PROCESSING, ClassroomTaskStatus.RETRYING]:
            return False
        
        if not self.started_at:
            return False
        
        return (datetime.now() - self.started_at).total_seconds() > timeout_seconds
    
    def get_priority_score(self) -> int:
        """获取优先级分数（用于排序）"""
        base_score = self.priority.value * 1000
        
        # 重试任务优先级更高
        if self.status == ClassroomTaskStatus.RETRYING:
            base_score += 500
        
        # 等待时间越长优先级越高
        wait_time_hours = self.get_wait_time() / 3600
        base_score += int(wait_time_hours * 10)
        
        return base_score
    
    def get_status_display(self) -> str:
        """获取状态显示文本"""
        status_map = {
            ClassroomTaskStatus.PENDING: "等待中",
            ClassroomTaskStatus.PROCESSING: "处理中",
            ClassroomTaskStatus.COMPLETED: "已完成",
            ClassroomTaskStatus.FAILED: "失败",
            ClassroomTaskStatus.CANCELLED: "已取消",
            ClassroomTaskStatus.RETRYING: "重试中"
        }
        return status_map.get(self.status, "未知状态")
    
    def get_progress_info(self) -> Dict[str, Any]:
        """获取进度信息"""
        return {
            'status': self.status.value,
            'status_display': self.get_status_display(),
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self.get_duration(),
            'wait_time': self.get_wait_time(),
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'can_retry': self.can_retry(),
            'is_overdue': self.is_overdue(),
            'priority': self.priority.value,
            'priority_score': self.get_priority_score()
        }
    
    def get_result_summary(self) -> Dict[str, Any]:
        """获取结果摘要"""
        return {
            'score': self.result_score,
            'feedback': self.result_feedback,
            'confidence': self.confidence_score,
            'criteria_scores': self.criteria_scores,
            'suggestions': self.improvement_suggestions,
            'has_result': self.status == ClassroomTaskStatus.COMPLETED,
            'error_message': self.error_message if self.status == ClassroomTaskStatus.FAILED else None
        }
    
    def update_priority(self, new_priority: TaskPriority) -> bool:
        """更新任务优先级"""
        if self.status in [ClassroomTaskStatus.COMPLETED, ClassroomTaskStatus.CANCELLED]:
            return False
        
        self.priority = new_priority
        self.last_updated = datetime.now()
        return True
    
    def add_marking_file(self, file_path: str) -> bool:
        """添加批改标准文件"""
        if file_path and file_path not in self.marking_files:
            self.marking_files.append(file_path)
            self.last_updated = datetime.now()
            return True
        return False
    
    def remove_marking_file(self, file_path: str) -> bool:
        """移除批改标准文件"""
        if file_path in self.marking_files:
            self.marking_files.remove(file_path)
            self.last_updated = datetime.now()
            return True
        return False
    
    def set_grading_config(self, config: GradingConfig):
        """设置批改配置"""
        self.grading_config = config
        self.last_updated = datetime.now()
    
    def get_file_info(self) -> Dict[str, Any]:
        """获取文件信息"""
        return {
            'answer_files_count': len(self.answer_files),
            'marking_files_count': len(self.marking_files),
            'answer_files': self.answer_files,
            'marking_files': self.marking_files,
            'has_grading_config': self.grading_config is not None
        }