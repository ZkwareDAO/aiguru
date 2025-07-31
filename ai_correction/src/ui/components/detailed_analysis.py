#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细分析UI组件
提供学生成绩的详细分析界面
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Dict, Any, Optional
import logging

from src.models.analysis import (
    DetailedAnalysis, StudentResult, ClassStatistics, ComparisonData,
    TrendAnalysis, WeaknessArea, AnalysisType
)
from src.services.detailed_analysis_service import DetailedAnalysisService


class DetailedAnalysisComponent:
    """详细分析组件"""
    
    def __init__(self, analysis_service: DetailedAnalysisService):
        self.analysis_service = analysis_service
        self.logger = logging.getLogger(__name__)
    
    def render(self):
        """渲染详细分析界面"""
        st.header("📊 详细分析")
        
        # 分析类型选择
        analysis_type = st.selectbox(
            "选择分析类型",
            ["个人详细分析", "学生对比分析", "班级统计分析", "趋势分析"],
            key="analysis_type_selector"
        )
        
        if analysis_type == "个人详细分析":
            self._render_individual_analysis()
        elif analysis_type == "学生对比分析":
            self._render_comparison_analysis()
        elif analysis_type == "班级统计分析":
            self._render_class_statistics()
        elif analysis_type == "趋势分析":
            self._render_trend_analysis()
    
    def _render_individual_analysis(self):
        """渲染个人详细分析"""
        st.subheader("👤 个人详细分析")
        
        # 模拟数据选择（实际应用中从数据库获取）
        student_name = st.selectbox(
            "选择学生",
            ["张三", "李四", "王五", "赵六"],
            key="individual_student_selector"
        )
        
        assignment_name = st.selectbox(
            "选择作业",
            ["数学期中考试", "语文作文练习", "英语阅读理解", "物理实验报告"],
            key="individual_assignment_selector"
        )
        
        if st.button("生成个人分析", key="generate_individual"):
            # 创建模拟数据
            student_result = self._create_mock_student_result(student_name, assignment_name)
            class_statistics = self._create_mock_class_statistics(assignment_name)
            
            # 生成分析
            analysis = self.analysis_service.generate_individual_analysis(
                student_result, class_statistics
            )
            
            # 显示分析结果
            self._display_individual_analysis(analysis)
    
    def _render_comparison_analysis(self):
        """渲染对比分析"""
        st.subheader("🔄 学生对比分析")
        
        # 学生选择
        selected_students = st.multiselect(
            "选择要对比的学生（2-5个）",
            ["张三", "李四", "王五", "赵六", "钱七", "孙八"],
            default=["张三", "李四"],
            key="comparison_students_selector"
        )
        
        assignment_name = st.selectbox(
            "选择作业",
            ["数学期中考试", "语文作文练习", "英语阅读理解", "物理实验报告"],
            key="comparison_assignment_selector"
        )
        
        if len(selected_students) >= 2 and st.button("生成对比分析", key="generate_comparison"):
            # 创建模拟数据
            student_results = [
                self._create_mock_student_result(name, assignment_name, i)
                for i, name in enumerate(selected_students)
            ]
            
            # 生成分析
            analysis = self.analysis_service.generate_comparison_analysis(student_results)
            
            # 显示分析结果
            self._display_comparison_analysis(analysis)
        elif len(selected_students) < 2:
            st.warning("请至少选择2个学生进行对比")
    
    def _render_class_statistics(self):
        """渲染班级统计分析"""
        st.subheader("📈 班级统计分析")
        
        class_name = st.selectbox(
            "选择班级",
            ["高一(1)班", "高一(2)班", "高二(1)班", "高二(2)班"],
            key="class_statistics_selector"
        )
        
        assignment_name = st.selectbox(
            "选择作业",
            ["数学期中考试", "语文作文练习", "英语阅读理解", "物理实验报告"],
            key="class_assignment_selector"
        )
        
        if st.button("生成班级统计", key="generate_class_stats"):
            # 创建模拟班级数据
            student_results = self._create_mock_class_results(class_name, assignment_name)
            class_statistics = self.analysis_service.calculate_class_statistics(student_results)
            
            # 显示统计结果
            self._display_class_statistics(class_statistics, student_results)
    
    def _render_trend_analysis(self):
        """渲染趋势分析"""
        st.subheader("📈 趋势分析")
        
        student_name = st.selectbox(
            "选择学生",
            ["张三", "李四", "王五", "赵六"],
            key="trend_student_selector"
        )
        
        time_period = st.selectbox(
            "选择时间范围",
            ["最近3次作业", "最近5次作业", "本学期全部", "本学年全部"],
            key="trend_period_selector"
        )
        
        if st.button("生成趋势分析", key="generate_trend"):
            # 创建模拟历史数据
            historical_results = self._create_mock_historical_results(student_name, time_period)
            
            # 生成分析
            analysis = self.analysis_service.generate_trend_analysis(
                "student_001", historical_results
            )
            
            # 显示分析结果
            self._display_trend_analysis(analysis)
    
    def _display_individual_analysis(self, analysis: DetailedAnalysis):
        """显示个人分析结果"""
        if not analysis.student_result:
            st.error("分析数据不完整")
            return
        
        student = analysis.student_result
        class_stats = analysis.class_statistics
        
        # 基本信息卡片
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总分", f"{student.total_score:.1f}", f"满分 {student.max_score}")
        
        with col2:
            st.metric("得分率", f"{student.percentage:.1f}%")
        
        with col3:
            st.metric("班级排名", f"{student.rank}/{student.class_size}")
        
        with col4:
            if class_stats:
                diff = student.percentage - class_stats.average_score
                st.metric("vs班级平均", f"{diff:+.1f}%", f"班级平均 {class_stats.average_score:.1f}%")
        
        # 得分细分图表
        if student.score_breakdown:
            st.subheader("📊 得分细分")
            
            # 创建雷达图
            categories = [sb.criterion_name for sb in student.score_breakdown]
            scores = [sb.percentage for sb in student.score_breakdown]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=scores,
                theta=categories,
                fill='toself',
                name='得分率',
                line_color='rgb(59, 130, 246)'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )),
                showlegend=True,
                title="各项得分雷达图"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 详细得分表格
            score_df = pd.DataFrame([
                {
                    "评分项目": sb.criterion_name,
                    "得分": f"{sb.score:.1f}",
                    "满分": f"{sb.max_score:.1f}",
                    "得分率": f"{sb.percentage:.1f}%",
                    "反馈": sb.feedback or "无"
                }
                for sb in student.score_breakdown
            ])
            
            st.dataframe(score_df, use_container_width=True)
        
        # 改进建议
        if student.improvement_suggestions:
            st.subheader("💡 改进建议")
            
            for suggestion in student.improvement_suggestions:
                priority_color = {
                    "high": "🔴",
                    "medium": "🟡", 
                    "low": "🟢"
                }.get(suggestion.priority, "⚪")
                
                with st.expander(f"{priority_color} {suggestion.category}"):
                    st.write(f"**建议**: {suggestion.suggestion}")
                    if suggestion.examples:
                        st.write("**示例**:")
                        for example in suggestion.examples:
                            st.write(f"- {example}")
                    if suggestion.resources:
                        st.write("**相关资源**:")
                        for resource in suggestion.resources:
                            st.write(f"- {resource}")
        
        # 薄弱知识点
        if analysis.weakness_areas:
            st.subheader("⚠️ 薄弱知识点")
            
            for weakness in analysis.weakness_areas:
                st.warning(f"**{weakness.area_name}**: {weakness.description}")
                st.write(f"平均得分率: {weakness.average_score:.1f}%")
                st.write("建议措施:")
                for action in weakness.recommended_actions:
                    st.write(f"- {action}")
    
    def _display_comparison_analysis(self, analysis: DetailedAnalysis):
        """显示对比分析结果"""
        if not analysis.comparison_data:
            st.error("对比数据不完整")
            return
        
        comparison = analysis.comparison_data
        students = comparison.student_results
        
        # 基本对比表格
        st.subheader("📊 基本信息对比")
        
        comparison_df = pd.DataFrame([
            {
                "学生姓名": student.student_name,
                "总分": f"{student.total_score:.1f}",
                "得分率": f"{student.percentage:.1f}%",
                "班级排名": student.rank,
                "相对表现": comparison.relative_performance.get(student.student_id, "")
            }
            for student in students
        ])
        
        st.dataframe(comparison_df, use_container_width=True)
        
        # 对比图表
        st.subheader("📈 可视化对比")
        
        # 总分对比柱状图
        fig_bar = px.bar(
            x=[s.student_name for s in students],
            y=[s.percentage for s in students],
            title="得分率对比",
            labels={'x': '学生', 'y': '得分率(%)'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # 各项得分对比雷达图
        if students and students[0].score_breakdown:
            categories = [sb.criterion_name for sb in students[0].score_breakdown]
            
            fig_radar = go.Figure()
            
            for student in students:
                scores = [sb.percentage for sb in student.score_breakdown]
                fig_radar.add_trace(go.Scatterpolar(
                    r=scores,
                    theta=categories,
                    fill='toself',
                    name=student.student_name
                ))
            
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )),
                showlegend=True,
                title="各项得分对比雷达图"
            )
            
            st.plotly_chart(fig_radar, use_container_width=True)
    
    def _display_class_statistics(self, class_stats: ClassStatistics, student_results: List[StudentResult]):
        """显示班级统计结果"""
        # 基本统计信息
        st.subheader("📊 班级基本统计")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("班级人数", class_stats.total_students)
        
        with col2:
            st.metric("平均分", f"{class_stats.average_score:.1f}")
        
        with col3:
            st.metric("最高分", f"{class_stats.highest_score:.1f}")
        
        with col4:
            st.metric("最低分", f"{class_stats.lowest_score:.1f}")
        
        # 分数分布
        st.subheader("📈 分数分布")
        
        # 分数段分布饼图
        fig_pie = px.pie(
            values=list(class_stats.score_distribution.values()),
            names=list(class_stats.score_distribution.keys()),
            title="分数段分布"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # 分数分布直方图
        scores = [result.percentage for result in student_results]
        fig_hist = px.histogram(
            x=scores,
            nbins=10,
            title="分数分布直方图",
            labels={'x': '得分率(%)', 'y': '人数'}
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # 共同优势和薄弱点
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("✅ 班级优势")
            if class_stats.common_strengths:
                for strength in class_stats.common_strengths:
                    st.success(strength)
            else:
                st.info("暂无明显优势项目")
        
        with col2:
            st.subheader("⚠️ 需要改进")
            if class_stats.common_weaknesses:
                for weakness in class_stats.common_weaknesses:
                    st.warning(weakness)
            else:
                st.info("各项表现均衡")
    
    def _display_trend_analysis(self, analysis: DetailedAnalysis):
        """显示趋势分析结果"""
        if not analysis.trend_analysis:
            st.error("趋势数据不完整")
            return
        
        trend = analysis.trend_analysis
        
        # 趋势概述
        st.subheader(f"📈 {trend.student_name} 的学习趋势")
        
        trend_emoji = {
            "improving": "📈",
            "declining": "📉",
            "stable": "➡️"
        }.get(trend.overall_trend, "❓")
        
        st.info(f"{trend_emoji} {trend.trend_description}")
        
        # 趋势图表
        if trend.trend_points:
            dates = [point.date.strftime("%m-%d") for point in trend.trend_points]
            scores = [point.percentage for point in trend.trend_points]
            assignments = [point.assignment_title for point in trend.trend_points]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=dates,
                y=scores,
                mode='lines+markers',
                name='得分率',
                text=assignments,
                hovertemplate='<b>%{text}</b><br>日期: %{x}<br>得分率: %{y:.1f}%<extra></extra>'
            ))
            
            fig.update_layout(
                title="成绩趋势图",
                xaxis_title="日期",
                yaxis_title="得分率(%)",
                hovermode='closest'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 趋势数据表格
            trend_df = pd.DataFrame([
                {
                    "日期": point.date.strftime("%Y-%m-%d"),
                    "作业": point.assignment_title,
                    "得分率": f"{point.percentage:.1f}%",
                    "班级排名": point.rank
                }
                for point in trend.trend_points
            ])
            
            st.dataframe(trend_df, use_container_width=True)
        
        # 性能洞察
        if trend.performance_insights:
            st.subheader("💡 性能洞察")
            for insight in trend.performance_insights:
                st.write(f"• {insight}")
    
    def _create_mock_student_result(self, student_name: str, assignment_name: str, index: int = 0) -> StudentResult:
        """创建模拟学生结果数据"""
        import random
        
        # 模拟得分细分
        score_breakdown = [
            {
                "criterion_id": "content",
                "criterion_name": "内容准确性",
                "score": 18 + random.uniform(-3, 3),
                "max_score": 25,
                "feedback": "内容基本准确，但部分细节需要完善"
            },
            {
                "criterion_id": "language",
                "criterion_name": "语言表达",
                "score": 20 + random.uniform(-4, 4),
                "max_score": 25,
                "feedback": "语言表达流畅，词汇运用恰当"
            },
            {
                "criterion_id": "structure",
                "criterion_name": "结构逻辑",
                "score": 16 + random.uniform(-2, 4),
                "max_score": 20,
                "feedback": "结构清晰，逻辑性较强"
            },
            {
                "criterion_id": "creativity",
                "criterion_name": "创新性",
                "score": 7 + random.uniform(-2, 3),
                "max_score": 10,
                "feedback": "有一定创新思维，可进一步发挥"
            }
        ]
        
        # 调整分数以产生差异
        for sb in score_breakdown:
            sb["score"] += index * random.uniform(-2, 2)
            sb["score"] = max(0, min(sb["score"], sb["max_score"]))
            sb["percentage"] = (sb["score"] / sb["max_score"]) * 100
        
        total_score = sum(sb["score"] for sb in score_breakdown)
        max_score = sum(sb["max_score"] for sb in score_breakdown)
        percentage = (total_score / max_score) * 100
        
        from src.models.analysis import ScoreBreakdown
        
        return StudentResult(
            student_id=f"student_{index:03d}",
            student_name=student_name,
            assignment_id="assignment_001",
            assignment_title=assignment_name,
            total_score=total_score,
            max_score=max_score,
            percentage=percentage,
            rank=index + 1,
            class_size=30,
            score_breakdown=[
                ScoreBreakdown(
                    criterion_id=sb["criterion_id"],
                    criterion_name=sb["criterion_name"],
                    score=sb["score"],
                    max_score=sb["max_score"],
                    percentage=sb["percentage"],
                    feedback=sb["feedback"]
                )
                for sb in score_breakdown
            ],
            overall_feedback=f"{student_name}在{assignment_name}中表现良好，继续保持！"
        )
    
    def _create_mock_class_statistics(self, assignment_name: str) -> ClassStatistics:
        """创建模拟班级统计数据"""
        return ClassStatistics(
            class_id="class_001",
            class_name="高一(1)班",
            assignment_id="assignment_001",
            assignment_title=assignment_name,
            total_students=30,
            submitted_count=30,
            graded_count=30,
            average_score=75.5,
            median_score=76.0,
            highest_score=92.5,
            lowest_score=58.0,
            standard_deviation=8.2
        )
    
    def _create_mock_class_results(self, class_name: str, assignment_name: str) -> List[StudentResult]:
        """创建模拟班级结果数据"""
        students = [f"学生{i:02d}" for i in range(1, 31)]
        return [
            self._create_mock_student_result(name, assignment_name, i)
            for i, name in enumerate(students)
        ]
    
    def _create_mock_historical_results(self, student_name: str, time_period: str) -> List[StudentResult]:
        """创建模拟历史结果数据"""
        import random
        from datetime import datetime, timedelta
        
        assignments = [
            "数学第一次月考", "数学第二次月考", "数学期中考试",
            "数学第三次月考", "数学第四次月考", "数学期末考试"
        ]
        
        count = {
            "最近3次作业": 3,
            "最近5次作业": 5,
            "本学期全部": 6,
            "本学年全部": 6
        }.get(time_period, 3)
        
        results = []
        base_score = 75
        
        for i in range(count):
            # 模拟成绩趋势
            trend_factor = random.uniform(-5, 5)
            score_variation = random.uniform(-8, 8)
            
            result = self._create_mock_student_result(
                student_name, 
                assignments[i % len(assignments)], 
                0
            )
            
            # 调整分数以显示趋势
            adjustment = (base_score + trend_factor * i + score_variation) / result.percentage
            result.total_score *= adjustment
            result.percentage = (result.total_score / result.max_score) * 100
            result.grading_time = datetime.now() - timedelta(days=(count - i) * 15)
            
            results.append(result)
        
        return results