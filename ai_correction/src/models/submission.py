#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提交相关数据模型
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json


class SubmissionStatus(Enum):
    """提交状态"""
    SUBMITTED = "submitted"           # 已提交
    AI_GRADED = "ai_graded"          # AI已批改
    TEACHER_REVIEWED = "teacher_reviewed"  # 教师已审核
    RETURNED = "returned"            # 已返回
    PENDING_REVIEW = "pending_review"  # 待审核
    FAILED = "failed"                # 批改失败


@dataclass
class SubmissionGradingDetails:
    """提交批改详情"""
    ai_score: Optional[float] = None
    ai_feedback: Optional[str] = None
    teacher_score: Optional[float] = None
    teacher_feedback: Optional[str] = None
    grading_criteria_scores: Dict[str, float] = field(default_factory=dict)
    improvement_suggestions: List[str] = field(default_factory=list)
    grading_timestamp: Optional[datetime] = None
    review_timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'ai_score': self.ai_score,
            'ai_feedback': self.ai_feedback,
            'teacher_score': self.teacher_score,
            'teacher_feedback': self.teacher_feedback,
            'grading_criteria_scores': self.grading_criteria_scores,
            'improvement_suggestions': self.improvement_suggestions,
            'grading_timestamp': self.grading_timestamp.isoformat() if self.grading_timestamp else None,
            'review_timestamp': self.review_timestamp.isoformat() if self.review_timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubmissionGradingDetails':
        """从字典创建"""
        return cls(
            ai_score=data.get('ai_score'),
            ai_feedback=data.get('ai_feedback'),
            teacher_score=data.get('teacher_score'),
            teacher_feedback=data.get('teacher_feedback'),
            grading_criteria_scores=data.get('grading_criteria_scores', {}),
            improvement_suggestions=data.get('improvement_suggestions', []),
            grading_timestamp=datetime.fromisoformat(data['grading_timestamp']) if data.get('grading_timestamp') else None,
            review_timestamp=datetime.fromisoformat(data['review_timestamp']) if data.get('review_timestamp') else None
        )


