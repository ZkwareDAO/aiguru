#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作业相关数据模型
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from .grading_config import GradingConfig


@dataclass
class Assignment:
    """作业数据模型"""
    id: Optional[int] = None
    class_id: int = 0
    title: str = ""
    description: str = ""
    question_files: List[str] = field(default_factory=list)  # 作业题目文件路径
    marking_files: List[str] = field(default_factory=list)   # 批改标准文件路径
    grading_config_id: Optional[str] = None  # 关联的批改配置ID
    auto_grading_enabled: bool = True        # 是否启用自动批改
    grading_template_id: Optional[str] = None  # 批改模板ID
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    # 统计信息
    submission_count: int = 0
    graded_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'class_id': self.class_id,
            'title': self.title,
            'description': self.description,
            'question_files': self.question_files,
            'marking_files': self.marking_files,
            'grading_config_id': self.grading_config_id,
            'auto_grading_enabled': self.auto_grading_enabled,
            'grading_template_id': self.grading_template_id,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
            'submission_count': self.submission_count,
            'graded_count': self.graded_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Assignment':
        """从字典创建"""
        return cls(
            id=data.get('id'),
            class_id=data.get('class_id', 0),
            title=data.get('title', ''),
            description=data.get('description', ''),
            question_files=data.get('question_files', []),
            marking_files=data.get('marking_files', []),
            grading_config_id=data.get('grading_config_id'),
            auto_grading_enabled=data.get('auto_grading_enabled', True),
            grading_template_id=data.get('grading_template_id'),
            deadline=datetime.fromisoformat(data['deadline']) if data.get('deadline') else None,
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            is_active=data.get('is_active', True),
            submission_count=data.get('submission_count', 0),
            graded_count=data.get('graded_count', 0)
        )
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Assignment':
        """从数据库行创建"""
        return cls(
            id=row.get('id'),
            class_id=row.get('class_id', 0),
            title=row.get('title', ''),
            description=row.get('description', ''),
            question_files=json.loads(row.get('question_files', '[]')),
            marking_files=json.loads(row.get('marking_files', '[]')),
            grading_config_id=row.get('grading_config_id'),
            auto_grading_enabled=bool(row.get('auto_grading_enabled', 1)),
            grading_template_id=row.get('grading_template_id'),
            deadline=datetime.fromisoformat(row['deadline']) if row.get('deadline') else None,
            created_at=datetime.fromisoformat(row.get('created_at', datetime.now().isoformat())),
            is_active=bool(row.get('is_active', 1)),
            submission_count=row.get('submission_count', 0),
            graded_count=row.get('graded_count', 0)
        )
    
    def validate(self) -> List[str]:
        """验证作业数据"""
        errors = []
        
        if not self.title.strip():
            errors.append("作业标题不能为空")
        
        if self.class_id <= 0:
            errors.append("班级ID必须大于0")
        
        if self.deadline and self.deadline <= datetime.now():
            errors.append("截止时间必须在当前时间之后")
        
        # 验证文件路径格式
        for file_path in self.question_files:
            if not isinstance(file_path, str) or not file_path.strip():
                errors.append("题目文件路径格式无效")
                break
        
        for file_path in self.marking_files:
            if not isinstance(file_path, str) or not file_path.strip():
                errors.append("批改标准文件路径格式无效")
                break
        
        return errors
    
    def is_overdue(self) -> bool:
        """检查作业是否已过期"""
        if not self.deadline:
            return False
        return datetime.now() > self.deadline
    
    def get_completion_rate(self) -> float:
        """获取完成率"""
        if self.submission_count == 0:
            return 0.0
        return (self.graded_count / self.submission_count) * 100
    
    def get_grading_progress(self) -> Dict[str, Any]:
        """获取批改进度信息"""
        return {
            'total_submissions': self.submission_count,
            'graded_submissions': self.graded_count,
            'pending_submissions': self.submission_count - self.graded_count,
            'completion_rate': self.get_completion_rate(),
            'is_complete': self.graded_count == self.submission_count and self.submission_count > 0
        }
    
    def update_statistics(self, submission_count: int, graded_count: int):
        """更新统计信息"""
        self.submission_count = max(0, submission_count)
        self.graded_count = max(0, min(graded_count, submission_count))
    
    def has_grading_config(self) -> bool:
        """检查是否有批改配置"""
        return self.grading_config_id is not None or self.grading_template_id is not None
    
    def can_auto_grade(self) -> bool:
        """检查是否可以自动批改"""
        return self.auto_grading_enabled and self.has_grading_config()
    
    def get_file_count(self) -> Dict[str, int]:
        """获取文件数量统计"""
        return {
            'question_files': len(self.question_files),
            'marking_files': len(self.marking_files),
            'total_files': len(self.question_files) + len(self.marking_files)
        }
    
    def add_question_file(self, file_path: str) -> bool:
        """添加题目文件"""
        if file_path and file_path not in self.question_files:
            self.question_files.append(file_path)
            return True
        return False
    
    def add_marking_file(self, file_path: str) -> bool:
        """添加批改标准文件"""
        if file_path and file_path not in self.marking_files:
            self.marking_files.append(file_path)
            return True
        return False
    
    def remove_question_file(self, file_path: str) -> bool:
        """移除题目文件"""
        if file_path in self.question_files:
            self.question_files.remove(file_path)
            return True
        return False
    
    def remove_marking_file(self, file_path: str) -> bool:
        """移除批改标准文件"""
        if file_path in self.marking_files:
            self.marking_files.remove(file_path)
            return True
        return False