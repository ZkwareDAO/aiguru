#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提交界面组件
提供学生作业提交和结果查看的界面
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import json

from src.models.assignment import Assignment
from src.models.submission import Submission, SubmissionStatus, SubmissionGradingDetails
from src.services.assignment_service import AssignmentService
from src.services.submission_service import SubmissionService
from src.infrastructure.logging import get_logger


class SubmissionInterface:
    """提交界面组件"""
    
    def __init__(self, assignment_service: AssignmentService, 
                 submission_service: SubmissionService):
        self.assignment_service = assignment_service
        self.submission_service = submission_service
        self.logger = get_logger(f"{__name__}.SubmissionInterface")
    
    def render_assignment_details(self, assignment: Assignment, student_username: str = None):
        """显示作业详情和要求"""
        st.markdown(f"## 📋 {assignment.title}")
        
        # 作业基本信息卡片
        with st.container():
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("作业ID", assignment.id)
            
            with col2:
                if hasattr(assignment, 'class_name'):
                    st.metric("班级", assignment.class_name)
                else:
                    st.metric("班级ID", assignment.class_id)
            
            with col3:
                if assignment.deadline:
                    deadline_str = assignment.deadline.strftime("%m-%d %H:%M")
                    st.metric("截止时间", deadline_str)
                else:
                    st.metric("截止时间", "无限制")
            
            with col4:
                # 显示提交状态
                if student_username:
                    submission = self.submission_service.get_submission(assignment.id, student_username)
                    if submission:
                        status_text = self._get_status_display(submission.status)
                        st.metric("提交状态", status_text)
                    else:
                        st.metric("提交状态", "未提交")
        
        # 时间状态指示器
        if assignment.deadline:
            time_left = assignment.deadline - datetime.now()
            if time_left.total_seconds() > 0:
                if time_left.days > 0:
                    st.success(f"⏰ 距离截止还有 {time_left.days} 天 {time_left.seconds // 3600} 小时")
                elif time_left.seconds > 3600:
                    st.warning(f"⏰ 距离截止还有 {time_left.seconds // 3600} 小时")
                else:
                    st.error(f"⏰ 距离截止还有 {time_left.seconds // 60} 分钟")
            else:
                st.error("⏰ 作业已过截止时间")
        
        # 作业描述
        if assignment.description:
            st.markdown("### 📝 作业要求")
            st.markdown(assignment.description)
        
        # 题目文件
        if assignment.question_files:
            st.markdown("### 📎 题目文件")
            
            for i, file_path in enumerate(assignment.question_files):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"📄 {file_path}")
                
                with col2:
                    if st.button("📥 下载", key=f"download_question_{assignment.id}_{i}"):
                        self._download_file(file_path)
        
        # 批改标准（可选显示）
        if assignment.marking_files and st.checkbox("显示批改标准", help="查看本次作业的批改标准"):
            st.markdown("### 📏 批改标准")
            
            for i, file_path in enumerate(assignment.marking_files):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"📋 {file_path}")
                
                with col2:
                    if st.button("📥 下载", key=f"download_marking_{assignment.id}_{i}"):
                        self._download_file(file_path)
        
        # 作业配置信息
        with st.expander("⚙️ 作业配置", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**基本设置**")
                st.write(f"- 自动批改: {'启用' if assignment.auto_grading_enabled else '禁用'}")
                st.write(f"- 创建时间: {assignment.created_at.strftime('%Y-%m-%d %H:%M')}")
                st.write(f"- 作业状态: {'活跃' if assignment.is_active else '已停用'}")
            
            with col2:
                st.write("**批改设置**")
                st.write(f"- 配置ID: {assignment.grading_config_id or '使用默认配置'}")
                st.write(f"- 模板ID: {assignment.grading_template_id or '使用默认模板'}")
                
                if hasattr(assignment, 'teacher_username'):
                    st.write(f"- 任课教师: {assignment.teacher_username}")
    
    def render_file_upload_form(self, assignment: Assignment, student_username: str):
        """提供文件上传表单"""
        st.markdown("### 📤 提交作业")
        
        # 检查是否已经提交
        existing_submission = self.submission_service.get_submission(assignment.id, student_username)
        
        if existing_submission:
            st.info("您已经提交过这个作业，重新提交将覆盖之前的内容")
            
            # 显示之前的提交信息
            with st.expander("查看之前的提交", expanded=False):
                st.write(f"**提交时间**: {existing_submission.submitted_at.strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**提交状态**: {self._get_status_display(existing_submission.status)}")
                
                if existing_submission.answer_files:
                    st.write("**已提交文件**:")
                    for file in existing_submission.answer_files:
                        st.write(f"- 📎 {file}")
        
        # 文件上传表单
        with st.form(f"submission_form_{assignment.id}"):
            st.markdown("#### 📁 选择答案文件")
            
            # 文件上传器
            uploaded_files = st.file_uploader(
                "选择要提交的文件",
                type=['pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'zip'],
                accept_multiple_files=True,
                help="支持的文件格式: PDF, Word文档, 文本文件, 图片, 压缩包"
            )
            
            # 文件预览
            if uploaded_files:
                st.markdown("#### 📋 文件预览")
                
                total_size = 0
                for file in uploaded_files:
                    file_size = len(file.getvalue())
                    total_size += file_size
                    
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"📄 {file.name}")
                    
                    with col2:
                        st.write(f"{self._format_file_size(file_size)}")
                    
                    with col3:
                        st.write(f"{file.type}")
                
                # 总大小检查
                max_size = 50 * 1024 * 1024  # 50MB
                if total_size > max_size:
                    st.error(f"文件总大小超过限制 ({self._format_file_size(max_size)})")
                else:
                    st.success(f"文件总大小: {self._format_file_size(total_size)}")
            
            # 提交说明
            submission_note = st.text_area(
                "提交说明（可选）",
                placeholder="您可以在这里添加关于本次提交的说明...",
                max_chars=500
            )
            
            # 确认选项
            confirm_submission = st.checkbox(
                "我确认已仔细检查文件内容，准备提交作业",
                help="请确保文件内容正确且完整"
            )
            
            # 提交按钮
            submitted = st.form_submit_button(
                "🚀 提交作业",
                type="primary",
                disabled=not (uploaded_files and confirm_submission)
            )
            
            if submitted:
                if uploaded_files and confirm_submission:
                    self._handle_file_submission(assignment, student_username, uploaded_files, submission_note)
                else:
                    st.error("请选择文件并确认提交")
    
    def render_submission_status(self, assignment: Assignment, student_username: str):
        """显示提交状态和进度"""
        submission = self.submission_service.get_submission(assignment.id, student_username)
        
        if not submission:
            st.warning("📝 您还未提交此作业")
            return
        
        st.markdown("### 📊 提交状态")
        
        # 状态进度条
        status_steps = [
            ("已提交", SubmissionStatus.SUBMITTED),
            ("AI批改中", SubmissionStatus.AI_GRADED),
            ("教师审核", SubmissionStatus.TEACHER_REVIEWED),
            ("已完成", SubmissionStatus.RETURNED)
        ]
        
        current_step = self._get_status_step(submission.status)
        
        # 创建进度指示器
        cols = st.columns(len(status_steps))
        for i, (step_name, step_status) in enumerate(status_steps):
            with cols[i]:
                if i <= current_step:
                    st.success(f"✅ {step_name}")
                elif i == current_step + 1:
                    st.info(f"🔄 {step_name}")
                else:
                    st.write(f"⏳ {step_name}")
        
        # 详细状态信息
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("当前状态", self._get_status_display(submission.status))
        
        with col2:
            st.metric("提交时间", submission.submitted_at.strftime("%m-%d %H:%M"))
        
        with col3:
            if submission.graded_at:
                st.metric("批改时间", submission.graded_at.strftime("%m-%d %H:%M"))
            else:
                st.metric("批改时间", "待批改")
        
        # AI置信度（如果有）
        if submission.ai_confidence:
            st.markdown("#### 🤖 AI批改置信度")
            confidence_percent = submission.ai_confidence * 100
            
            # 置信度进度条
            st.progress(submission.ai_confidence)
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"置信度: {confidence_percent:.1f}%")
            
            with col2:
                if confidence_percent >= 80:
                    st.success("高置信度")
                elif confidence_percent >= 60:
                    st.warning("中等置信度")
                else:
                    st.error("低置信度，建议人工审核")
        
        # 批改进度详情
        if submission.status in [SubmissionStatus.AI_GRADED, SubmissionStatus.TEACHER_REVIEWED, SubmissionStatus.RETURNED]:
            with st.expander("📈 批改进度详情", expanded=False):
                if submission.grading_details:
                    try:
                        details = json.loads(submission.grading_details) if isinstance(submission.grading_details, str) else submission.grading_details
                        
                        if isinstance(details, dict):
                            for key, value in details.items():
                                st.write(f"**{key}**: {value}")
                    except:
                        st.write("批改详情格式错误")
                else:
                    st.write("暂无详细批改信息")
        
        # 需要人工审核提示
        if submission.manual_review_required:
            st.warning("⚠️ 此提交需要教师人工审核")
    
    def render_grading_results(self, assignment: Assignment, student_username: str):
        """显示批改结果和反馈"""
        submission = self.submission_service.get_submission(assignment.id, student_username)
        
        if not submission:
            st.warning("📝 您还未提交此作业")
            return
        
        if submission.status not in [SubmissionStatus.AI_GRADED, SubmissionStatus.TEACHER_REVIEWED, SubmissionStatus.RETURNED]:
            st.info("📋 作业正在批改中，请耐心等待...")
            return
        
        st.markdown("### 📊 批改结果")
        
        # 分数展示
        if submission.score is not None:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("总分", f"{submission.score:.1f}")
            
            with col2:
                # 假设满分为100分
                percentage = (submission.score / 100) * 100
                st.metric("得分率", f"{percentage:.1f}%")
            
            with col3:
                # 等级评定
                grade = self._get_grade_level(submission.score)
                st.metric("等级", grade)
            
            # 分数可视化
            score_progress = min(submission.score / 100, 1.0)
            st.progress(score_progress)
        else:
            st.info("暂未评分")
        
        # AI批改结果
        if submission.ai_result:
            st.markdown("#### 🤖 AI批改反馈")
            
            with st.container():
                st.markdown(submission.ai_result)
        
        # 教师反馈
        if submission.teacher_feedback:
            st.markdown("#### 👨‍🏫 教师反馈")
            
            with st.container():
                st.markdown(submission.teacher_feedback)
        
        # 详细评分细节
        if submission.grading_details:
            st.markdown("#### 📋 详细评分")
            
            try:
                if isinstance(submission.grading_details, str):
                    details = json.loads(submission.grading_details)
                else:
                    details = submission.grading_details
                
                if isinstance(details, dict):
                    # 如果有评分细节，创建表格显示
                    if 'criteria_scores' in details:
                        criteria_data = []
                        for criterion, score_info in details['criteria_scores'].items():
                            if isinstance(score_info, dict):
                                criteria_data.append({
                                    "评分项目": criterion,
                                    "得分": score_info.get('score', 0),
                                    "满分": score_info.get('max_score', 100),
                                    "得分率": f"{(score_info.get('score', 0) / score_info.get('max_score', 100) * 100):.1f}%",
                                    "反馈": score_info.get('feedback', '无')
                                })
                        
                        if criteria_data:
                            df = pd.DataFrame(criteria_data)
                            st.dataframe(df, use_container_width=True)
                    
                    # 改进建议
                    if 'suggestions' in details and details['suggestions']:
                        st.markdown("#### 💡 改进建议")
                        for i, suggestion in enumerate(details['suggestions'], 1):
                            st.write(f"{i}. {suggestion}")
                
            except Exception as e:
                self.logger.error(f"解析批改详情失败: {e}")
                st.error("批改详情格式错误")
        
        # 提交的文件列表
        if submission.answer_files:
            st.markdown("#### 📎 提交的文件")
            
            for i, file_path in enumerate(submission.answer_files):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"📄 {file_path}")
                
                with col2:
                    if st.button("📥 下载", key=f"download_answer_{submission.id}_{i}"):
                        self._download_file(file_path)
        
        # 操作按钮
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 重新提交", help="重新提交作业（如果允许）"):
                self._handle_resubmission(assignment, student_username)
        
        with col2:
            if st.button("📧 联系教师", help="就此作业联系教师"):
                self._contact_teacher(assignment, submission)
        
        with col3:
            if st.button("📊 查看统计", help="查看班级统计信息"):
                self._show_class_statistics(assignment)
    
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
    
    def _get_status_step(self, status: SubmissionStatus) -> int:
        """获取状态对应的步骤"""
        step_map = {
            SubmissionStatus.SUBMITTED: 0,
            SubmissionStatus.AI_GRADED: 1,
            SubmissionStatus.TEACHER_REVIEWED: 2,
            SubmissionStatus.RETURNED: 3,
            SubmissionStatus.FAILED: 0,
            SubmissionStatus.PENDING_REVIEW: 1
        }
        return step_map.get(status, 0)
    
    def _get_grade_level(self, score: float) -> str:
        """根据分数获取等级"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def _handle_file_submission(self, assignment: Assignment, student_username: str, 
                               uploaded_files: List, submission_note: str = ""):
        """处理文件提交"""
        try:
            # 保存文件（这里简化处理，实际应该保存到文件系统）
            file_names = []
            for file in uploaded_files:
                # 这里应该实际保存文件
                file_names.append(file.name)
                self.logger.info(f"保存文件: {file.name}, 大小: {len(file.getvalue())} bytes")
            
            # 调用提交服务
            success = self.submission_service.submit_assignment(
                assignment.id,
                student_username,
                file_names
            )
            
            if success:
                st.success("✅ 作业提交成功！")
                st.balloons()
                
                # 显示提交确认信息
                with st.container():
                    st.info("📋 提交确认")
                    st.write(f"**提交时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**提交文件**: {len(file_names)} 个文件")
                    
                    if submission_note:
                        st.write(f"**提交说明**: {submission_note}")
                
                # 如果启用自动批改，显示批改提示
                if assignment.auto_grading_enabled:
                    st.info("🤖 系统将自动开始批改，请稍后查看结果")
                else:
                    st.info("👨‍🏫 作业将由教师手动批改，请耐心等待")
                
                # 刷新页面状态
                st.rerun()
            else:
                st.error("❌ 作业提交失败，请重试")
                
        except Exception as e:
            self.logger.error(f"处理文件提交失败: {e}")
            st.error(f"提交失败: {e}")
    
    def _download_file(self, file_path: str):
        """下载文件"""
        st.info(f"下载功能开发中: {file_path}")
    
    def _handle_resubmission(self, assignment: Assignment, student_username: str):
        """处理重新提交"""
        if assignment.deadline and datetime.now() > assignment.deadline:
            st.warning("⚠️ 作业已过截止时间，重新提交可能被标记为迟交")
        
        st.info("重新提交功能开发中...")
    
    def _contact_teacher(self, assignment: Assignment, submission: Submission):
        """联系教师"""
        st.info("联系教师功能开发中...")
    
    def _show_class_statistics(self, assignment: Assignment):
        """显示班级统计"""
        try:
            stats = self.assignment_service.get_assignment_statistics(assignment.id)
            
            with st.expander("📊 班级统计信息", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("班级人数", stats.get('total_students', 0))
                
                with col2:
                    st.metric("提交人数", stats.get('total_submissions', 0))
                
                with col3:
                    st.metric("平均分", f"{stats.get('average_score', 0):.1f}" if stats.get('average_score') else "暂无")
                
                with col4:
                    st.metric("提交率", f"{stats.get('submission_rate', 0):.1f}%")
                
                # 分数分布（简化显示）
                if stats.get('average_score'):
                    st.write("**班级表现**:")
                    avg_score = stats.get('average_score', 0)
                    if avg_score >= 85:
                        st.success("班级整体表现优秀")
                    elif avg_score >= 75:
                        st.info("班级整体表现良好")
                    elif avg_score >= 65:
                        st.warning("班级整体表现一般")
                    else:
                        st.error("班级整体需要改进")
                
        except Exception as e:
            self.logger.error(f"获取班级统计失败: {e}")
            st.error("获取班级统计失败")