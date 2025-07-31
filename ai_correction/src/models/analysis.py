#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析相关数据模型
用于详细分析功能的数据结构定义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import uuid
from datetime import datetime


class AnalysisType(Enum):
    """分析类型"""
    INDIVIDUAL = "individual"  # 个人分析
    COMPARISON = "comparison"  # 对比分析
    CLASS_OVERVIEW = "class_overview"  # 班级概览
    TREND = "trend"  # 趋势分析


@dataclass
class ScoreBreakdown:
    """得分细分"""
    criterion_id: str
    criterion_name: str
    score: float
    max_score: float
    percentage: float
    feedback: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'criterion_id': self.criterion_id,
            'criterion_name': self.criterion_name,
            'score': self.score,
            'max_score': self.max_score,
            'percentage': self.percentage,
            'feedback': self.feedback,
            'strengths': self.strengths,
            'weaknesses': self.weaknesses
        }


@dataclass
class ImprovementSuggestion:
    """改进建议"""
    category: str  # 改进类别
    priority: str  # 优先级: high, medium, low
    suggestion: str  # 具体建议
    examples: List[str] = field(default_factory=list)  # 示例
    resources: List[str] = field(default_factory=list)  # 相关资源
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'category': self.category,
            'priority': self.priority,
            'suggestion': self.suggestion,
            'examples': self.examples,
            'resources': self.resources
        }


@dataclass
class StudentResult:
    """学生结果详情"""
    student_id: str
    student_name: str
    assignment_id: str
    assignment_title: str
    total_score: float
    max_score: float
    percentage: float
    rank: int
    class_size: int
    score_breakdown: List[ScoreBreakdown] = field(default_factory=list)
    improvement_suggestions: List[ImprovementSuggestion] = field(default_factory=list)
    overall_feedback: str = ""
    submission_time: Optional[datetime] = None
    grading_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'student_id': self.student_id,
            'student_name': self.student_name,
            'assignment_id': self.assignment_id,
            'assignment_title': self.assignment_title,
            'total_score': self.total_score,
            'max_score': self.max_score,
            'percentage': self.percentage,
            'rank': self.rank,
            'class_size': self.class_size,
            'score_breakdown': [sb.to_dict() for sb in self.score_breakdown],
            'improvement_suggestions': [imp.to_dict() for imp in self.improvement_suggestions],
            'overall_feedback': self.overall_feedback,
            'submission_time': self.submission_time.isoformat() if self.submission_time else None,
            'grading_time': self.grading_time.isoformat() if self.grading_time else None
        }


@dataclass
class ClassStatistics:
    """班级统计信息"""
    class_id: str
    class_name: str
    assignment_id: str
    assignment_title: str
    total_students: int
    submitted_count: int
    graded_count: int
    average_score: float
    median_score: float
    highest_score: float
    lowest_score: float
    standard_deviation: float
    score_distribution: Dict[str, int] = field(default_factory=dict)  # 分数段分布
    common_strengths: List[str] = field(default_factory=list)
    common_weaknesses: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'class_id': self.class_id,
            'class_name': self.class_name,
            'assignment_id': self.assignment_id,
            'assignment_title': self.assignment_title,
            'total_students': self.total_students,
            'submitted_count': self.submitted_count,
            'graded_count': self.graded_count,
            'average_score': self.average_score,
            'median_score': self.median_score,
            'highest_score': self.highest_score,
            'lowest_score': self.lowest_score,
            'standard_deviation': self.standard_deviation,
            'score_distribution': self.score_distribution,
            'common_strengths': self.common_strengths,
            'common_weaknesses': self.common_weaknesses
        }


@dataclass
class ComparisonData:
    """对比数据"""
    student_results: List[StudentResult]
    comparison_metrics: Dict[str, List[float]] = field(default_factory=dict)
    relative_performance: Dict[str, str] = field(default_factory=dict)  # 相对表现描述
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'student_results': [sr.to_dict() for sr in self.student_results],
            'comparison_metrics': self.comparison_metrics,
            'relative_performance': self.relative_performance
        }


@dataclass
class TrendPoint:
    """趋势数据点"""
    date: datetime
    assignment_id: str
    assignment_title: str
    score: float
    percentage: float
    rank: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'date': self.date.isoformat(),
            'assignment_id': self.assignment_id,
            'assignment_title': self.assignment_title,
            'score': self.score,
            'percentage': self.percentage,
            'rank': self.rank
        }


