#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批改仪表板组件
提供班级批改情况的可视化分析界面
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from src.models.assignment import Assignment
from src.models.submission import Submission, SubmissionStatus
from src.services.assignment_service import AssignmentService
from src.services.submission_service import SubmissionService
from src.infrastructure.logging import get_logger


class GradingDashboard:
    """批改仪表板组件"""
    
    def __init__(self, assignment_service: AssignmentService, 
                 submission_service: SubmissionService):
        self.assignment_service = assignment_service
        self.submission_service = submission_service
        self.logger = get_logger(f"{__name__}.GradingDashboard")
    
    def render_class_overview(self, class_id: int, teacher_username: str = None):
        """显示班级整体情况"""
        st.markdown(f"## 📊 班级 {class_id} 整体情况")
        
        try:
            # 获取班级作业列表
            assignments = self.assignment_service.get_class_assignments(class_id)
            
            if not assignments:
                st.info("该班级暂无作业")
                return
            
            # 计算整体统计
            total_assignments = len(assignments)
            active_assignments = len([a for a in assignments if a.is_active])
            total_submissions = sum(a.submission_count for a in assignments)
            total_graded = sum(a.graded_count for a in assignments)
            
            # 基本统计卡片
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("总作业数", total_assignments)
            
            with col2:
                st.metric("活跃作业", active_assignments)
            
            with col3:
                st.metric("总提交数", total_submissions)
            
            with col4:
                grading_rate = (total_graded / total_submissions * 100) if total_submissions > 0 else 0
                st.metric("批改完成率", f"{grading_rate:.1f}%")
            
            # 作业完成情况图表
            self._render_class_completion_chart(assignments)
            
            # 最近活动
            self._render_recent_activities(class_id)
            
            # 学生表现概览
            self._render_student_performance_overview(class_id)
            
        except Exception as e:
            self.logger.error(f"渲染班级概览失败: {e}")
            st.error("获取班级数据失败")
    
    def render_assignment_statistics(self, assignment_id: int):
        """显示作业统计数据"""
        try:
            assignment = self.assignment_service.get_assignment_by_id(assignment_id)
            if not assignment:
                st.error("作业不存在")
                return
            
            st.markdown(f"## 📈 作业统计 - {assignment.title}")
            
            # 获取详细统计
            stats = self.assignment_service.get_assignment_statistics(assignment_id)
            
            # 基本统计指标
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("班级人数", stats.get('total_students', 0))
            
            with col2:
                st.metric("提交人数", stats.get('total_submissions', 0))
            
            with col3:
                st.metric("提交率", f"{stats.get('submission_rate', 0):.1f}%")
            
            with col4:
                st.metric("平均分", f"{stats.get('average_score', 0):.1f}" if stats.get('average_score') else "暂无")
            
            # 详细统计图表
            col1, col2 = st.columns(2)
            
            with col1:
                # 提交状态分布饼图
                self._render_submission_status_pie(stats)
            
            with col2:
                # 分数分布直方图
                self._render_score_distribution(assignment_id)
            
            # 时间趋势分析
            self._render_submission_timeline(assignment_id)
            
            # 详细数据表格
            self._render_assignment_details_table(assignment_id)
            
        except Exception as e:
            self.logger.error(f"渲染作业统计失败: {e}")
            st.error("获取作业统计失败")
    
    def render_grading_progress(self, assignment_id: int = None, class_id: int = None):
        """显示批改进度和状态"""
        st.markdown("## 🔄 批改进度监控")
        
        try:
            if assignment_id:
                # 单个作业的批改进度
                self._render_single_assignment_progress(assignment_id)
            elif class_id:
                # 班级所有作业的批改进度
                self._render_class_grading_progress(class_id)
            else:
                # 全局批改进度
                self._render_global_grading_progress()
            
        except Exception as e:
            self.logger.error(f"渲染批改进度失败: {e}")
            st.error("获取批改进度失败")
    
    def render_student_performance_analysis(self, class_id: int, assignment_id: int = None):
        """分析学生表现"""
        st.markdown("## 👥 学生表现分析")
        
        try:
            if assignment_id:
                # 单个作业的学生表现
                self._render_assignment_student_analysis(assignment_id)
            else:
                # 班级整体学生表现
                self._render_class_student_analysis(class_id)
            
        except Exception as e:
            self.logger.error(f"渲染学生表现分析失败: {e}")
            st.error("获取学生表现数据失败")
    
    def _render_class_completion_chart(self, assignments: List[Assignment]):
        """渲染班级完成情况图表"""
        st.markdown("### 📊 作业完成情况")
        
        # 准备数据
        chart_data = []
        for assignment in assignments:
            completion_rate = (assignment.graded_count / assignment.submission_count * 100) if assignment.submission_count > 0 else 0
            chart_data.append({
                "作业": assignment.title[:20] + "..." if len(assignment.title) > 20 else assignment.title,
                "提交数": assignment.submission_count,
                "已批改": assignment.graded_count,
                "完成率": completion_rate,
                "状态": "活跃" if assignment.is_active else "已停用"
            })
        
        if chart_data:
            df = pd.DataFrame(chart_data)
            
            # 创建双轴图表
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 添加柱状图（提交数和已批改数）
            fig.add_trace(
                go.Bar(name="提交数", x=df["作业"], y=df["提交数"], marker_color="lightblue"),
                secondary_y=False,
            )
            
            fig.add_trace(
                go.Bar(name="已批改", x=df["作业"], y=df["已批改"], marker_color="darkblue"),
                secondary_y=False,
            )
            
            # 添加完成率折线图
            fig.add_trace(
                go.Scatter(name="完成率", x=df["作业"], y=df["完成率"], 
                          mode="lines+markers", marker_color="red"),
                secondary_y=True,
            )
            
            # 设置坐标轴标题
            fig.update_xaxes(title_text="作业")
            fig.update_yaxes(title_text="数量", secondary_y=False)
            fig.update_yaxes(title_text="完成率 (%)", secondary_y=True)
            
            fig.update_layout(title="作业完成情况统计", height=400)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 数据表格
            st.dataframe(df, use_container_width=True)
    
    def _render_recent_activities(self, class_id: int):
        """渲染最近活动"""
        st.markdown("### 📅 最近活动")
        
        try:
            # 获取最近的提交（简化处理）
            recent_submissions = []
            assignments = self.assignment_service.get_class_assignments(class_id)
            
            for assignment in assignments[:5]:  # 只显示最近5个作业的活动
                submissions = self.submission_service.get_assignment_submissions(assignment.id)
                recent_submissions.extend(submissions[:3])  # 每个作业最多3个最近提交
            
            # 按时间排序
            recent_submissions.sort(key=lambda x: x.submitted_at or datetime.min, reverse=True)
            recent_submissions = recent_submissions[:10]  # 只显示最近10个活动
            
            if recent_submissions:
                for submission in recent_submissions:
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 1])
                        
                        with col1:
                            student_name = getattr(submission, 'student_real_name', submission.student_username)
                            st.write(f"👤 {student_name}")
                        
                        with col2:
                            assignment_title = getattr(submission, 'assignment_title', f"作业{submission.assignment_id}")
                            st.write(f"📝 {assignment_title}")
                        
                        with col3:
                            if submission.submitted_at:
                                time_ago = datetime.now() - submission.submitted_at
                                if time_ago.days > 0:
                                    st.write(f"{time_ago.days}天前")
                                elif time_ago.seconds > 3600:
                                    st.write(f"{time_ago.seconds // 3600}小时前")
                                else:
                                    st.write(f"{time_ago.seconds // 60}分钟前")
                        
                        st.markdown("---")
            else:
                st.info("暂无最近活动")
                
        except Exception as e:
            self.logger.error(f"获取最近活动失败: {e}")
            st.error("获取最近活动失败")
    
    def _render_student_performance_overview(self, class_id: int):
        """渲染学生表现概览"""
        st.markdown("### 🎯 学生表现概览")
        
        try:
            # 获取班级所有作业的提交统计
            assignments = self.assignment_service.get_class_assignments(class_id)
            
            if not assignments:
                st.info("暂无数据")
                return
            
            # 统计学生表现数据
            student_stats = {}
            
            for assignment in assignments:
                submissions = self.submission_service.get_assignment_submissions(assignment.id)
                
                for submission in submissions:
                    student_name = getattr(submission, 'student_real_name', submission.student_username)
                    
                    if student_name not in student_stats:
                        student_stats[student_name] = {
                            'total_submissions': 0,
                            'total_score': 0,
                            'graded_count': 0,
                            'avg_score': 0
                        }
                    
                    student_stats[student_name]['total_submissions'] += 1
                    
                    if submission.score is not None:
                        student_stats[student_name]['total_score'] += submission.score
                        student_stats[student_name]['graded_count'] += 1
            
            # 计算平均分
            for student_name, stats in student_stats.items():
                if stats['graded_count'] > 0:
                    stats['avg_score'] = stats['total_score'] / stats['graded_count']
            
            # 创建表现排行榜
            if student_stats:
                performance_data = []
                for student_name, stats in student_stats.items():
                    performance_data.append({
                        "学生": student_name,
                        "提交数": stats['total_submissions'],
                        "已评分": stats['graded_count'],
                        "平均分": f"{stats['avg_score']:.1f}" if stats['avg_score'] > 0 else "暂无"
                    })
                
                # 按平均分排序
                performance_data.sort(key=lambda x: float(x['平均分']) if x['平均分'] != '暂无' else 0, reverse=True)
                
                df = pd.DataFrame(performance_data)
                st.dataframe(df, use_container_width=True)
                
                # 平均分分布图
                scores = [float(item['平均分']) for item in performance_data if item['平均分'] != '暂无']
                if scores:
                    fig = px.histogram(x=scores, nbins=10, title="班级平均分分布")
                    fig.update_xaxes(title="平均分")
                    fig.update_yaxes(title="学生人数")
                    st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            self.logger.error(f"渲染学生表现概览失败: {e}")
            st.error("获取学生表现数据失败")
    
    def _render_submission_status_pie(self, stats: Dict[str, Any]):
        """渲染提交状态分布饼图"""
        st.markdown("#### 📊 提交状态分布")
        
        status_data = {
            "待批改": stats.get('pending_submissions', 0),
            "AI已批改": stats.get('ai_graded_submissions', 0),
            "教师已审核": stats.get('teacher_reviewed_submissions', 0),
            "已返回": stats.get('returned_submissions', 0)
        }
        
        # 过滤掉0值
        status_data = {k: v for k, v in status_data.items() if v > 0}
        
        if status_data:
            fig = px.pie(
                values=list(status_data.values()),
                names=list(status_data.keys()),
                title="提交状态分布"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无提交数据")
    
    def _render_score_distribution(self, assignment_id: int):
        """渲染分数分布直方图"""
        st.markdown("#### 📈 分数分布")
        
        try:
            submissions = self.submission_service.get_assignment_submissions(assignment_id)
            scores = [s.score for s in submissions if s.score is not None]
            
            if scores:
                fig = px.histogram(
                    x=scores,
                    nbins=10,
                    title="分数分布直方图",
                    labels={'x': '分数', 'y': '人数'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # 分数统计
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("最高分", f"{max(scores):.1f}")
                
                with col2:
                    st.metric("最低分", f"{min(scores):.1f}")
                
                with col3:
                    st.metric("标准差", f"{pd.Series(scores).std():.1f}")
            else:
                st.info("暂无分数数据")
                
        except Exception as e:
            self.logger.error(f"渲染分数分布失败: {e}")
            st.error("获取分数数据失败")
    
    def _render_submission_timeline(self, assignment_id: int):
        """渲染提交时间线"""
        st.markdown("#### ⏰ 提交时间线")
        
        try:
            submissions = self.submission_service.get_assignment_submissions(assignment_id)
            
            if submissions:
                # 按提交时间分组统计
                timeline_data = {}
                for submission in submissions:
                    if submission.submitted_at:
                        date_key = submission.submitted_at.strftime("%Y-%m-%d")
                        timeline_data[date_key] = timeline_data.get(date_key, 0) + 1
                
                if timeline_data:
                    dates = list(timeline_data.keys())
                    counts = list(timeline_data.values())
                    
                    fig = px.line(
                        x=dates,
                        y=counts,
                        title="每日提交数量趋势",
                        labels={'x': '日期', 'y': '提交数量'}
                    )
                    fig.update_traces(mode='lines+markers')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("暂无时间线数据")
            else:
                st.info("暂无提交数据")
                
        except Exception as e:
            self.logger.error(f"渲染提交时间线失败: {e}")
            st.error("获取时间线数据失败")
    
    def _render_assignment_details_table(self, assignment_id: int):
        """渲染作业详细数据表格"""
        st.markdown("#### 📋 详细数据")
        
        try:
            submissions = self.submission_service.get_assignment_submissions(assignment_id)
            
            if submissions:
                table_data = []
                for submission in submissions:
                    table_data.append({
                        "学生": getattr(submission, 'student_real_name', submission.student_username),
                        "提交时间": submission.submitted_at.strftime("%Y-%m-%d %H:%M") if submission.submitted_at else "",
                        "状态": self._get_status_display(submission.status),
                        "分数": f"{submission.score:.1f}" if submission.score is not None else "未评分",
                        "AI置信度": f"{submission.ai_confidence:.2f}" if submission.ai_confidence else "无",
                        "需要审核": "是" if submission.manual_review_required else "否"
                    })
                
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)
                
                # 导出功能
                if st.button("📊 导出数据"):
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="下载CSV文件",
                        data=csv,
                        file_name=f"assignment_{assignment_id}_data.csv",
                        mime="text/csv"
                    )
            else:
                st.info("暂无详细数据")
                
        except Exception as e:
            self.logger.error(f"渲染详细数据表格失败: {e}")
            st.error("获取详细数据失败")
    
    def _render_single_assignment_progress(self, assignment_id: int):
        """渲染单个作业的批改进度"""
        try:
            assignment = self.assignment_service.get_assignment_by_id(assignment_id)
            if not assignment:
                st.error("作业不存在")
                return
            
            st.markdown(f"### 📝 {assignment.title} - 批改进度")
            
            # 进度指标
            progress = assignment.get_grading_progress()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("总提交数", assignment.submission_count)
            
            with col2:
                st.metric("已批改数", assignment.graded_count)
            
            with col3:
                st.metric("完成率", f"{progress:.1f}%")
            
            # 进度条
            st.progress(progress / 100)
            
            # 批改状态详情
            stats = self.assignment_service.get_assignment_statistics(assignment_id)
            
            status_cols = st.columns(4)
            
            with status_cols[0]:
                st.metric("待批改", stats.get('pending_submissions', 0))
            
            with status_cols[1]:
                st.metric("AI批改", stats.get('ai_graded_submissions', 0))
            
            with status_cols[2]:
                st.metric("教师审核", stats.get('teacher_reviewed_submissions', 0))
            
            with status_cols[3]:
                st.metric("已完成", stats.get('returned_submissions', 0))
            
        except Exception as e:
            self.logger.error(f"渲染单个作业进度失败: {e}")
            st.error("获取作业进度失败")
    
    def _render_class_grading_progress(self, class_id: int):
        """渲染班级批改进度"""
        try:
            assignments = self.assignment_service.get_class_assignments(class_id)
            
            if not assignments:
                st.info("该班级暂无作业")
                return
            
            st.markdown(f"### 📚 班级 {class_id} - 整体批改进度")
            
            # 整体进度统计
            total_submissions = sum(a.submission_count for a in assignments)
            total_graded = sum(a.graded_count for a in assignments)
            overall_progress = (total_graded / total_submissions * 100) if total_submissions > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("总提交数", total_submissions)
            
            with col2:
                st.metric("已批改数", total_graded)
            
            with col3:
                st.metric("整体完成率", f"{overall_progress:.1f}%")
            
            # 整体进度条
            st.progress(overall_progress / 100)
            
            # 各作业进度详情
            st.markdown("#### 📊 各作业进度详情")
            
            progress_data = []
            for assignment in assignments:
                progress = assignment.get_grading_progress()
                progress_data.append({
                    "作业": assignment.title,
                    "提交数": assignment.submission_count,
                    "已批改": assignment.graded_count,
                    "进度": f"{progress:.1f}%",
                    "状态": "活跃" if assignment.is_active else "已停用"
                })
            
            df = pd.DataFrame(progress_data)
            st.dataframe(df, use_container_width=True)
            
        except Exception as e:
            self.logger.error(f"渲染班级批改进度失败: {e}")
            st.error("获取班级进度失败")
    
    def _render_global_grading_progress(self):
        """渲染全局批改进度"""
        st.markdown("### 🌐 全局批改进度")
        st.info("全局进度监控功能开发中...")
    
    def _render_assignment_student_analysis(self, assignment_id: int):
        """渲染单个作业的学生分析"""
        try:
            assignment = self.assignment_service.get_assignment_by_id(assignment_id)
            submissions = self.submission_service.get_assignment_submissions(assignment_id)
            
            st.markdown(f"### 👥 {assignment.title} - 学生表现分析")
            
            if not submissions:
                st.info("暂无提交数据")
                return
            
            # 学生表现排行
            student_data = []
            for submission in submissions:
                student_name = getattr(submission, 'student_real_name', submission.student_username)
                student_data.append({
                    "学生": student_name,
                    "分数": submission.score if submission.score is not None else 0,
                    "状态": self._get_status_display(submission.status),
                    "提交时间": submission.submitted_at.strftime("%m-%d %H:%M") if submission.submitted_at else "",
                    "AI置信度": f"{submission.ai_confidence:.2f}" if submission.ai_confidence else "无"
                })
            
            # 按分数排序
            student_data.sort(key=lambda x: x['分数'], reverse=True)
            
            df = pd.DataFrame(student_data)
            st.dataframe(df, use_container_width=True)
            
            # 表现分析图表
            scores = [item['分数'] for item in student_data if item['分数'] > 0]
            if scores:
                col1, col2 = st.columns(2)
                
                with col1:
                    # 分数分布
                    fig = px.histogram(x=scores, nbins=8, title="分数分布")
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # 排名图
                    fig = px.bar(
                        x=[item['学生'] for item in student_data[:10]],
                        y=[item['分数'] for item in student_data[:10]],
                        title="前10名学生排行"
                    )
                    fig.update_xaxes(tickangle=45)
                    st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            self.logger.error(f"渲染作业学生分析失败: {e}")
            st.error("获取学生分析数据失败")
    
    def _render_class_student_analysis(self, class_id: int):
        """渲染班级学生分析"""
        st.markdown(f"### 👥 班级 {class_id} - 学生表现分析")
        st.info("班级学生分析功能开发中...")
    
    def _get_status_display(self, status: SubmissionStatus) -> str:
        """获取状态显示文本"""
        status_map = {
            SubmissionStatus.SUBMITTED: "已提交",
            SubmissionStatus.AI_GRADED: "AI已批改",
            SubmissionStatus.TEACHER_REVIEWED: "教师已审核",
            SubmissionStatus.RETURNED: "已返回",
            SubmissionStatus.FAILED: "批改失败",
            SubmissionStatus.PENDING_REVIEW: "待审核"
        }
        return status_map.get(status, "未知状态")