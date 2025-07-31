"""
质量控制相关数据模型

定义质量规则、质量报告和质量问题的数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
import json


class QualityRuleType(Enum):
    """质量规则类型枚举"""
    SCORE_RANGE = "score_range"           # 分数范围检查
    FORMAT_CHECK = "format_check"         # 格式检查
    LOGIC_CHECK = "logic_check"           # 逻辑检查
    CONSISTENCY = "consistency"           # 一致性检查
    COMPLETENESS = "completeness"         # 完整性检查
    RELEVANCE = "relevance"              # 相关性检查
    ACCURACY = "accuracy"                # 准确性检查
    CUSTOM = "custom"                    # 自定义规则


class QualitySeverity(Enum):
    """质量问题严重程度枚举"""
    LOW = "low"           # 低
    MEDIUM = "medium"     # 中
    HIGH = "high"         # 高
    CRITICAL = "critical" # 严重


class QualityMetricType(Enum):
    """质量指标类型枚举"""
    ACCURACY = "accuracy"         # 准确性
    CONSISTENCY = "consistency"   # 一致性
    COMPLETENESS = "completeness" # 完整性
    RELEVANCE = "relevance"       # 相关性
    EFFICIENCY = "efficiency"     # 效率
    RELIABILITY = "reliability"   # 可靠性


@dataclass
class QualityRule:
    """质量规则"""
    id: str
    name: str
    description: str
    rule_type: QualityRuleType
    parameters: Dict[str, Any] = field(default_factory=dict)
    severity: QualitySeverity = QualitySeverity.MEDIUM
    is_active: bool = True
    weight: float = 1.0  # 规则权重
    threshold: float = 0.8  # 阈值
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    
    def evaluate(self, data: Dict[str, Any]) -> 'QualityEvaluation':
        """评估数据质量"""
        try:
            if self.rule_type == QualityRuleType.SCORE_RANGE:
                return self._evaluate_score_range(data)
            elif self.rule_type == QualityRuleType.FORMAT_CHECK:
                return self._evaluate_format(data)
            elif self.rule_type == QualityRuleType.LOGIC_CHECK:
                return self._evaluate_logic(data)
            elif self.rule_type == QualityRuleType.CONSISTENCY:
                return self._evaluate_consistency(data)
            elif self.rule_type == QualityRuleType.COMPLETENESS:
                return self._evaluate_completeness(data)
            elif self.rule_type == QualityRuleType.RELEVANCE:
                return self._evaluate_relevance(data)
            elif self.rule_type == QualityRuleType.ACCURACY:
                return self._evaluate_accuracy(data)
            else:
                return self._evaluate_custom(data)
        except Exception as e:
            return QualityEvaluation(
                rule_id=self.id,
                passed=False,
                score=0.0,
                message=f"评估失败: {str(e)}",
                details={"error": str(e)}
            )
    
    def _evaluate_score_range(self, data: Dict[str, Any]) -> 'QualityEvaluation':
        """评估分数范围"""
        score = data.get("score", 0)
        min_score = self.parameters.get("min_score", 0)
        max_score = self.parameters.get("max_score", 100)
        
        passed = min_score <= score <= max_score
        evaluation_score = 1.0 if passed else 0.0
        
        return QualityEvaluation(
            rule_id=self.id,
            passed=passed,
            score=evaluation_score,
            message=f"分数 {score} {'在' if passed else '不在'}允许范围 [{min_score}, {max_score}] 内",
            details={"actual_score": score, "min_score": min_score, "max_score": max_score}
        )
    
    def _evaluate_format(self, data: Dict[str, Any]) -> 'QualityEvaluation':
        """评估格式"""
        content = data.get("content", "")
        required_fields = self.parameters.get("required_fields", [])
        
        missing_fields = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        passed = len(missing_fields) == 0
        score = 1.0 - (len(missing_fields) / len(required_fields)) if required_fields else 1.0
        
        return QualityEvaluation(
            rule_id=self.id,
            passed=passed,
            score=score,
            message=f"格式检查{'通过' if passed else '失败'}",
            details={"missing_fields": missing_fields, "required_fields": required_fields}
        )
    
    def _evaluate_logic(self, data: Dict[str, Any]) -> 'QualityEvaluation':
        """评估逻辑"""
        # 简化的逻辑检查实现
        score = data.get("score", 0)
        feedback = data.get("feedback", "")
        
        # 检查分数和反馈的逻辑一致性
        if score == 0 and "优秀" in feedback:
            passed = False
            message = "分数为0但反馈为正面，逻辑不一致"
        elif score >= 90 and any(word in feedback for word in ["差", "错误", "不好"]):
            passed = False
            message = "高分但反馈为负面，逻辑不一致"
        else:
            passed = True
            message = "逻辑检查通过"
        
        return QualityEvaluation(
            rule_id=self.id,
            passed=passed,
            score=1.0 if passed else 0.0,
            message=message,
            details={"score": score, "feedback": feedback}
        )
    
    def _evaluate_consistency(self, data: Dict[str, Any]) -> 'QualityEvaluation':
        """评估一致性"""
        # 简化的一致性检查实现
        current_result = data.get("current_result", {})
        historical_results = data.get("historical_results", [])
        
        if not historical_results:
            return QualityEvaluation(
                rule_id=self.id,
                passed=True,
                score=1.0,
                message="无历史数据，跳过一致性检查",
                details={}
            )
        
        # 计算与历史结果的相似度
        similarities = []
        for hist_result in historical_results:
            similarity = self._calculate_similarity(current_result, hist_result)
            similarities.append(similarity)
        
        avg_similarity = sum(similarities) / len(similarities)
        passed = avg_similarity >= self.threshold
        
        return QualityEvaluation(
            rule_id=self.id,
            passed=passed,
            score=avg_similarity,
            message=f"一致性分数: {avg_similarity:.2f}",
            details={"similarities": similarities, "threshold": self.threshold}
        )
    
    def _evaluate_completeness(self, data: Dict[str, Any]) -> 'QualityEvaluation':
        """评估完整性"""
        required_components = self.parameters.get("required_components", [])
        content = data.get("content", "")
        
        found_components = []
        for component in required_components:
            if component.lower() in content.lower():
                found_components.append(component)
        
        completeness_score = len(found_components) / len(required_components) if required_components else 1.0
        passed = completeness_score >= self.threshold
        
        return QualityEvaluation(
            rule_id=self.id,
            passed=passed,
            score=completeness_score,
            message=f"完整性分数: {completeness_score:.2f}",
            details={
                "found_components": found_components,
                "required_components": required_components,
                "threshold": self.threshold
            }
        )
    
    def _evaluate_relevance(self, data: Dict[str, Any]) -> 'QualityEvaluation':
        """评估相关性"""
        # 简化的相关性检查实现
        content = data.get("content", "")
        keywords = self.parameters.get("keywords", [])
        
        if not keywords:
            return QualityEvaluation(
                rule_id=self.id,
                passed=True,
                score=1.0,
                message="无关键词配置，跳过相关性检查",
                details={}
            )
        
        found_keywords = []
        for keyword in keywords:
            if keyword.lower() in content.lower():
                found_keywords.append(keyword)
        
        relevance_score = len(found_keywords) / len(keywords)
        passed = relevance_score >= self.threshold
        
        return QualityEvaluation(
            rule_id=self.id,
            passed=passed,
            score=relevance_score,
            message=f"相关性分数: {relevance_score:.2f}",
            details={
                "found_keywords": found_keywords,
                "keywords": keywords,
                "threshold": self.threshold
            }
        )
    
    def _evaluate_accuracy(self, data: Dict[str, Any]) -> 'QualityEvaluation':
        """评估准确性"""
        # 简化的准确性检查实现
        predicted = data.get("predicted", "")
        expected = data.get("expected", "")
        
        if not expected:
            return QualityEvaluation(
                rule_id=self.id,
                passed=True,
                score=1.0,
                message="无期望结果，跳过准确性检查",
                details={}
            )
        
        accuracy_score = self._calculate_similarity(predicted, expected)
        passed = accuracy_score >= self.threshold
        
        return QualityEvaluation(
            rule_id=self.id,
            passed=passed,
            score=accuracy_score,
            message=f"准确性分数: {accuracy_score:.2f}",
            details={
                "predicted": predicted,
                "expected": expected,
                "threshold": self.threshold
            }
        )
    
    def _evaluate_custom(self, data: Dict[str, Any]) -> 'QualityEvaluation':
        """评估自定义规则"""
        # 自定义规则的占位实现
        return QualityEvaluation(
            rule_id=self.id,
            passed=True,
            score=1.0,
            message="自定义规则评估（待实现）",
            details={}
        )
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 简化的相似度计算（基于字符重叠）
        set1 = set(text1.lower())
        set2 = set(text2.lower())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type.value,
            "parameters": self.parameters,
            "severity": self.severity.value,
            "is_active": self.is_active,
            "weight": self.weight,
            "threshold": self.threshold,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QualityRule':
        """从字典创建实例"""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            rule_type=QualityRuleType(data["rule_type"]),
            parameters=data.get("parameters", {}),
            severity=QualitySeverity(data.get("severity", "medium")),
            is_active=data.get("is_active", True),
            weight=data.get("weight", 1.0),
            threshold=data.get("threshold", 0.8),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            tags=data.get("tags", [])
        )


@dataclass
class QualityEvaluation:
    """质量评估结果"""
    rule_id: str
    passed: bool
    score: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rule_id": self.rule_id,
            "passed": self.passed,
            "score": self.score,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class QualityIssue:
    """质量问题"""
    rule_id: str
    severity: QualitySeverity
    description: str
    suggestion: str
    confidence: float
    location: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "description": self.description,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "location": self.location,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QualityIssue':
        """从字典创建实例"""
        return cls(
            rule_id=data["rule_id"],
            severity=QualitySeverity(data["severity"]),
            description=data["description"],
            suggestion=data["suggestion"],
            confidence=data["confidence"],
            location=data.get("location"),
            context=data.get("context", {}),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


@dataclass
class QualityMetric:
    """质量指标"""
    metric_type: QualityMetricType
    value: float
    weight: float = 1.0
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metric_type": self.metric_type.value,
            "value": self.value,
            "weight": self.weight,
            "description": self.description,
            "details": self.details
        }


@dataclass
class QualityReport:
    """质量报告"""
    overall_score: float
    metric_scores: Dict[str, float] = field(default_factory=dict)
    issues: List[QualityIssue] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    evaluations: List[QualityEvaluation] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_issue(self, issue: QualityIssue):
        """添加质量问题"""
        self.issues.append(issue)
    
    def add_suggestion(self, suggestion: str):
        """添加改进建议"""
        if suggestion not in self.suggestions:
            self.suggestions.append(suggestion)
    
    def get_issues_by_severity(self, severity: QualitySeverity) -> List[QualityIssue]:
        """按严重程度获取问题"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def get_critical_issues(self) -> List[QualityIssue]:
        """获取严重问题"""
        return self.get_issues_by_severity(QualitySeverity.CRITICAL)
    
    def has_critical_issues(self) -> bool:
        """是否有严重问题"""
        return len(self.get_critical_issues()) > 0
    
    def calculate_weighted_score(self, weights: Dict[str, float] = None) -> float:
        """计算加权分数"""
        if not self.metric_scores:
            return self.overall_score
        
        if weights is None:
            weights = {metric: 1.0 for metric in self.metric_scores.keys()}
        
        total_weight = sum(weights.values())
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(
            score * weights.get(metric, 1.0) 
            for metric, score in self.metric_scores.items()
        )
        
        return weighted_sum / total_weight
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "overall_score": self.overall_score,
            "metric_scores": self.metric_scores,
            "issues": [issue.to_dict() for issue in self.issues],
            "suggestions": self.suggestions,
            "evaluations": [eval.to_dict() for eval in self.evaluations],
            "generated_at": self.generated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QualityReport':
        """从字典创建实例"""
        issues = [
            QualityIssue.from_dict(issue_data) 
            for issue_data in data.get("issues", [])
        ]
        
        evaluations = [
            QualityEvaluation(
                rule_id=eval_data["rule_id"],
                passed=eval_data["passed"],
                score=eval_data["score"],
                message=eval_data["message"],
                details=eval_data.get("details", {}),
                timestamp=datetime.fromisoformat(eval_data["timestamp"])
            )
            for eval_data in data.get("evaluations", [])
        ]
        
        return cls(
            overall_score=data["overall_score"],
            metric_scores=data.get("metric_scores", {}),
            issues=issues,
            suggestions=data.get("suggestions", []),
            evaluations=evaluations,
            generated_at=datetime.fromisoformat(data["generated_at"]),
            metadata=data.get("metadata", {})
        )


# 导出所有模型类
__all__ = [
    "QualityRuleType",
    "QualitySeverity",
    "QualityMetricType",
    "QualityRule",
    "QualityEvaluation",
    "QualityIssue",
    "QualityMetric",
    "QualityReport"
]