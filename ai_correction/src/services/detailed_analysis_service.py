#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细分析服务
提供学生成绩的详细分析功能
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import statistics
import numpy as np
from datetime import datetime, timedelta

from src.models.analysis import (
    DetailedAnalysis, StudentResult, ClassStatistics, ComparisonData,
    TrendAnalysis, TrendPoint, WeaknessArea, ScoreBreakdown,
    ImprovementSuggestion, AnalysisType
)


class DetailedAnalysisService:
    """详细分析服务类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_individual_analysis(self, student_result: StudentResult, 
                                   class_statistics: ClassStatistics) -> DetailedAnalysis:
        """生成个人详细分析"""
        try:
            analysis = DetailedAnalysis(
                analysis_type=AnalysisType.INDIVIDUAL,
                student_result=student_result,
                class_statistics=class_statistics
            )
            
            # 生成改进建议
            self._generate_improvement_suggestions(student_result, class_statistics)
            
            # 分析薄弱知识点
            weakness_areas = self._identify_weakness_areas([student_result])
            analysis.weakness_areas = weakness_areas
            
            self.logger.info(f"生成个人分析完成: {student_result.student_name}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"生成个人分析失败: {e}")
            raise
    
    def generate_comparison_analysis(self, student_results: List[StudentResult]) -> DetailedAnalysis:
        """生成对比分析"""
        try:
            if len(student_results) < 2:
                raise ValueError("对比分析至少需要2个学生的结果")
            
            # 计算对比指标
            comparison_metrics = self._calculate_comparison_metrics(student_results)
            
            # 生成相对表现描述
            relative_performance = self._generate_relative_performance(student_results)
            
            comparison_data = ComparisonData(
                student_results=student_results,
                comparison_metrics=comparison_metrics,
                relative_performance=relative_performance
            )
            
            analysis = DetailedAnalysis(
                analysis_type=AnalysisType.COMPARISON,
                comparison_data=comparison_data
            )
            
            self.logger.info(f"生成对比分析完成: {len(student_results)}个学生")
            return analysis
            
        except Exception as e:
            self.logger.error(f"生成对比分析失败: {e}")
            raise
    
    def generate_trend_analysis(self, student_id: str, historical_results: List[StudentResult]) -> DetailedAnalysis:
        """生成趋势分析"""
        try:
            if len(historical_results) < 3:
                raise ValueError("趋势分析至少需要3次历史记录")
            
            # 按时间排序
            sorted_results = sorted(historical_results, 
                                  key=lambda x: x.grading_time or datetime.now())
            
            # 创建趋势点
            trend_points = []
            for result in sorted_results:
                trend_point = TrendPoint(
                    date=result.grading_time or datetime.now(),
                    assignment_id=result.assignment_id,
                    assignment_title=result.assignment_title,
                    score=result.total_score,
                    percentage=result.percentage,
                    rank=result.rank
                )
                trend_points.append(trend_point)
            
            # 分析趋势
            trend_direction, trend_description = self._analyze_trend(trend_points)
            
            # 生成性能洞察
            performance_insights = self._generate_performance_insights(trend_points)
            
            trend_analysis = TrendAnalysis(
                student_id=student_id,
                student_name=sorted_results[0].student_name,
                trend_points=trend_points,
                overall_trend=trend_direction,
                trend_description=trend_description,
                performance_insights=performance_insights
            )
            
            analysis = DetailedAnalysis(
                analysis_type=AnalysisType.TREND,
                trend_analysis=trend_analysis
            )
            
            self.logger.info(f"生成趋势分析完成: {student_id}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"生成趋势分析失败: {e}")
            raise
    
    def calculate_class_statistics(self, student_results: List[StudentResult]) -> ClassStatistics:
        """计算班级统计信息"""
        try:
            if not student_results:
                raise ValueError("学生结果列表不能为空")
            
            scores = [result.total_score for result in student_results]
            percentages = [result.percentage for result in student_results]
            
            # 基本统计
            average_score = statistics.mean(scores)
            median_score = statistics.median(scores)
            highest_score = max(scores)
            lowest_score = min(scores)
            std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0
            
            # 分数段分布
            score_distribution = self._calculate_score_distribution(percentages)
            
            # 共同优势和薄弱点
            common_strengths, common_weaknesses = self._analyze_common_patterns(student_results)
            
            # 获取班级信息（假设所有学生来自同一班级）
            first_result = student_results[0]
            
            class_stats = ClassStatistics(
                class_id="default_class",  # 这里应该从实际数据获取
                class_name="默认班级",
                assignment_id=first_result.assignment_id,
                assignment_title=first_result.assignment_title,
                total_students=len(student_results),
                submitted_count=len(student_results),
                graded_count=len(student_results),
                average_score=average_score,
                median_score=median_score,
                highest_score=highest_score,
                lowest_score=lowest_score,
                standard_deviation=std_dev,
                score_distribution=score_distribution,
                common_strengths=common_strengths,
                common_weaknesses=common_weaknesses
            )
            
            self.logger.info(f"计算班级统计完成: {len(student_results)}个学生")
            return class_stats
            
        except Exception as e:
            self.logger.error(f"计算班级统计失败: {e}")
            raise
    
    def _generate_improvement_suggestions(self, student_result: StudentResult, 
                                        class_statistics: ClassStatistics):
        """生成改进建议"""
        suggestions = []
        
        # 基于得分细分生成建议
        for breakdown in student_result.score_breakdown:
            if breakdown.percentage < 80:  # 低于80%的项目需要改进
                priority = "high" if breakdown.percentage < 60 else "medium"
                
                suggestion = ImprovementSuggestion(
                    category=breakdown.criterion_name,
                    priority=priority,
                    suggestion=f"在{breakdown.criterion_name}方面需要加强练习",
                    examples=[f"当前得分: {breakdown.score:.1f}/{breakdown.max_score}"],
                    resources=["相关练习题", "参考资料"]
                )
                suggestions.append(suggestion)
        
        # 基于班级平均水平生成建议
        if student_result.percentage < class_statistics.average_score:
            suggestion = ImprovementSuggestion(
                category="整体表现",
                priority="medium",
                suggestion="整体表现低于班级平均水平，建议加强基础练习",
                examples=[f"班级平均分: {class_statistics.average_score:.1f}%"],
                resources=["基础练习册", "辅导资料"]
            )
            suggestions.append(suggestion)
        
        # 确保至少有一个建议
        if not suggestions:
            suggestion = ImprovementSuggestion(
                category="持续改进",
                priority="low",
                suggestion="表现良好，建议继续保持并寻求进一步提升",
                examples=["可以尝试更有挑战性的练习"],
                resources=["进阶练习材料", "拓展阅读"]
            )
            suggestions.append(suggestion)
        
        student_result.improvement_suggestions = suggestions
    
    def _identify_weakness_areas(self, student_results: List[StudentResult]) -> List[WeaknessArea]:
        """识别薄弱知识点"""
        weakness_areas = []
        
        # 统计各评分标准的表现
        criterion_stats = {}
        for result in student_results:
            for breakdown in result.score_breakdown:
                if breakdown.criterion_name not in criterion_stats:
                    criterion_stats[breakdown.criterion_name] = []
                criterion_stats[breakdown.criterion_name].append(breakdown.percentage)
        
        # 识别薄弱点
        for criterion_name, percentages in criterion_stats.items():
            avg_percentage = statistics.mean(percentages)
            if avg_percentage < 60:  # 平均得分率低于60%视为薄弱点
                affected_students = [
                    result.student_id for result in student_results
                    for breakdown in result.score_breakdown
                    if breakdown.criterion_name == criterion_name and breakdown.percentage < 70
                ]
                
                weakness_area = WeaknessArea(
                    area_name=criterion_name,
                    description=f"{criterion_name}是班级的薄弱环节",
                    affected_students=affected_students,
                    average_score=avg_percentage,
                    improvement_rate=100 - avg_percentage,
                    recommended_actions=[
                        f"加强{criterion_name}的专项训练",
                        "提供相关的辅导材料",
                        "组织小组讨论和互助学习"
                    ]
                )
                weakness_areas.append(weakness_area)
        
        return weakness_areas
    
    def _calculate_comparison_metrics(self, student_results: List[StudentResult]) -> Dict[str, List[float]]:
        """计算对比指标"""
        metrics = {
            'total_scores': [result.total_score for result in student_results],
            'percentages': [result.percentage for result in student_results],
            'ranks': [result.rank for result in student_results]
        }
        
        # 按评分标准分组对比
        criterion_names = set()
        for result in student_results:
            for breakdown in result.score_breakdown:
                criterion_names.add(breakdown.criterion_name)
        
        for criterion_name in criterion_names:
            criterion_scores = []
            for result in student_results:
                for breakdown in result.score_breakdown:
                    if breakdown.criterion_name == criterion_name:
                        criterion_scores.append(breakdown.percentage)
                        break
                else:
                    criterion_scores.append(0.0)  # 如果没有该项评分
            metrics[f'{criterion_name}_scores'] = criterion_scores
        
        return metrics
    
    def _generate_relative_performance(self, student_results: List[StudentResult]) -> Dict[str, str]:
        """生成相对表现描述"""
        performance = {}
        
        if len(student_results) == 2:
            result1, result2 = student_results
            if result1.percentage > result2.percentage:
                diff = result1.percentage - result2.percentage
                performance[result1.student_id] = f"领先{diff:.1f}个百分点"
                performance[result2.student_id] = f"落后{diff:.1f}个百分点"
            elif result2.percentage > result1.percentage:
                diff = result2.percentage - result1.percentage
                performance[result2.student_id] = f"领先{diff:.1f}个百分点"
                performance[result1.student_id] = f"落后{diff:.1f}个百分点"
            else:
                performance[result1.student_id] = "表现相当"
                performance[result2.student_id] = "表现相当"
        
        return performance
    
    def _analyze_trend(self, trend_points: List[TrendPoint]) -> Tuple[str, str]:
        """分析趋势方向"""
        if len(trend_points) < 2:
            return "stable", "数据不足以分析趋势"
        
        # 计算线性趋势
        scores = [point.percentage for point in trend_points]
        x = list(range(len(scores)))
        
        # 简单线性回归
        n = len(scores)
        sum_x = sum(x)
        sum_y = sum(scores)
        sum_xy = sum(x[i] * scores[i] for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        if slope > 2:
            return "improving", f"成绩呈上升趋势，平均每次提高{slope:.1f}分"
        elif slope < -2:
            return "declining", f"成绩呈下降趋势，平均每次下降{abs(slope):.1f}分"
        else:
            return "stable", "成绩相对稳定"
    
    def _generate_performance_insights(self, trend_points: List[TrendPoint]) -> List[str]:
        """生成性能洞察"""
        insights = []
        
        if len(trend_points) < 3:
            return ["数据不足以生成深入洞察"]
        
        scores = [point.percentage for point in trend_points]
        
        # 最佳表现
        best_score = max(scores)
        best_index = scores.index(best_score)
        insights.append(f"最佳表现出现在{trend_points[best_index].assignment_title}，得分{best_score:.1f}%")
        
        # 最近表现
        recent_score = scores[-1]
        previous_score = scores[-2]
        if recent_score > previous_score:
            insights.append(f"最近一次作业表现有所提升，提高了{recent_score - previous_score:.1f}个百分点")
        elif recent_score < previous_score:
            insights.append(f"最近一次作业表现有所下降，下降了{previous_score - recent_score:.1f}个百分点")
        else:
            insights.append("最近一次作业表现保持稳定")
        
        # 稳定性分析
        std_dev = statistics.stdev(scores)
        if std_dev < 5:
            insights.append("成绩表现较为稳定")
        elif std_dev > 15:
            insights.append("成绩波动较大，建议保持学习的连续性")
        
        return insights
    
    def _calculate_score_distribution(self, percentages: List[float]) -> Dict[str, int]:
        """计算分数段分布"""
        distribution = {
            "优秀(90-100%)": 0,
            "良好(80-89%)": 0,
            "中等(70-79%)": 0,
            "及格(60-69%)": 0,
            "不及格(0-59%)": 0
        }
        
        for percentage in percentages:
            if percentage >= 90:
                distribution["优秀(90-100%)"] += 1
            elif percentage >= 80:
                distribution["良好(80-89%)"] += 1
            elif percentage >= 70:
                distribution["中等(70-79%)"] += 1
            elif percentage >= 60:
                distribution["及格(60-69%)"] += 1
            else:
                distribution["不及格(0-59%)"] += 1
        
        return distribution
    
    def _analyze_common_patterns(self, student_results: List[StudentResult]) -> Tuple[List[str], List[str]]:
        """分析共同优势和薄弱点"""
        strengths = []
        weaknesses = []
        
        # 统计各评分标准的平均表现
        criterion_performance = {}
        for result in student_results:
            for breakdown in result.score_breakdown:
                if breakdown.criterion_name not in criterion_performance:
                    criterion_performance[breakdown.criterion_name] = []
                criterion_performance[breakdown.criterion_name].append(breakdown.percentage)
        
        # 识别优势和薄弱点
        for criterion_name, percentages in criterion_performance.items():
            avg_percentage = statistics.mean(percentages)
            if avg_percentage >= 80:
                strengths.append(f"{criterion_name}表现优秀，平均得分率{avg_percentage:.1f}%")
            elif avg_percentage < 60:
                weaknesses.append(f"{criterion_name}需要加强，平均得分率{avg_percentage:.1f}%")
        
        return strengths, weaknesses