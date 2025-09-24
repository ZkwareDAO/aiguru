#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作业中心组件
提供教师和学生的作业管理界面
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from src.models.assignment import Assignment
from src.models.submission import Submission, SubmissionStatus
from src.services.assignment_service import AssignmentService
from src.services.submission_service import SubmissionService
from src.services.classroom_grading_service import ClassroomGradingService
from src.infrastructure.logging import get_logger


class AssignmentCenter:
    """作业中心组件"""
    
    def __init__(self, assignment_service: AssignmentService, 
                 submission_service: SubmissionService,
                 grading_service: Optional[ClassroomGradingService] = None):
        self.assignment_service = assignment_service
        self.submission_service = submission_service
        self.grading_service = grading_service
        self.logger = get_logger(f"{__name__}.AssignmentCenter")
    
    def render_teacher_view(self, teacher_username: str):
        """渲染教师作业管理界面"""
        st.markdown("## 👨‍🏫 教师作业管理")
        
        # 教师摘要信息
        self._render_teacher_summary(teacher_username)
        
        # 选项卡
        tab1, tab2, tab3, tab4 = st.tabs(["📝 创建作业", "📋 作业列表", "📊 提交管理", "📈 统计分析"])
        
        with tab1:
            self._render_assignment_creation_form(teacher_username)
        
        with tab2:
            self._render_teacher_assignment_list(teacher_username)
        
        with tab3:
            self._render_submission_management(teacher_username)
        
        with tab4:
            self._render_teacher_statistics(teacher_username)
    
    def render_student_view(self, student_username: str):
        """渲染学生作业列表界面"""
        st.markdown("## 🎓 学生作业中心")
        
        # 学生摘要信息
        self._render_student_summary(student_username)
        
        # 选项卡
        tab1, tab2, tab3 = st.tabs(["📚 待完成作业", "✅ 已完成作业", "📊 我的成绩"])
        
        with tab1:
            self._render_pending_assignments(student_username)
        
        with tab2:
            self._render_completed_assignments(student_username)
        
        with tab3:
            self._render_student_statistics(student_username)
    
    def _render_teacher_summary(self, teacher_username: str):
        """渲染教师摘要信息"""
        try:
            summary = self.assignment_service.get_teacher_assignment_summary(teacher_username)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("总作业数", summary.get('total_assignments', 0))
            
            with col2:
                st.metric("活跃作业", summary.get('active_assignments', 0))
            
            with col3:
                st.metric("总提交数", summary.get('total_submissions', 0))
            
            with col4:
                st.metric("待批改", summary.get('pending_grading', 0))
            
        except Exception as e:
            self.logger.error(f"获取教师摘要失败: {e}")
            st.error("获取摘要信息失败")
    
    def _render_student_summary(self, student_username: str):
        """渲染学生摘要信息"""
        try:
            # 获取学生的作业统计
            assignments = self.assignment_service.get_student_assignments(student_username)
            
            total_assignments = len(assignments)
            completed_assignments = len([a for a in assignments if hasattr(a, 'submission_status') and a.submission_status])
            pending_assignments = total_assignments - completed_assignments
            
            # 获取最近的成绩
            recent_submissions = self.submission_service.get_submission_history(student_username, limit=5)
            avg_score = sum(s.score for s in recent_submissions if s.score) / len(recent_submissions) if recent_submissions else 0
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("总作业数", total_assignments)
            
            with col2:
                st.metric("已完成", completed_assignments)
            
            with col3:
                st.metric("待完成", pending_assignments)
            
            with col4:
                st.metric("平均分", f"{avg_score:.1f}" if avg_score > 0 else "暂无")
            
        except Exception as e:
            self.logger.error(f"获取学生摘要失败: {e}")
            st.error("获取摘要信息失败")
    
    def render_assignment_creation_form(self, teacher_username: str = None):
        """渲染作业创建表单"""
        st.markdown("### 📝 创建新作业")
        
        with st.form("create_assignment_form"):
            # 基本信息
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("作业标题*", placeholder="例如：第一章练习题")
                class_id = st.number_input("班级ID*", min_value=1, value=1, help="请输入班级ID")
            
            with col2:
                deadline = st.date_input("截止日期", value=datetime.now().date() + timedelta(days=7))
                deadline_time = st.time_input("截止时间", value=datetime.now().time().replace(hour=23, minute=59))
            
            description = st.text_area("作业描述", placeholder="详细描述作业要求和注意事项")
            
            # 文件上传
            st.markdown("#### 📎 文件上传")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**题目文件**")
                question_files = st.file_uploader(
                    "上传题目文件",
                    type=['pdf', 'doc', 'docx', 'txt'],
                    accept_multiple_files=True,
                    key="question_files"
                )
            
            with col2:
                st.markdown("**批改标准文件**")
                marking_files = st.file_uploader(
                    "上传批改标准文件",
                    type=['pdf', 'doc', 'docx', 'txt'],
                    accept_multiple_files=True,
                    key="marking_files"
                )
            
            # 批改设置
            st.markdown("#### ⚙️ 批改设置")
            
            col1, col2 = st.columns(2)
            
            with col1:
                auto_grading_enabled = st.checkbox("启用自动批改", value=True)
                grading_config_id = st.text_input("批改配置ID", placeholder="可选，留空使用默认配置")
            
            with col2:
                grading_template_id = st.text_input("批改模板ID", placeholder="可选，留空使用默认模板")
            
            # 提交按钮
            submitted = st.form_submit_button("🚀 创建作业", type="primary")
            
            if submitted:
                if not title.strip():
                    st.error("请填写作业标题")
                elif not class_id:
                    st.error("请填写班级ID")
                else:
                    self._create_assignment(
                        class_id=class_id,
                        title=title,
                        description=description,
                        question_files=[f.name for f in question_files] if question_files else [],
                        marking_files=[f.name for f in marking_files] if marking_files else [],
                        deadline=datetime.combine(deadline, deadline_time),
                        auto_grading_enabled=auto_grading_enabled,
                        grading_config_id=grading_config_id if grading_config_id.strip() else None,
                        grading_template_id=grading_template_id if grading_template_id.strip() else None
                    )
    
    def _render_assignment_creation_form(self, teacher_username: str):
        """渲染教师的作业创建表单"""
        self.render_assignment_creation_form(teacher_username)
    
    def render_assignment_list(self, assignments: List[Assignment], view_type: str = "teacher"):
        """渲染作业列表"""
        if not assignments:
            st.info("暂无作业")
            return
        
        # 搜索和筛选
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_term = st.text_input("🔍 搜索作业", placeholder="输入作业标题或描述")
        
        with col2:
            status_filter = st.selectbox("状态筛选", ["全部", "活跃", "已过期", "已停用"])
        
        with col3:
            sort_by = st.selectbox("排序方式", ["创建时间", "截止时间", "标题", "提交数"])
        
        # 筛选作业
        filtered_assignments = assignments
        
        if search_term:
            filtered_assignments = [
                a for a in filtered_assignments 
                if search_term.lower() in a.title.lower() or 
                   search_term.lower() in (a.description or "").lower()
            ]
        
        if status_filter == "活跃":
            filtered_assignments = [a for a in filtered_assignments if a.is_active and not a.is_overdue()]
        elif status_filter == "已过期":
            filtered_assignments = [a for a in filtered_assignments if a.is_active and a.is_overdue()]
        elif status_filter == "已停用":
            filtered_assignments = [a for a in filtered_assignments if not a.is_active]
        
        # 排序
        if sort_by == "创建时间":
            filtered_assignments.sort(key=lambda x: x.created_at, reverse=True)
        elif sort_by == "截止时间":
            filtered_assignments.sort(key=lambda x: x.deadline or datetime.max)
        elif sort_by == "标题":
            filtered_assignments.sort(key=lambda x: x.title)
        elif sort_by == "提交数":
            filtered_assignments.sort(key=lambda x: x.submission_count, reverse=True)
        
        # 显示作业卡片
        for assignment in filtered_assignments:
            if view_type == "teacher":
                self._render_teacher_assignment_card(assignment)
            else:
                self._render_student_assignment_card(assignment)
    
    def _render_teacher_assignment_list(self, teacher_username: str):
        """渲染教师作业列表"""
        try:
            # 获取教师的班级
            # 这里简化处理，实际应该从班级服务获取
            assignments = []
            for class_id in [1, 2, 3]:  # 假设教师管理这些班级
                class_assignments = self.assignment_service.get_class_assignments(class_id)
                assignments.extend(class_assignments)
            
            self.render_assignment_list(assignments, "teacher")
            
        except Exception as e:
            self.logger.error(f"获取教师作业列表失败: {e}")
            st.error("获取作业列表失败")
    
    def _render_pending_assignments(self, student_username: str):
        """渲染学生待完成作业"""
        try:
            assignments = self.assignment_service.get_student_assignments(student_username)
            pending_assignments = [
                a for a in assignments 
                if not hasattr(a, 'submission_status') or not a.submission_status
            ]
            
            if not pending_assignments:
                st.success("🎉 太棒了！您已完成所有作业！")
                return
            
            st.markdown(f"### 📚 待完成作业 ({len(pending_assignments)})")
            
            for assignment in pending_assignments:
                self._render_student_assignment_card(assignment, show_submit_button=True)
                
        except Exception as e:
            self.logger.error(f"获取学生待完成作业失败: {e}")
            st.error("获取待完成作业失败")
    
    def _render_completed_assignments(self, student_username: str):
        """渲染学生已完成作业"""
        try:
            assignments = self.assignment_service.get_student_assignments(student_username)
            completed_assignments = [
                a for a in assignments 
                if hasattr(a, 'submission_status') and a.submission_status
            ]
            
            if not completed_assignments:
                st.info("暂无已完成的作业")
                return
            
            st.markdown(f"### ✅ 已完成作业 ({len(completed_assignments)})")
            
            for assignment in completed_assignments:
                self._render_student_assignment_card(assignment, show_results=True)
                
        except Exception as e:
            self.logger.error(f"获取学生已完成作业失败: {e}")
            st.error("获取已完成作业失败")
    
    def _render_teacher_assignment_card(self, assignment: Assignment):
        """渲染教师作业卡片"""
        with st.container():
            # 状态指示器
            status_color = "🟢" if assignment.is_active and not assignment.is_overdue() else "🔴" if assignment.is_overdue() else "⚪"
            
            col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
            
            with col1:
                st.markdown(f"**{status_color} {assignment.title}**")
                if assignment.description:
                    st.write(assignment.description[:100] + "..." if len(assignment.description) > 100 else assignment.description)
                
                # 时间信息
                created_time = assignment.created_at.strftime("%Y-%m-%d %H:%M")
                deadline_time = assignment.deadline.strftime("%Y-%m-%d %H:%M") if assignment.deadline else "无截止时间"
                st.caption(f"创建: {created_time} | 截止: {deadline_time}")
            
            with col2:
                st.metric("提交数", f"{assignment.submission_count}")
                st.metric("已批改", f"{assignment.graded_count}")
            
            with col3:
                completion_rate = (assignment.graded_count / assignment.submission_count * 100) if assignment.submission_count > 0 else 0
                st.metric("完成率", f"{completion_rate:.1f}%")
                
                if assignment.auto_grading_enabled:
                    st.success("🤖 自动批改")
                else:
                    st.info("👨‍🏫 手动批改")
            
            with col4:
                col_view, col_edit, col_stats = st.columns(3)
                
                with col_view:
                    if st.button("👀", key=f"view_assignment_{assignment.id}", help="查看详情"):
                        self._view_assignment_details(assignment)
                
                with col_edit:
                    if st.button("✏️", key=f"edit_assignment_{assignment.id}", help="编辑"):
                        self._edit_assignment(assignment)
                
                with col_stats:
                    if st.button("📊", key=f"stats_assignment_{assignment.id}", help="统计"):
                        self._show_assignment_statistics(assignment)
            
            # 详细信息展开
            with st.expander(f"详情 - {assignment.title}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**基本信息**:")
                    st.write(f"- 班级ID: {assignment.class_id}")
                    st.write(f"- 创建时间: {assignment.created_at.strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"- 截止时间: {assignment.deadline.strftime('%Y-%m-%d %H:%M') if assignment.deadline else '无'}")
                    st.write(f"- 状态: {'活跃' if assignment.is_active else '已停用'}")
                
                with col2:
                    st.write("**批改设置**:")
                    st.write(f"- 自动批改: {'启用' if assignment.auto_grading_enabled else '禁用'}")
                    st.write(f"- 配置ID: {assignment.grading_config_id or '默认'}")
                    st.write(f"- 模板ID: {assignment.grading_template_id or '默认'}")
                
                if assignment.question_files:
                    st.write("**题目文件**:")
                    for file in assignment.question_files:
                        st.write(f"- {file}")
                
                if assignment.marking_files:
                    st.write("**批改标准文件**:")
                    for file in assignment.marking_files:
                        st.write(f"- {file}")
        
        st.markdown("---")
    
    def _render_student_assignment_card(self, assignment: Assignment, show_submit_button: bool = False, show_results: bool = False):
        """渲染学生作业卡片"""
        with st.container():
            # 状态指示器
            if hasattr(assignment, 'submission_status'):
                if assignment.submission_status == 'returned':
                    status_color = "🟢"
                    status_text = "已批改"
                elif assignment.submission_status in ['submitted', 'ai_graded', 'teacher_reviewed']:
                    status_color = "🟡"
                    status_text = "批改中"
                else:
                    status_color = "⚪"
                    status_text = "未提交"
            else:
                status_color = "🔴"
                status_text = "待提交"
            
            col1, col2, col3 = st.columns([3, 1, 2])
            
            with col1:
                st.markdown(f"**{status_color} {assignment.title}**")
                if assignment.description:
                    st.write(assignment.description[:100] + "..." if len(assignment.description) > 100 else assignment.description)
                
                # 时间信息
                if assignment.deadline:
                    deadline_str = assignment.deadline.strftime("%Y-%m-%d %H:%M")
                    is_overdue = assignment.is_overdue()
                    if is_overdue:
                        st.error(f"⏰ 截止时间: {deadline_str} (已过期)")
                    else:
                        time_left = assignment.deadline - datetime.now()
                        if time_left.days > 0:
                            st.info(f"⏰ 截止时间: {deadline_str} (还有{time_left.days}天)")
                        else:
                            st.warning(f"⏰ 截止时间: {deadline_str} (今天截止)")
                else:
                    st.info("⏰ 无截止时间")
            
            with col2:
                st.write(f"**状态**: {status_text}")
                if hasattr(assignment, 'class_name'):
                    st.write(f"**班级**: {assignment.class_name}")
                
                if show_results and hasattr(assignment, 'submission_score') and assignment.submission_score:
                    st.metric("得分", f"{assignment.submission_score:.1f}")
            
            with col3:
                if show_submit_button:
                    if st.button("📤 提交作业", key=f"submit_{assignment.id}", type="primary"):
                        self._show_submission_form(assignment)
                
                if show_results:
                    if st.button("📊 查看结果", key=f"view_result_{assignment.id}"):
                        self._show_submission_results(assignment)
                
                if st.button("👀 查看详情", key=f"view_detail_{assignment.id}"):
                    self._view_assignment_details(assignment)
            
            # 详细信息展开
            with st.expander(f"作业详情 - {assignment.title}", expanded=False):
                if assignment.description:
                    st.write("**作业描述**:")
                    st.write(assignment.description)
                
                if assignment.question_files:
                    st.write("**题目文件**:")
                    for file in assignment.question_files:
                        st.write(f"- 📎 {file}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**基本信息**:")
                    st.write(f"- 发布时间: {assignment.created_at.strftime('%Y-%m-%d %H:%M')}")
                    if assignment.deadline:
                        st.write(f"- 截止时间: {assignment.deadline.strftime('%Y-%m-%d %H:%M')}")
                
                with col2:
                    if hasattr(assignment, 'submitted_at') and assignment.submitted_at:
                        st.write("**提交信息**:")
                        st.write(f"- 提交时间: {assignment.submitted_at}")
                        if hasattr(assignment, 'graded_at') and assignment.graded_at:
                            st.write(f"- 批改时间: {assignment.graded_at}")
        
        st.markdown("---")
    
    def render_submission_management(self, teacher_username: str = None):
        """渲染提交管理界面"""
        st.markdown("### 📊 提交管理")
        
        # 筛选选项
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox(
                "状态筛选",
                ["全部", "待批改", "已批改", "需要审核", "已返回"],
                key="submission_status_filter"
            )
        
        with col2:
            assignment_filter = st.selectbox(
                "作业筛选",
                ["全部作业"] + self._get_teacher_assignment_titles(teacher_username),
                key="submission_assignment_filter"
            )
        
        with col3:
            sort_by = st.selectbox(
                "排序方式",
                ["提交时间", "学生姓名", "分数", "状态"],
                key="submission_sort_by"
            )
        
        try:
            # 获取提交列表
            submissions = self._get_filtered_submissions(teacher_username, status_filter, assignment_filter, sort_by)
            
            if not submissions:
                st.info("暂无符合条件的提交")
                return
            
            # 批量操作
            st.markdown("#### 批量操作")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🚀 批量批改", help="对选中的提交进行批量批改"):
                    self._batch_grade_submissions(submissions)
            
            with col2:
                if st.button("📧 批量通知", help="向学生发送批量通知"):
                    self._batch_notify_students(submissions)
            
            with col3:
                if st.button("📊 导出数据", help="导出提交数据"):
                    self._export_submissions_data(submissions)
            
            # 提交列表
            st.markdown("#### 提交列表")
            self._render_submissions_table(submissions)
            
        except Exception as e:
            self.logger.error(f"渲染提交管理失败: {e}")
            st.error("获取提交数据失败")
    
    def _render_submissions_table(self, submissions: List[Submission]):
        """渲染提交表格"""
        if not submissions:
            return
        
        # 创建表格数据
        table_data = []
        for submission in submissions:
            table_data.append({
                "学生": getattr(submission, 'student_real_name', submission.student_username),
                "作业": getattr(submission, 'assignment_title', f"作业{submission.assignment_id}"),
                "提交时间": submission.submitted_at.strftime("%Y-%m-%d %H:%M") if submission.submitted_at else "",
                "状态": self._get_status_display(submission.status),
                "分数": f"{submission.score:.1f}" if submission.score else "未评分",
                "操作": submission.id
            })
        
        df = pd.DataFrame(table_data)
        
        # 使用streamlit的数据编辑器
        edited_df = st.data_editor(
            df,
            column_config={
                "操作": st.column_config.Column(
                    "操作",
                    width="small",
                ),
            },
            disabled=["学生", "作业", "提交时间", "状态"],
            hide_index=True,
            use_container_width=True
        )
        
        # 为每个提交添加操作按钮
        for i, submission in enumerate(submissions):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("👀 查看", key=f"view_submission_{submission.id}"):
                    self._view_submission_details(submission)
            
            with col2:
                if st.button("✏️ 批改", key=f"grade_submission_{submission.id}"):
                    self._grade_submission(submission)
            
            with col3:
                if st.button("💬 反馈", key=f"feedback_submission_{submission.id}"):
                    self._provide_feedback(submission)
            
            with col4:
                if st.button("📧 通知", key=f"notify_submission_{submission.id}"):
                    self._notify_student(submission)
    
    def _render_teacher_statistics(self, teacher_username: str):
        """渲染教师统计分析"""
        st.markdown("### 📈 统计分析")
        
        try:
            # 获取统计数据
            summary = self.assignment_service.get_teacher_assignment_summary(teacher_username)
            
            # 基本统计
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("总作业数", summary.get('total_assignments', 0))
            
            with col2:
                st.metric("总提交数", summary.get('total_submissions', 0))
            
            with col3:
                completion_rate = (summary.get('total_submissions', 0) / max(summary.get('total_assignments', 1), 1)) * 100
                st.metric("完成率", f"{completion_rate:.1f}%")
            
            with col4:
                grading_rate = ((summary.get('total_submissions', 0) - summary.get('pending_grading', 0)) / max(summary.get('total_submissions', 1), 1)) * 100
                st.metric("批改率", f"{grading_rate:.1f}%")
            
            # 详细图表
            self._render_teacher_charts(teacher_username)
            
        except Exception as e:
            self.logger.error(f"渲染教师统计失败: {e}")
            st.error("获取统计数据失败")
    
    def _render_student_statistics(self, student_username: str):
        """渲染学生统计分析"""
        st.markdown("### 📊 我的成绩统计")
        
        try:
            # 获取学生提交历史
            submissions = self.submission_service.get_submission_history(student_username, limit=20)
            
            if not submissions:
                st.info("暂无成绩记录")
                return
            
            # 基本统计
            total_submissions = len(submissions)
            graded_submissions = [s for s in submissions if s.score is not None]
            avg_score = sum(s.score for s in graded_submissions) / len(graded_submissions) if graded_submissions else 0
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("总提交数", total_submissions)
            
            with col2:
                st.metric("已评分", len(graded_submissions))
            
            with col3:
                st.metric("平均分", f"{avg_score:.1f}")
            
            with col4:
                if graded_submissions:
                    latest_score = graded_submissions[0].score
                    st.metric("最新得分", f"{latest_score:.1f}")
            
            # 成绩趋势图
            self._render_student_charts(submissions)
            
        except Exception as e:
            self.logger.error(f"渲染学生统计失败: {e}")
            st.error("获取统计数据失败")
    
    def _create_assignment(self, **kwargs):
        """创建作业"""
        try:
            assignment_id = self.assignment_service.create_assignment(**kwargs)
            
            if assignment_id:
                st.success(f"✅ 作业创建成功！作业ID: {assignment_id}")
                st.balloons()
                
                # 清空表单
                for key in st.session_state.keys():
                    if key.startswith(('question_files', 'marking_files')):
                        del st.session_state[key]
                
                st.rerun()
            else:
                st.error("❌ 作业创建失败，请检查输入信息")
                
        except Exception as e:
            self.logger.error(f"创建作业失败: {e}")
            st.error(f"创建作业失败: {e}")
    
    def _view_assignment_details(self, assignment: Assignment):
        """查看作业详情"""
        with st.expander(f"📋 作业详情 - {assignment.title}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**基本信息**")
                st.write(f"- 作业ID: {assignment.id}")
                st.write(f"- 标题: {assignment.title}")
                st.write(f"- 班级ID: {assignment.class_id}")
                st.write(f"- 创建时间: {assignment.created_at.strftime('%Y-%m-%d %H:%M')}")
                st.write(f"- 截止时间: {assignment.deadline.strftime('%Y-%m-%d %H:%M') if assignment.deadline else '无'}")
                st.write(f"- 状态: {'活跃' if assignment.is_active else '已停用'}")
            
            with col2:
                st.write("**统计信息**")
                st.write(f"- 提交数: {assignment.submission_count}")
                st.write(f"- 已批改: {assignment.graded_count}")
                st.write(f"- 自动批改: {'启用' if assignment.auto_grading_enabled else '禁用'}")
                st.write(f"- 配置ID: {assignment.grading_config_id or '默认'}")
            
            if assignment.description:
                st.write("**作业描述**")
                st.write(assignment.description)
            
            if assignment.question_files:
                st.write("**题目文件**")
                for file in assignment.question_files:
                    st.write(f"- 📎 {file}")
            
            if assignment.marking_files:
                st.write("**批改标准文件**")
                for file in assignment.marking_files:
                    st.write(f"- 📎 {file}")
    
    def _edit_assignment(self, assignment: Assignment):
        """编辑作业"""
        st.info("编辑功能开发中...")
    
    def _show_assignment_statistics(self, assignment: Assignment):
        """显示作业统计"""
        try:
            stats = self.assignment_service.get_assignment_statistics(assignment.id)
            
            with st.expander(f"📊 统计数据 - {assignment.title}", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("总学生数", stats.get('total_students', 0))
                
                with col2:
                    st.metric("提交数", stats.get('total_submissions', 0))
                
                with col3:
                    st.metric("提交率", f"{stats.get('submission_rate', 0):.1f}%")
                
                with col4:
                    st.metric("平均分", f"{stats.get('average_score', 0):.1f}" if stats.get('average_score') else "暂无")
                
                # 详细统计
                st.write("**详细统计**")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"- 待批改: {stats.get('pending_submissions', 0)}")
                    st.write(f"- AI批改: {stats.get('ai_graded_submissions', 0)}")
                    st.write(f"- 教师审核: {stats.get('teacher_reviewed_submissions', 0)}")
                
                with col2:
                    st.write(f"- 已返回: {stats.get('returned_submissions', 0)}")
                    st.write(f"- 最高分: {stats.get('max_score', 0)}")
                    st.write(f"- 最低分: {stats.get('min_score', 0)}")
                
        except Exception as e:
            self.logger.error(f"获取作业统计失败: {e}")
            st.error("获取统计数据失败")
    
    def _show_submission_form(self, assignment: Assignment):
        """显示提交表单"""
        with st.expander(f"📤 提交作业 - {assignment.title}", expanded=True):
            st.write("**作业要求**")
            if assignment.description:
                st.write(assignment.description)
            
            if assignment.question_files:
                st.write("**题目文件**")
                for file in assignment.question_files:
                    st.write(f"- 📎 {file}")
            
            st.write("**上传答案**")
            answer_files = st.file_uploader(
                "选择答案文件",
                type=['pdf', 'doc', 'docx', 'txt', 'jpg', 'png'],
                accept_multiple_files=True,
                key=f"answer_files_{assignment.id}"
            )
            
            if st.button(f"提交作业", key=f"submit_assignment_{assignment.id}", type="primary"):
                if answer_files:
                    # 这里应该保存文件并调用提交服务
                    file_names = [f.name for f in answer_files]
                    
                    # 获取当前用户（这里简化处理）
                    student_username = st.session_state.get('current_user', 'test_student')
                    
                    success = self.submission_service.submit_assignment(
                        assignment.id,
                        student_username,
                        file_names
                    )
                    
                    if success:
                        st.success("✅ 作业提交成功！")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ 作业提交失败")
                else:
                    st.error("请选择要提交的文件")
    
    def _show_submission_results(self, assignment: Assignment):
        """显示提交结果"""
        try:
            # 获取当前用户（这里简化处理）
            student_username = st.session_state.get('current_user', 'test_student')
            
            submission = self.submission_service.get_submission(assignment.id, student_username)
            
            if not submission:
                st.error("未找到提交记录")
                return
            
            with st.expander(f"📊 批改结果 - {assignment.title}", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if submission.score is not None:
                        st.metric("得分", f"{submission.score:.1f}")
                    else:
                        st.info("尚未评分")
                
                with col2:
                    st.write(f"**状态**: {self._get_status_display(submission.status)}")
                
                with col3:
                    if submission.graded_at:
                        st.write(f"**批改时间**: {submission.graded_at.strftime('%Y-%m-%d %H:%M')}")
                
                if submission.ai_result:
                    st.write("**AI批改反馈**")
                    st.write(submission.ai_result)
                
                if submission.teacher_feedback:
                    st.write("**教师反馈**")
                    st.write(submission.teacher_feedback)
                
                if submission.answer_files:
                    st.write("**提交的文件**")
                    for file in submission.answer_files:
                        st.write(f"- 📎 {file}")
                
        except Exception as e:
            self.logger.error(f"显示提交结果失败: {e}")
            st.error("获取提交结果失败")
    
    def _get_teacher_assignment_titles(self, teacher_username: str) -> List[str]:
        """获取教师的作业标题列表"""
        try:
            # 简化处理，实际应该从数据库获取
            return ["数学第一章练习", "数学第二章练习", "期中考试", "期末考试"]
        except:
            return []
    
    def _get_filtered_submissions(self, teacher_username: str, status_filter: str, 
                                assignment_filter: str, sort_by: str) -> List[Submission]:
        """获取筛选后的提交列表"""
        try:
            # 根据状态筛选
            if status_filter == "待批改":
                submissions = self.submission_service.get_pending_grading_submissions(teacher_username)
            elif status_filter == "需要审核":
                submissions = self.submission_service.get_submissions_requiring_review(teacher_username)
            else:
                # 获取所有提交（简化处理）
                submissions = self.submission_service.get_pending_grading_submissions(teacher_username)
            
            # 根据作业筛选
            if assignment_filter != "全部作业":
                submissions = [s for s in submissions if getattr(s, 'assignment_title', '') == assignment_filter]
            
            # 排序
            if sort_by == "提交时间":
                submissions.sort(key=lambda x: x.submitted_at or datetime.min, reverse=True)
            elif sort_by == "学生姓名":
                submissions.sort(key=lambda x: getattr(x, 'student_real_name', x.student_username))
            elif sort_by == "分数":
                submissions.sort(key=lambda x: x.score or 0, reverse=True)
            
            return submissions
            
        except Exception as e:
            self.logger.error(f"获取筛选提交失败: {e}")
            return []
    
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
    
    def _batch_grade_submissions(self, submissions: List[Submission]):
        """批量批改提交"""
        st.info("批量批改功能开发中...")
    
    def _batch_notify_students(self, submissions: List[Submission]):
        """批量通知学生"""
        st.info("批量通知功能开发中...")
    
    def _export_submissions_data(self, submissions: List[Submission]):
        """导出提交数据"""
        st.info("数据导出功能开发中...")
    
    def _view_submission_details(self, submission: Submission):
        """查看提交详情"""
        st.info("查看提交详情功能开发中...")
    
    def _grade_submission(self, submission: Submission):
        """批改提交"""
        st.info("批改功能开发中...")
    
    def _provide_feedback(self, submission: Submission):
        """提供反馈"""
        st.info("反馈功能开发中...")
    
    def _notify_student(self, submission: Submission):
        """通知学生"""
        st.info("通知功能开发中...")
    
    def _render_teacher_charts(self, teacher_username: str):
        """渲染教师图表"""
        st.info("教师图表功能开发中...")
    
    def _render_student_charts(self, submissions: List[Submission]):
        """渲染学生图表"""
        st.info("学生图表功能开发中...")