@dataclass
class Submission:
    """提交数据模型"""
    id: Optional[int] = None
    assignment_id: int = 0
    student_username: str = ""
    answer_files: List[str] = field(default_factory=list)  # 学生答案文件路径
    ai_result: Optional[str] = None       # AI批改原始结果
    teacher_feedback: Optional[str] = None  # 教师修改后的反馈
    status: SubmissionStatus = SubmissionStatus.SUBMITTED
    score: Optional[float] = None         # 最终得分
    task_id: Optional[str] = None         # 关联的批改任务ID
    grading_details: Optional[SubmissionGradingDetails] = None  # 详细批改信息
    ai_confidence: Optional[float] = None  # AI批改置信度
    manual_review_required: bool = False   # 是否需要人工审核
    submitted_at: datetime = field(default_factory=datetime.now)
    graded_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    
    # 为了向后兼容，保留files字段映射
    @property
    def files(self) -> List[str]:
        """向后兼容的files属性"""
        return self.answer_files
    
    @files.setter
    def files(self, value: List[str]):
        """向后兼容的files属性设置"""
        self.answer_files = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'assignment_id': self.assignment_id,
            'student_username': self.student_username,
            'answer_files': self.answer_files,
            'files': self.answer_files,  # 向后兼容
            'ai_result': self.ai_result,
            'teacher_feedback': self.teacher_feedback,
            'status': self.status.value,
            'score': self.score,
            'task_id': self.task_id,
            'grading_details': self.grading_details.to_dict() if self.grading_details else None,
            'ai_confidence': self.ai_confidence,
            'manual_review_required': self.manual_review_required,
            'submitted_at': self.submitted_at.isoformat(),
            'graded_at': self.graded_at.isoformat() if self.graded_at else None,
            'returned_at': self.returned_at.isoformat() if self.returned_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Submission':
        """从字典创建"""
        grading_details = None
        if data.get('grading_details'):
            grading_details = SubmissionGradingDetails.from_dict(data['grading_details'])
        
        return cls(
            id=data.get('id'),
            assignment_id=data.get('assignment_id', 0),
            student_username=data.get('student_username', ''),
            answer_files=data.get('answer_files', data.get('files', [])),  # 向后兼容
            ai_result=data.get('ai_result'),
            teacher_feedback=data.get('teacher_feedback'),
            status=SubmissionStatus(data.get('status', 'submitted')),
            score=data.get('score'),
            task_id=data.get('task_id'),
            grading_details=grading_details,
            ai_confidence=data.get('ai_confidence'),
            manual_review_required=data.get('manual_review_required', False),
            submitted_at=datetime.fromisoformat(data.get('submitted_at', datetime.now().isoformat())),
            graded_at=datetime.fromisoformat(data['graded_at']) if data.get('graded_at') else None,
            returned_at=datetime.fromisoformat(data['returned_at']) if data.get('returned_at') else None
        )
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Submission':
        """从数据库行创建"""
        grading_details = None
        if row.get('grading_details'):
            try:
                details_data = json.loads(row['grading_details'])
                grading_details = SubmissionGradingDetails.from_dict(details_data)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return cls(
            id=row.get('id'),
            assignment_id=row.get('assignment_id', 0),
            student_username=row.get('student_username', ''),
            answer_files=json.loads(row.get('answer_files', '[]')),
            ai_result=row.get('ai_result'),
            teacher_feedback=row.get('teacher_feedback'),
            status=SubmissionStatus(row.get('status', 'submitted')),
            score=row.get('score'),
            task_id=row.get('task_id'),
            grading_details=grading_details,
            ai_confidence=row.get('ai_confidence'),
            manual_review_required=bool(row.get('manual_review_required', 0)),
            submitted_at=datetime.fromisoformat(row.get('submitted_at', datetime.now().isoformat())),
            graded_at=datetime.fromisoformat(row['graded_at']) if row.get('graded_at') else None,
            returned_at=datetime.fromisoformat(row['returned_at']) if row.get('returned_at') else None
        )
    
    def validate(self) -> List[str]:
        """验证提交数据"""
        errors = []
        
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
        
        # 验证分数范围
        if self.score is not None and (self.score < 0 or self.score > 100):
            errors.append("分数必须在0-100之间")
        
        # 验证AI置信度范围
        if self.ai_confidence is not None and (self.ai_confidence < 0 or self.ai_confidence > 1):
            errors.append("AI置信度必须在0-1之间")
        
        return errors
    
    def transition_to(self, new_status: SubmissionStatus) -> bool:
        """状态转换"""
        valid_transitions = {
            SubmissionStatus.SUBMITTED: [SubmissionStatus.AI_GRADED, SubmissionStatus.TEACHER_REVIEWED, SubmissionStatus.FAILED],
            SubmissionStatus.AI_GRADED: [SubmissionStatus.TEACHER_REVIEWED, SubmissionStatus.RETURNED, SubmissionStatus.PENDING_REVIEW],
            SubmissionStatus.TEACHER_REVIEWED: [SubmissionStatus.RETURNED],
            SubmissionStatus.PENDING_REVIEW: [SubmissionStatus.TEACHER_REVIEWED, SubmissionStatus.RETURNED],
            SubmissionStatus.RETURNED: [],  # 终态
            SubmissionStatus.FAILED: [SubmissionStatus.SUBMITTED]  # 可以重新提交
        }
        
        if new_status in valid_transitions.get(self.status, []):
            self.status = new_status
            
            # 更新相关时间戳
            if new_status == SubmissionStatus.AI_GRADED:
                self.graded_at = datetime.now()
            elif new_status == SubmissionStatus.RETURNED:
                self.returned_at = datetime.now()
            
            return True
        
        return False
    
    def is_graded(self) -> bool:
        """检查是否已批改"""
        return self.status in [SubmissionStatus.AI_GRADED, SubmissionStatus.TEACHER_REVIEWED, SubmissionStatus.RETURNED]
    
    def is_completed(self) -> bool:
        """检查是否已完成"""
        return self.status == SubmissionStatus.RETURNED
    
    def needs_review(self) -> bool:
        """检查是否需要审核"""
        return self.manual_review_required or self.status == SubmissionStatus.PENDING_REVIEW
    
    def get_final_score(self) -> Optional[float]:
        """获取最终分数"""
        if self.grading_details and self.grading_details.teacher_score is not None:
            return self.grading_details.teacher_score
        elif self.grading_details and self.grading_details.ai_score is not None:
            return self.grading_details.ai_score
        return self.score
    
    def get_final_feedback(self) -> Optional[str]:
        """获取最终反馈"""
        if self.grading_details and self.grading_details.teacher_feedback:
            return self.grading_details.teacher_feedback
        elif self.grading_details and self.grading_details.ai_feedback:
            return self.grading_details.ai_feedback
        return self.teacher_feedback or self.ai_result
    
    def set_ai_grading_result(self, score: float, feedback: str, confidence: float = None, 
                             criteria_scores: Dict[str, float] = None, 
                             suggestions: List[str] = None):
        """设置AI批改结果"""
        if not self.grading_details:
            self.grading_details = SubmissionGradingDetails()
        
        self.grading_details.ai_score = score
        self.grading_details.ai_feedback = feedback
        self.grading_details.grading_timestamp = datetime.now()
        
        if criteria_scores:
            self.grading_details.grading_criteria_scores = criteria_scores
        
        if suggestions:
            self.grading_details.improvement_suggestions = suggestions
        
        if confidence is not None:
            self.ai_confidence = confidence
        
        # 更新兼容字段
        self.score = score
        self.ai_result = feedback
        
        # 根据置信度决定是否需要人工审核
        if confidence is not None and confidence < 0.7:
            self.manual_review_required = True
        
        self.transition_to(SubmissionStatus.AI_GRADED)
    
    def set_teacher_review(self, score: Optional[float] = None, feedback: Optional[str] = None):
        """设置教师审核结果"""
        if not self.grading_details:
            self.grading_details = SubmissionGradingDetails()
        
        if score is not None:
            self.grading_details.teacher_score = score
            self.score = score  # 更新兼容字段
        
        if feedback is not None:
            self.grading_details.teacher_feedback = feedback
            self.teacher_feedback = feedback  # 更新兼容字段
        
        self.grading_details.review_timestamp = datetime.now()
        self.manual_review_required = False
        
        self.transition_to(SubmissionStatus.TEACHER_REVIEWED)
    
    def get_processing_time(self) -> Optional[float]:
        """获取处理时间（小时）"""
        if not self.graded_at:
            return None
        
        time_diff = self.graded_at - self.submitted_at
        return time_diff.total_seconds() / 3600
    
    def get_file_count(self) -> int:
        """获取文件数量"""
        return len(self.answer_files)
    
    def add_answer_file(self, file_path: str) -> bool:
        """添加答案文件"""
        if file_path and file_path not in self.answer_files:
            self.answer_files.append(file_path)
            return True
        return False
    
    def remove_answer_file(self, file_path: str) -> bool:
        """移除答案文件"""
        if file_path in self.answer_files:
            self.answer_files.remove(file_path)
            return True
        return False
    
    def get_status_display(self) -> str:
        """获取状态显示文本"""
        status_map = {
            SubmissionStatus.SUBMITTED: "已提交",
            SubmissionStatus.AI_GRADED: "AI已批改",
            SubmissionStatus.TEACHER_REVIEWED: "教师已审核",
            SubmissionStatus.RETURNED: "已返回",
            SubmissionStatus.PENDING_REVIEW: "待审核",
            SubmissionStatus.FAILED: "批改失败"
        }
        return status_map.get(self.status, "未知状态")