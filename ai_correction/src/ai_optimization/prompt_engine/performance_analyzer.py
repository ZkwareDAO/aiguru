"""
提示词性能分析器

实现提示词效果评估指标、A/B测试框架和自动优化建议生成功能。
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
import json
import statistics
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
import random

from ..models.prompt_models import PromptTemplate, GeneratedPrompt, PerformanceMetrics
from ..config.config_manager import ConfigManager


class MetricType(Enum):
    """指标类型"""
    RESPONSE_TIME = "response_time"
    SUCCESS_RATE = "success_rate"
    QUALITY_SCORE = "quality_score"
    TOKEN_EFFICIENCY = "token_efficiency"
    USER_SATISFACTION = "user_satisfaction"
    CONSISTENCY = "consistency"


@dataclass
class PerformanceRecord:
    """性能记录"""
    template_id: str
    prompt_id: str
    timestamp: datetime
    response_time: float
    success: bool
    quality_score: float
    token_count: int
    user_feedback: Optional[float] = None
    context_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "template_id": self.template_id,
            "prompt_id": self.prompt_id,
            "timestamp": self.timestamp.isoformat(),
            "response_time": self.response_time,
            "success": self.success,
            "quality_score": self.quality_score,
            "token_count": self.token_count,
            "user_feedback": self.user_feedback,
            "context_info": self.context_info
        }


@dataclass
class ABTestGroup:
    """A/B测试组"""
    group_id: str
    template_id: str
    template_name: str
    sample_size: int = 0
    records: List[PerformanceRecord] = field(default_factory=list)
    
    def add_record(self, record: PerformanceRecord):
        """添加记录"""
        self.records.append(record)
        self.sample_size = len(self.records)
    
    def get_metrics(self) -> Dict[str, float]:
        """获取组指标"""
        if not self.records:
            return {}
        
        response_times = [r.response_time for r in self.records]
        quality_scores = [r.quality_score for r in self.records]
        success_count = sum(1 for r in self.records if r.success)
        token_counts = [r.token_count for r in self.records]
        
        return {
            "avg_response_time": statistics.mean(response_times),
            "success_rate": success_count / len(self.records),
            "avg_quality_score": statistics.mean(quality_scores),
            "avg_token_count": statistics.mean(token_counts),
            "sample_size": self.sample_size
        }


@dataclass
class ABTestResult:
    """A/B测试结果"""
    test_id: str
    start_time: datetime
    end_time: datetime
    groups: List[ABTestGroup]
    winner_group_id: Optional[str] = None
    confidence_level: float = 0.0
    statistical_significance: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "test_id": self.test_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "groups": [
                {
                    "group_id": group.group_id,
                    "template_id": group.template_id,
                    "template_name": group.template_name,
                    "metrics": group.get_metrics()
                }
                for group in self.groups
            ],
            "winner_group_id": self.winner_group_id,
            "confidence_level": self.confidence_level,
            "statistical_significance": self.statistical_significance
        }


class MetricsCalculator:
    """指标计算器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_response_time_metrics(self, records: List[PerformanceRecord]) -> Dict[str, float]:
        """计算响应时间指标"""
        if not records:
            return {}
        
        response_times = [r.response_time for r in records]
        
        return {
            "avg_response_time": statistics.mean(response_times),
            "median_response_time": statistics.median(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "std_response_time": statistics.stdev(response_times) if len(response_times) > 1 else 0
        }
    
    def calculate_success_rate_metrics(self, records: List[PerformanceRecord]) -> Dict[str, float]:
        """计算成功率指标"""
        if not records:
            return {}
        
        success_count = sum(1 for r in records if r.success)
        total_count = len(records)
        
        return {
            "success_rate": success_count / total_count,
            "failure_rate": (total_count - success_count) / total_count,
            "success_count": success_count,
            "total_count": total_count
        }
    
    def calculate_quality_metrics(self, records: List[PerformanceRecord]) -> Dict[str, float]:
        """计算质量指标"""
        if not records:
            return {}
        
        quality_scores = [r.quality_score for r in records if r.quality_score is not None]
        
        if not quality_scores:
            return {}
        
        return {
            "avg_quality_score": statistics.mean(quality_scores),
            "median_quality_score": statistics.median(quality_scores),
            "min_quality_score": min(quality_scores),
            "max_quality_score": max(quality_scores),
            "std_quality_score": statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0
        }
    
    def calculate_efficiency_metrics(self, records: List[PerformanceRecord]) -> Dict[str, float]:
        """计算效率指标"""
        if not records:
            return {}
        
        # Token效率 = 质量分数 / Token数量
        efficiency_scores = []
        for record in records:
            if record.token_count > 0 and record.quality_score is not None:
                efficiency = record.quality_score / record.token_count * 1000  # 每1000个token的质量分数
                efficiency_scores.append(efficiency)
        
        if not efficiency_scores:
            return {}
        
        return {
            "avg_token_efficiency": statistics.mean(efficiency_scores),
            "median_token_efficiency": statistics.median(efficiency_scores),
            "min_token_efficiency": min(efficiency_scores),
            "max_token_efficiency": max(efficiency_scores)
        }
    
    def calculate_consistency_metrics(self, records: List[PerformanceRecord]) -> Dict[str, float]:
        """计算一致性指标"""
        if len(records) < 2:
            return {}
        
        quality_scores = [r.quality_score for r in records if r.quality_score is not None]
        response_times = [r.response_time for r in records]
        
        consistency_metrics = {}
        
        # 质量一致性（变异系数）
        if quality_scores and len(quality_scores) > 1:
            mean_quality = statistics.mean(quality_scores)
            std_quality = statistics.stdev(quality_scores)
            consistency_metrics["quality_consistency"] = 1 - (std_quality / mean_quality) if mean_quality > 0 else 0
        
        # 响应时间一致性
        if len(response_times) > 1:
            mean_time = statistics.mean(response_times)
            std_time = statistics.stdev(response_times)
            consistency_metrics["time_consistency"] = 1 - (std_time / mean_time) if mean_time > 0 else 0
        
        return consistency_metrics


class ABTestManager:
    """A/B测试管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_tests: Dict[str, ABTestResult] = {}
        self.completed_tests: Dict[str, ABTestResult] = {}
        self._lock = threading.Lock()
    
    def create_ab_test(self, test_id: str, template_ids: List[str], 
                      template_names: List[str] = None) -> ABTestResult:
        """创建A/B测试"""
        if len(template_ids) < 2:
            raise ValueError("A/B测试至少需要2个模板")
        
        template_names = template_names or [f"Template_{i}" for i in range(len(template_ids))]
        
        groups = []
        for i, template_id in enumerate(template_ids):
            group = ABTestGroup(
                group_id=f"group_{i}",
                template_id=template_id,
                template_name=template_names[i] if i < len(template_names) else f"Template_{i}"
            )
            groups.append(group)
        
        ab_test = ABTestResult(
            test_id=test_id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(days=7),  # 默认7天
            groups=groups
        )
        
        with self._lock:
            self.active_tests[test_id] = ab_test
        
        self.logger.info(f"创建A/B测试: {test_id}, 模板数量: {len(template_ids)}")
        return ab_test
    
    def assign_to_group(self, test_id: str, user_context: Dict[str, Any] = None) -> Optional[str]:
        """分配用户到测试组"""
        with self._lock:
            if test_id not in self.active_tests:
                return None
            
            ab_test = self.active_tests[test_id]
            
            # 简单的随机分配策略
            group_index = random.randint(0, len(ab_test.groups) - 1)
            return ab_test.groups[group_index].template_id
    
    def record_test_result(self, test_id: str, template_id: str, record: PerformanceRecord):
        """记录测试结果"""
        with self._lock:
            if test_id not in self.active_tests:
                return
            
            ab_test = self.active_tests[test_id]
            
            # 找到对应的组
            for group in ab_test.groups:
                if group.template_id == template_id:
                    group.add_record(record)
                    break
    
    def analyze_test_results(self, test_id: str) -> Optional[ABTestResult]:
        """分析测试结果"""
        with self._lock:
            if test_id not in self.active_tests:
                return None
            
            ab_test = self.active_tests[test_id]
            
            # 检查是否有足够的样本
            min_sample_size = 30
            valid_groups = [g for g in ab_test.groups if g.sample_size >= min_sample_size]
            
            if len(valid_groups) < 2:
                self.logger.warning(f"A/B测试 {test_id} 样本量不足")
                return ab_test
            
            # 计算各组指标
            group_metrics = []
            for group in valid_groups:
                metrics = group.get_metrics()
                group_metrics.append((group.group_id, metrics))
            
            # 找出最佳组（基于综合分数）
            best_group_id = None
            best_score = -1
            
            for group_id, metrics in group_metrics:
                # 综合分数 = 质量分数 * 成功率 - 响应时间惩罚
                score = (metrics.get("avg_quality_score", 0) * 
                        metrics.get("success_rate", 0) - 
                        metrics.get("avg_response_time", 0) * 0.01)
                
                if score > best_score:
                    best_score = score
                    best_group_id = group_id
            
            # 计算统计显著性（简化版本）
            ab_test.winner_group_id = best_group_id
            ab_test.confidence_level = self._calculate_confidence_level(group_metrics)
            ab_test.statistical_significance = ab_test.confidence_level > 0.95
            
            return ab_test
    
    def _calculate_confidence_level(self, group_metrics: List[Tuple[str, Dict[str, float]]]) -> float:
        """计算置信水平（简化版本）"""
        if len(group_metrics) < 2:
            return 0.0
        
        # 简化的置信度计算，基于样本量和效果差异
        sample_sizes = [metrics["sample_size"] for _, metrics in group_metrics]
        quality_scores = [metrics.get("avg_quality_score", 0) for _, metrics in group_metrics]
        
        min_sample_size = min(sample_sizes)
        max_quality_diff = max(quality_scores) - min(quality_scores)
        
        # 基于样本量和效果差异的简化置信度
        confidence = min(0.99, (min_sample_size / 100) * (max_quality_diff * 10))
        return max(0.5, confidence)
    
    def complete_test(self, test_id: str) -> Optional[ABTestResult]:
        """完成测试"""
        with self._lock:
            if test_id not in self.active_tests:
                return None
            
            ab_test = self.active_tests[test_id]
            ab_test.end_time = datetime.now()
            
            # 分析最终结果
            final_result = self.analyze_test_results(test_id)
            
            # 移动到已完成测试
            self.completed_tests[test_id] = ab_test
            del self.active_tests[test_id]
            
            self.logger.info(f"A/B测试完成: {test_id}, 获胜组: {ab_test.winner_group_id}")
            return final_result
    
    def get_test_status(self, test_id: str) -> Optional[Dict[str, Any]]:
        """获取测试状态"""
        with self._lock:
            if test_id in self.active_tests:
                ab_test = self.active_tests[test_id]
                return {
                    "status": "active",
                    "progress": self._calculate_test_progress(ab_test),
                    "groups": [
                        {
                            "group_id": g.group_id,
                            "template_name": g.template_name,
                            "sample_size": g.sample_size
                        }
                        for g in ab_test.groups
                    ]
                }
            elif test_id in self.completed_tests:
                ab_test = self.completed_tests[test_id]
                return {
                    "status": "completed",
                    "winner": ab_test.winner_group_id,
                    "confidence": ab_test.confidence_level,
                    "significant": ab_test.statistical_significance
                }
            else:
                return None
    
    def _calculate_test_progress(self, ab_test: ABTestResult) -> float:
        """计算测试进度"""
        target_sample_size = 100  # 目标样本量
        total_samples = sum(g.sample_size for g in ab_test.groups)
        total_target = target_sample_size * len(ab_test.groups)
        
        return min(1.0, total_samples / total_target)


class OptimizationAdvisor:
    """优化建议生成器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_optimization_suggestions(self, template_id: str, 
                                        records: List[PerformanceRecord],
                                        template: PromptTemplate = None) -> List[str]:
        """生成优化建议"""
        if not records:
            return ["暂无性能数据，无法生成建议"]
        
        suggestions = []
        
        # 分析性能指标
        calculator = MetricsCalculator()
        
        response_metrics = calculator.calculate_response_time_metrics(records)
        success_metrics = calculator.calculate_success_rate_metrics(records)
        quality_metrics = calculator.calculate_quality_metrics(records)
        efficiency_metrics = calculator.calculate_efficiency_metrics(records)
        consistency_metrics = calculator.calculate_consistency_metrics(records)
        
        # 响应时间建议
        if response_metrics.get("avg_response_time", 0) > 10:
            suggestions.append("平均响应时间较长，建议简化提示词内容或优化参数设置")
        
        if response_metrics.get("std_response_time", 0) > 5:
            suggestions.append("响应时间波动较大，建议检查网络稳定性或API配置")
        
        # 成功率建议
        if success_metrics.get("success_rate", 1) < 0.9:
            suggestions.append("成功率较低，建议检查提示词格式和参数验证")
        
        # 质量分数建议
        if quality_metrics.get("avg_quality_score", 1) < 0.7:
            suggestions.append("质量分数较低，建议优化提示词内容和结构")
        
        if quality_metrics.get("std_quality_score", 0) > 0.2:
            suggestions.append("质量分数波动较大，建议增强提示词的一致性")
        
        # 效率建议
        if efficiency_metrics.get("avg_token_efficiency", 0) < 0.5:
            suggestions.append("Token使用效率较低，建议精简提示词内容")
        
        # 一致性建议
        if consistency_metrics.get("quality_consistency", 1) < 0.8:
            suggestions.append("质量一致性较低，建议标准化提示词格式")
        
        if consistency_metrics.get("time_consistency", 1) < 0.8:
            suggestions.append("响应时间一致性较低，建议优化API调用策略")
        
        # 基于模板内容的建议
        if template:
            template_suggestions = self._analyze_template_content(template, records)
            suggestions.extend(template_suggestions)
        
        return suggestions if suggestions else ["模板性能表现良好，暂无优化建议"]
    
    def _analyze_template_content(self, template: PromptTemplate, 
                                records: List[PerformanceRecord]) -> List[str]:
        """分析模板内容并生成建议"""
        suggestions = []
        
        # 分析模板长度
        total_length = sum(len(content) for content in template.layers.values())
        avg_response_time = statistics.mean([r.response_time for r in records])
        
        if total_length > 3000 and avg_response_time > 8:
            suggestions.append("模板内容较长且响应时间较慢，建议精简描述")
        
        # 分析参数数量
        if len(template.parameters) > 10:
            failure_rate = 1 - statistics.mean([1 if r.success else 0 for r in records])
            if failure_rate > 0.1:
                suggestions.append("参数过多可能导致错误率增加，建议合并相关参数")
        
        # 分析标签完整性
        if not template.tags:
            suggestions.append("建议为模板添加标签以便更好地分类和优化")
        
        return suggestions


class PerformanceAnalyzer:
    """提示词性能分析器"""
    
    def __init__(self, config_manager: ConfigManager = None):
        """初始化性能分析器"""
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        self.config = self._load_config()
        
        # 初始化组件
        self.metrics_calculator = MetricsCalculator()
        self.ab_test_manager = ABTestManager()
        self.optimization_advisor = OptimizationAdvisor()
        
        # 性能记录存储
        self.performance_records: Dict[str, List[PerformanceRecord]] = {}
        self._records_lock = threading.Lock()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        return {
            "max_records_per_template": self.config_manager.get(
                "performance_analyzer.max_records_per_template", 1000
            ),
            "analysis_window_days": self.config_manager.get(
                "performance_analyzer.analysis_window_days", 30
            ),
            "min_sample_size": self.config_manager.get(
                "performance_analyzer.min_sample_size", 10
            ),
            "enable_ab_testing": self.config_manager.get(
                "performance_analyzer.enable_ab_testing", True
            )
        }
    
    def record_performance(self, template_id: str, prompt: GeneratedPrompt,
                          response_time: float, success: bool, 
                          quality_score: float, user_feedback: float = None):
        """记录性能数据"""
        record = PerformanceRecord(
            template_id=template_id,
            prompt_id=prompt.context_hash,
            timestamp=datetime.now(),
            response_time=response_time,
            success=success,
            quality_score=quality_score,
            token_count=prompt.get_token_count(),
            user_feedback=user_feedback,
            context_info=prompt.usage_stats
        )
        
        with self._records_lock:
            if template_id not in self.performance_records:
                self.performance_records[template_id] = []
            
            self.performance_records[template_id].append(record)
            
            # 限制记录数量
            max_records = self.config["max_records_per_template"]
            if len(self.performance_records[template_id]) > max_records:
                self.performance_records[template_id] = self.performance_records[template_id][-max_records:]
        
        self.logger.debug(f"记录性能数据: {template_id}, 响应时间: {response_time:.2f}s")
    
    def analyze_template_performance(self, template_id: str, 
                                   time_window_days: int = None) -> Dict[str, Any]:
        """分析模板性能"""
        time_window_days = time_window_days or self.config["analysis_window_days"]
        
        with self._records_lock:
            if template_id not in self.performance_records:
                return {"error": "没有找到性能记录"}
            
            all_records = self.performance_records[template_id]
        
        # 过滤时间窗口内的记录
        cutoff_time = datetime.now() - timedelta(days=time_window_days)
        recent_records = [r for r in all_records if r.timestamp >= cutoff_time]
        
        if not recent_records:
            return {"error": "时间窗口内没有性能记录"}
        
        # 计算各种指标
        analysis = {
            "template_id": template_id,
            "analysis_period": {
                "start_time": min(r.timestamp for r in recent_records).isoformat(),
                "end_time": max(r.timestamp for r in recent_records).isoformat(),
                "total_records": len(recent_records)
            }
        }
        
        # 响应时间指标
        analysis["response_time"] = self.metrics_calculator.calculate_response_time_metrics(recent_records)
        
        # 成功率指标
        analysis["success_rate"] = self.metrics_calculator.calculate_success_rate_metrics(recent_records)
        
        # 质量指标
        analysis["quality"] = self.metrics_calculator.calculate_quality_metrics(recent_records)
        
        # 效率指标
        analysis["efficiency"] = self.metrics_calculator.calculate_efficiency_metrics(recent_records)
        
        # 一致性指标
        analysis["consistency"] = self.metrics_calculator.calculate_consistency_metrics(recent_records)
        
        return analysis
    
    def compare_templates(self, template_ids: List[str], 
                         time_window_days: int = None) -> Dict[str, Any]:
        """比较多个模板的性能"""
        comparison = {
            "templates": {},
            "ranking": [],
            "comparison_time": datetime.now().isoformat()
        }
        
        template_scores = []
        
        for template_id in template_ids:
            analysis = self.analyze_template_performance(template_id, time_window_days)
            
            if "error" not in analysis:
                comparison["templates"][template_id] = analysis
                
                # 计算综合分数
                score = self._calculate_composite_score(analysis)
                template_scores.append((template_id, score))
        
        # 排序
        template_scores.sort(key=lambda x: x[1], reverse=True)
        comparison["ranking"] = [
            {"template_id": tid, "score": score} 
            for tid, score in template_scores
        ]
        
        return comparison
    
    def _calculate_composite_score(self, analysis: Dict[str, Any]) -> float:
        """计算综合分数"""
        weights = {
            "quality": 0.4,
            "success_rate": 0.3,
            "efficiency": 0.2,
            "consistency": 0.1
        }
        
        score = 0.0
        
        # 质量分数
        quality_score = analysis.get("quality", {}).get("avg_quality_score", 0)
        score += quality_score * weights["quality"]
        
        # 成功率
        success_rate = analysis.get("success_rate", {}).get("success_rate", 0)
        score += success_rate * weights["success_rate"]
        
        # 效率分数（标准化）
        efficiency = analysis.get("efficiency", {}).get("avg_token_efficiency", 0)
        normalized_efficiency = min(1.0, efficiency / 2.0)  # 假设2.0是很好的效率
        score += normalized_efficiency * weights["efficiency"]
        
        # 一致性分数
        quality_consistency = analysis.get("consistency", {}).get("quality_consistency", 0)
        score += quality_consistency * weights["consistency"]
        
        return score
    
    def create_ab_test(self, test_id: str, template_ids: List[str], 
                      template_names: List[str] = None) -> ABTestResult:
        """创建A/B测试"""
        if not self.config["enable_ab_testing"]:
            raise ValueError("A/B测试功能未启用")
        
        return self.ab_test_manager.create_ab_test(test_id, template_ids, template_names)
    
    def participate_in_ab_test(self, test_id: str, 
                              user_context: Dict[str, Any] = None) -> Optional[str]:
        """参与A/B测试"""
        return self.ab_test_manager.assign_to_group(test_id, user_context)
    
    def record_ab_test_result(self, test_id: str, template_id: str, 
                             prompt: GeneratedPrompt, response_time: float,
                             success: bool, quality_score: float):
        """记录A/B测试结果"""
        record = PerformanceRecord(
            template_id=template_id,
            prompt_id=prompt.context_hash,
            timestamp=datetime.now(),
            response_time=response_time,
            success=success,
            quality_score=quality_score,
            token_count=prompt.get_token_count(),
            context_info=prompt.usage_stats
        )
        
        # 同时记录到性能记录和A/B测试
        self.record_performance(template_id, prompt, response_time, success, quality_score)
        self.ab_test_manager.record_test_result(test_id, template_id, record)
    
    def analyze_ab_test(self, test_id: str) -> Optional[ABTestResult]:
        """分析A/B测试结果"""
        return self.ab_test_manager.analyze_test_results(test_id)
    
    def complete_ab_test(self, test_id: str) -> Optional[ABTestResult]:
        """完成A/B测试"""
        return self.ab_test_manager.complete_test(test_id)
    
    def get_optimization_suggestions(self, template_id: str, 
                                   template: PromptTemplate = None) -> List[str]:
        """获取优化建议"""
        with self._records_lock:
            records = self.performance_records.get(template_id, [])
        
        if len(records) < self.config["min_sample_size"]:
            return [f"样本量不足（当前: {len(records)}, 最少需要: {self.config['min_sample_size']}）"]
        
        return self.optimization_advisor.generate_optimization_suggestions(
            template_id, records, template
        )
    
    def generate_performance_report(self, template_ids: List[str] = None,
                                  time_window_days: int = None) -> Dict[str, Any]:
        """生成性能报告"""
        if template_ids is None:
            with self._records_lock:
                template_ids = list(self.performance_records.keys())
        
        report = {
            "report_time": datetime.now().isoformat(),
            "time_window_days": time_window_days or self.config["analysis_window_days"],
            "templates": {},
            "summary": {
                "total_templates": len(template_ids),
                "total_records": 0,
                "avg_performance_score": 0.0
            }
        }
        
        total_records = 0
        performance_scores = []
        
        for template_id in template_ids:
            analysis = self.analyze_template_performance(template_id, time_window_days)
            
            if "error" not in analysis:
                report["templates"][template_id] = analysis
                total_records += analysis["analysis_period"]["total_records"]
                
                score = self._calculate_composite_score(analysis)
                performance_scores.append(score)
        
        report["summary"]["total_records"] = total_records
        if performance_scores:
            report["summary"]["avg_performance_score"] = statistics.mean(performance_scores)
        
        return report
    
    def clear_performance_data(self, template_id: str = None):
        """清空性能数据"""
        with self._records_lock:
            if template_id:
                if template_id in self.performance_records:
                    del self.performance_records[template_id]
                    self.logger.info(f"清空模板性能数据: {template_id}")
            else:
                self.performance_records.clear()
                self.logger.info("清空所有性能数据")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        with self._records_lock:
            total_records = sum(len(records) for records in self.performance_records.values())
            
            return {
                "total_templates": len(self.performance_records),
                "total_records": total_records,
                "active_ab_tests": len(self.ab_test_manager.active_tests),
                "completed_ab_tests": len(self.ab_test_manager.completed_tests),
                "config": self.config
            }