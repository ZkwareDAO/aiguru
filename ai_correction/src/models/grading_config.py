#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批改配置相关数据模型
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import uuid
from datetime import datetime


class SubjectType(Enum):
    """学科类型"""
    CHINESE = "chinese"
    MATH = "math"
    ENGLISH = "english"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    HISTORY = "history"
    GEOGRAPHY = "geography"
    POLITICS = "politics"
    OTHER = "other"


class GradeLevel(Enum):
    """年级水平"""
    PRIMARY_1_3 = "primary_1_3"  # 小学1-3年级
    PRIMARY_4_6 = "primary_4_6"  # 小学4-6年级
    MIDDLE_7_9 = "middle_7_9"    # 初中7-9年级
    HIGH_10_12 = "high_10_12"    # 高中10-12年级
    UNIVERSITY = "university"     # 大学
    OTHER = "other"


@dataclass
class ScoringRule:
    """评分规则"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    max_score: float = 0.0
    criteria: List[str] = field(default_factory=list)
    auto_grading: bool = True
    weight: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'max_score': self.max_score,
            'criteria': self.criteria,
            'auto_grading': self.auto_grading,
            'weight': self.weight
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScoringRule':
        """从字典创建"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            description=data.get('description', ''),
            max_score=data.get('max_score', 0.0),
            criteria=data.get('criteria', []),
            auto_grading=data.get('auto_grading', True),
            weight=data.get('weight', 1.0)
        )


@dataclass
class WeightConfig:
    """权重配置"""
    content_accuracy: float = 0.4  # 内容准确性
    language_quality: float = 0.3  # 语言质量
    structure_logic: float = 0.2   # 结构逻辑
    creativity: float = 0.1        # 创新性
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'content_accuracy': self.content_accuracy,
            'language_quality': self.language_quality,
            'structure_logic': self.structure_logic,
            'creativity': self.creativity
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WeightConfig':
        """从字典创建"""
        return cls(
            content_accuracy=data.get('content_accuracy', 0.4),
            language_quality=data.get('language_quality', 0.3),
            structure_logic=data.get('structure_logic', 0.2),
            creativity=data.get('creativity', 0.1)
        )
    
    def normalize(self):
        """归一化权重，确保总和为1"""
        total = self.content_accuracy + self.language_quality + self.structure_logic + self.creativity
        if total > 0:
            self.content_accuracy /= total
            self.language_quality /= total
            self.structure_logic /= total
            self.creativity /= total


@dataclass
class GradingConfig:
    """批改配置"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    subject: SubjectType = SubjectType.OTHER
    grade_level: GradeLevel = GradeLevel.OTHER
    scoring_rules: List[ScoringRule] = field(default_factory=list)
    weight_distribution: WeightConfig = field(default_factory=WeightConfig)
    custom_prompts: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_template: bool = False
    created_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'subject': self.subject.value,
            'grade_level': self.grade_level.value,
            'scoring_rules': [rule.to_dict() for rule in self.scoring_rules],
            'weight_distribution': self.weight_distribution.to_dict(),
            'custom_prompts': self.custom_prompts,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_template': self.is_template,
            'created_by': self.created_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GradingConfig':
        """从字典创建"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            subject=SubjectType(data.get('subject', 'other')),
            grade_level=GradeLevel(data.get('grade_level', 'other')),
            scoring_rules=[ScoringRule.from_dict(rule) for rule in data.get('scoring_rules', [])],
            weight_distribution=WeightConfig.from_dict(data.get('weight_distribution', {})),
            custom_prompts=data.get('custom_prompts', []),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat())),
            is_template=data.get('is_template', False),
            created_by=data.get('created_by')
        )
    
    def get_total_score(self) -> float:
        """获取总分"""
        return sum(rule.max_score for rule in self.scoring_rules)
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if not self.name.strip():
            errors.append("配置名称不能为空")
        
        if not self.scoring_rules:
            errors.append("至少需要一个评分规则")
        
        for rule in self.scoring_rules:
            if not rule.name.strip():
                errors.append(f"评分规则名称不能为空")
            if rule.max_score <= 0:
                errors.append(f"评分规则 '{rule.name}' 的最大分数必须大于0")
        
        # 验证权重总和
        weight_sum = (self.weight_distribution.content_accuracy + 
                     self.weight_distribution.language_quality + 
                     self.weight_distribution.structure_logic + 
                     self.weight_distribution.creativity)
        
        if abs(weight_sum - 1.0) > 0.01:
            errors.append("权重分配总和必须等于1.0")
        
        return errors


@dataclass
class GradingTemplate:
    """批改模板"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    subject: SubjectType = SubjectType.OTHER
    grade_level: GradeLevel = GradeLevel.OTHER
    config: GradingConfig = field(default_factory=GradingConfig)
    usage_count: int = 0
    is_public: bool = False
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'subject': self.subject.value,
            'grade_level': self.grade_level.value,
            'config': self.config.to_dict(),
            'usage_count': self.usage_count,
            'is_public': self.is_public,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GradingTemplate':
        """从字典创建"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            description=data.get('description', ''),
            subject=SubjectType(data.get('subject', 'other')),
            grade_level=GradeLevel(data.get('grade_level', 'other')),
            config=GradingConfig.from_dict(data.get('config', {})),
            usage_count=data.get('usage_count', 0),
            is_public=data.get('is_public', False),
            created_by=data.get('created_by'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        )