@dataclass
class TrendAnalysis:
    """趋势分析"""
    student_id: str
    student_name: str
    trend_points: List[TrendPoint] = field(default_factory=list)
    overall_trend: str = ""  # improving, declining, stable
    trend_description: str = ""
    performance_insights: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'student_id': self.student_id,
            'student_name': self.student_name,
            'trend_points': [tp.to_dict() for tp in self.trend_points],
            'overall_trend': self.overall_trend,
            'trend_description': self.trend_description,
            'performance_insights': self.performance_insights
        }


@dataclass
class WeaknessArea:
    """薄弱知识点"""
    area_name: str
    description: str
    affected_students: List[str]  # 学生ID列表
    average_score: float
    improvement_rate: float  # 改进空间百分比
    recommended_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'area_name': self.area_name,
            'description': self.description,
            'affected_students': self.affected_students,
            'average_score': self.average_score,
            'improvement_rate': self.improvement_rate,
            'recommended_actions': self.recommended_actions
        }


@dataclass
class DetailedAnalysis:
    """详细分析结果"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    analysis_type: AnalysisType = AnalysisType.INDIVIDUAL
    student_result: Optional[StudentResult] = None
    class_statistics: Optional[ClassStatistics] = None
    comparison_data: Optional[ComparisonData] = None
    trend_analysis: Optional[TrendAnalysis] = None
    weakness_areas: List[WeaknessArea] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'analysis_type': self.analysis_type.value,
            'student_result': self.student_result.to_dict() if self.student_result else None,
            'class_statistics': self.class_statistics.to_dict() if self.class_statistics else None,
            'comparison_data': self.comparison_data.to_dict() if self.comparison_data else None,
            'trend_analysis': self.trend_analysis.to_dict() if self.trend_analysis else None,
            'weakness_areas': [wa.to_dict() for wa in self.weakness_areas],
            'generated_at': self.generated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DetailedAnalysis':
        """从字典创建详细分析对象"""
        analysis = cls(
            id=data.get('id', str(uuid.uuid4())),
            analysis_type=AnalysisType(data.get('analysis_type', 'individual')),
            generated_at=datetime.fromisoformat(data.get('generated_at', datetime.now().isoformat()))
        )
        
        # 处理学生结果
        if data.get('student_result'):
            sr_data = data['student_result']
            analysis.student_result = StudentResult(
                student_id=sr_data['student_id'],
                student_name=sr_data['student_name'],
                assignment_id=sr_data['assignment_id'],
                assignment_title=sr_data['assignment_title'],
                total_score=sr_data['total_score'],
                max_score=sr_data['max_score'],
                percentage=sr_data['percentage'],
                rank=sr_data['rank'],
                class_size=sr_data['class_size'],
                overall_feedback=sr_data.get('overall_feedback', ''),
                submission_time=datetime.fromisoformat(sr_data['submission_time']) if sr_data.get('submission_time') else None,
                grading_time=datetime.fromisoformat(sr_data['grading_time']) if sr_data.get('grading_time') else None
            )
            
            # 处理得分细分
            for sb_data in sr_data.get('score_breakdown', []):
                score_breakdown = ScoreBreakdown(
                    criterion_id=sb_data['criterion_id'],
                    criterion_name=sb_data['criterion_name'],
                    score=sb_data['score'],
                    max_score=sb_data['max_score'],
                    percentage=sb_data['percentage'],
                    feedback=sb_data.get('feedback', ''),
                    strengths=sb_data.get('strengths', []),
                    weaknesses=sb_data.get('weaknesses', [])
                )
                analysis.student_result.score_breakdown.append(score_breakdown)
            
            # 处理改进建议
            for imp_data in sr_data.get('improvement_suggestions', []):
                improvement = ImprovementSuggestion(
                    category=imp_data['category'],
                    priority=imp_data['priority'],
                    suggestion=imp_data['suggestion'],
                    examples=imp_data.get('examples', []),
                    resources=imp_data.get('resources', [])
                )
                analysis.student_result.improvement_suggestions.append(improvement)
        
        return analysis