# 预设模板数据
DEFAULT_TEMPLATES = [
    GradingTemplate(
        name="语文作文批改",
        description="适用于语文作文的综合评分模板",
        subject=SubjectType.CHINESE,
        grade_level=GradeLevel.MIDDLE_7_9,
        config=GradingConfig(
            name="语文作文批改",
            subject=SubjectType.CHINESE,
            grade_level=GradeLevel.MIDDLE_7_9,
            scoring_rules=[
                ScoringRule(
                    name="内容与思想",
                    description="文章内容的深度和思想性",
                    max_score=25.0,
                    criteria=["主题明确", "内容充实", "思想深刻", "观点正确"],
                    weight=0.4
                ),
                ScoringRule(
                    name="语言表达",
                    description="语言运用的准确性和流畅性",
                    max_score=25.0,
                    criteria=["语言准确", "表达流畅", "词汇丰富", "句式多样"],
                    weight=0.3
                ),
                ScoringRule(
                    name="结构层次",
                    description="文章结构的合理性和层次性",
                    max_score=20.0,
                    criteria=["结构完整", "层次清晰", "过渡自然", "首尾呼应"],
                    weight=0.2
                ),
                ScoringRule(
                    name="创新亮点",
                    description="文章的创新性和亮点",
                    max_score=10.0,
                    criteria=["立意新颖", "表达独特", "见解深刻", "文采飞扬"],
                    weight=0.1
                )
            ],
            weight_distribution=WeightConfig(0.4, 0.3, 0.2, 0.1),
            custom_prompts=[
                "请重点关注文章的主题表达和思想深度",
                "注意语言表达的准确性和流畅性",
                "评价文章结构的合理性"
            ]
        ),
        is_public=True
    ),
    GradingTemplate(
        name="数学解答题批改",
        description="适用于数学解答题的步骤化评分模板",
        subject=SubjectType.MATH,
        grade_level=GradeLevel.HIGH_10_12,
        config=GradingConfig(
            name="数学解答题批改",
            subject=SubjectType.MATH,
            grade_level=GradeLevel.HIGH_10_12,
            scoring_rules=[
                ScoringRule(
                    name="解题思路",
                    description="解题方法和思路的正确性",
                    max_score=30.0,
                    criteria=["方法正确", "思路清晰", "步骤合理", "逻辑严密"],
                    weight=0.5
                ),
                ScoringRule(
                    name="计算过程",
                    description="计算步骤的准确性和完整性",
                    max_score=40.0,
                    criteria=["计算准确", "步骤完整", "过程清晰", "格式规范"],
                    weight=0.4
                ),
                ScoringRule(
                    name="最终答案",
                    description="最终答案的正确性",
                    max_score=30.0,
                    criteria=["答案正确", "单位准确", "格式规范", "结论明确"],
                    weight=0.3
                )
            ],
            weight_distribution=WeightConfig(0.5, 0.4, 0.1, 0.0),
            custom_prompts=[
                "重点检查解题方法是否正确",
                "仔细核对计算过程中的每一步",
                "确认最终答案的准确性"
            ]
        ),
        is_public=True
    ),
    GradingTemplate(
        name="英语作文批改",
        description="适用于英语作文的综合评分模板",
        subject=SubjectType.ENGLISH,
        grade_level=GradeLevel.HIGH_10_12,
        config=GradingConfig(
            name="英语作文批改",
            subject=SubjectType.ENGLISH,
            grade_level=GradeLevel.HIGH_10_12,
            scoring_rules=[
                ScoringRule(
                    name="内容要点",
                    description="内容的完整性和相关性",
                    max_score=25.0,
                    criteria=["要点完整", "内容相关", "论述充分", "例证恰当"],
                    weight=0.35
                ),
                ScoringRule(
                    name="语言运用",
                    description="语法、词汇和句式的运用",
                    max_score=25.0,
                    criteria=["语法正确", "词汇丰富", "句式多样", "表达地道"],
                    weight=0.35
                ),
                ScoringRule(
                    name="篇章结构",
                    description="文章结构和逻辑组织",
                    max_score=20.0,
                    criteria=["结构清晰", "逻辑连贯", "过渡自然", "段落合理"],
                    weight=0.2
                ),
                ScoringRule(
                    name="书写规范",
                    description="拼写、标点和书写质量",
                    max_score=10.0,
                    criteria=["拼写正确", "标点准确", "书写清晰", "格式规范"],
                    weight=0.1
                )
            ],
            weight_distribution=WeightConfig(0.35, 0.35, 0.2, 0.1),
            custom_prompts=[
                "检查内容是否涵盖所有要点",
                "评估语言运用的准确性和丰富性",
                "关注文章的整体结构和逻辑"
            ]
        ),
        is_public=True
    )
]