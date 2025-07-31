#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进度监控面板组件
实现实时进度跟踪、WebSocket连接和错误处理
"""

import streamlit as st
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import threading
from dataclasses import dataclass

from src.models.task import Task, TaskStatus, TaskError
from src.services.task_service import get_task_service


@dataclass
class ProgressDisplayConfig:
    """进度显示配置"""
    show_percentage: bool = True
    show_estimated_time: bool = True
    show_current_operation: bool = True
    show_error_details: bool = True
    auto_refresh_interval: float = 1.0
    enable_sound_notifications: bool = False


class ProgressDashboard:
    """进度监控面板组件"""
    
    def __init__(self, config: Optional[ProgressDisplayConfig] = None):
        self.config = config or ProgressDisplayConfig()
        self.task_service = get_task_service()
        
        # 初始化会话状态
        self._init_session_state()
    
    def _init_session_state(self):
        """初始化会话状态"""
        if 'progress_dashboard' not in st.session_state:
            st.session_state.progress_dashboard = {
                'monitoring_tasks': set(),  # 正在监控的任务ID
                'last_update': {},  # 每个任务的最后更新时间
                'notification_shown': set(),  # 已显示通知的任务
                'auto_refresh': True,  # 自动刷新开关
                'selected_task': None,  # 当前选中的任务
                'filter_status': 'all'  # 状态过滤器
            }
    
    def render(self, task_ids: Optional[List[str]] = None, title: str = "📊 实时进度监控"):
        """渲染进度监控面板"""
        st.markdown(f"### {title}")
        
        # 控制面板
        self._render_control_panel()
        
        # 如果没有指定任务ID，显示所有活跃任务
        if task_ids is None:
            task_ids = self._get_active_task_ids()
        
        if not task_ids:
            st.info("📝 当前没有正在执行的任务")
            return
        
        # 任务过滤和排序
        filtered_tasks = self._filter_and_sort_tasks(task_ids)
        
        if not filtered_tasks:
            st.info("🔍 没有符合筛选条件的任务")
            return
        
        # 渲染任务列表
        self._render_task_list(filtered_tasks)
        
        # 自动刷新
        if st.session_state.progress_dashboard['auto_refresh']:
            time.sleep(self.config.auto_refresh_interval)
            st.rerun()
    
    def _render_control_panel(self):
        """渲染控制面板"""
        with st.expander("⚙️ 控制面板", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # 自动刷新开关
                auto_refresh = st.checkbox(
                    "🔄 自动刷新",
                    value=st.session_state.progress_dashboard['auto_refresh'],
                    help="启用后将自动刷新进度信息"
                )
                st.session_state.progress_dashboard['auto_refresh'] = auto_refresh
            
            with col2:
                # 状态过滤器
                status_filter = st.selectbox(
                    "📋 状态筛选",
                    options=['all', 'running', 'pending', 'completed', 'failed', 'paused'],
                    index=0,
                    format_func=lambda x: {
                        'all': '全部',
                        'running': '运行中',
                        'pending': '等待中',
                        'completed': '已完成',
                        'failed': '失败',
                        'paused': '已暂停'
                    }.get(x, x)
                )
                st.session_state.progress_dashboard['filter_status'] = status_filter
            
            with col3:
                # 手动刷新按钮
                if st.button("🔄 立即刷新"):
                    st.rerun()
            
            with col4:
                # 清理完成任务
                if st.button("🧹 清理完成任务"):
                    self._cleanup_completed_tasks()
                    st.success("✅ 已清理完成的任务")
                    st.rerun()
    
    def _render_task_list(self, tasks: List[Task]):
        """渲染任务列表"""
        for task in tasks:
            self._render_task_card(task)
            st.markdown("---")
    
    def _render_task_card(self, task: Task):
        """渲染单个任务卡片"""
        # 任务标题和状态
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            status_icon = self._get_status_icon(task.status)
            st.markdown(f"**{status_icon} {task.name}**")
            if task.description:
                st.caption(task.description)
        
        with col2:
            status_color = self._get_status_color(task.status)
            st.markdown(f"<span style='color: {status_color}; font-weight: bold;'>{task.status.value.upper()}</span>", 
                       unsafe_allow_html=True)
        
        with col3:
            # 任务操作按钮
            self._render_task_actions(task)
        
        # 进度信息
        if task.status in [TaskStatus.RUNNING, TaskStatus.PAUSED]:
            self._render_progress_info(task)
        
        # 时间信息
        self._render_time_info(task)
        
        # 错误信息
        if task.errors:
            self._render_error_info(task)
        
        # 详细信息（可展开）
        with st.expander(f"📋 详细信息 - {task.id[:8]}", expanded=False):
            self._render_task_details(task)
    
    def _render_progress_info(self, task: Task):
        """渲染进度信息"""
        progress = task.progress
        
        # 进度条
        if self.config.show_percentage and progress.total_steps > 0:
            progress_value = progress.completed_steps / progress.total_steps
            st.progress(progress_value, text=f"{progress.percentage:.1f}% 完成")
        
        # 当前步骤和操作
        col1, col2 = st.columns(2)
        
        with col1:
            if progress.current_step:
                st.write(f"**当前步骤:** {progress.current_step}")
            if progress.completed_steps > 0 and progress.total_steps > 0:
                st.write(f"**进度:** {progress.completed_steps}/{progress.total_steps}")
        
        with col2:
            if self.config.show_current_operation and progress.current_operation:
                st.write(f"**当前操作:** {progress.current_operation}")
            
            # 预计剩余时间
            if self.config.show_estimated_time and progress.estimated_remaining_time:
                remaining = progress.estimated_remaining_time
                if remaining.total_seconds() > 0:
                    st.write(f"**预计剩余:** {self._format_duration(remaining)}")
    
    def _render_time_info(self, task: Task):
        """渲染时间信息"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.caption(f"**创建时间:** {task.created_at.strftime('%H:%M:%S')}")
        
        with col2:
            if task.started_at:
                st.caption(f"**开始时间:** {task.started_at.strftime('%H:%M:%S')}")
        
        with col3:
            if task.completed_at:
                st.caption(f"**完成时间:** {task.completed_at.strftime('%H:%M:%S')}")
            elif task.started_at:
                duration = datetime.now() - task.started_at
                st.caption(f"**运行时长:** {self._format_duration(duration)}")
    
    def _render_error_info(self, task: Task):
        """渲染错误信息"""
        if not self.config.show_error_details:
            return
        
        with st.expander(f"⚠️ 错误信息 ({len(task.errors)})", expanded=False):
            for i, error in enumerate(task.errors[-5:]):  # 只显示最近5个错误
                st.error(f"**{error.error_type}:** {error.error_message}")
                st.caption(f"时间: {error.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | 重试次数: {error.retry_count}")
                
                if error.stack_trace and st.checkbox(f"显示堆栈跟踪 #{i+1}", key=f"stack_{task.id}_{i}"):
                    st.code(error.stack_trace, language="python")
    
    def _render_task_actions(self, task: Task):
        """渲染任务操作按钮"""
        if task.status == TaskStatus.RUNNING:
            if st.button("⏸️", key=f"pause_{task.id}", help="暂停任务"):
                if self.task_service.pause_task(task.id):
                    st.success("✅ 任务已暂停")
                    st.rerun()
                else:
                    st.error("❌ 暂停失败")
        
        elif task.status == TaskStatus.PAUSED:
            if st.button("▶️", key=f"resume_{task.id}", help="恢复任务"):
                if self.task_service.resume_task(task.id):
                    st.success("✅ 任务已恢复")
                    st.rerun()
                else:
                    st.error("❌ 恢复失败")
        
        elif task.status == TaskStatus.FAILED and task.can_retry():
            if st.button("🔄", key=f"retry_{task.id}", help="重试任务"):
                if self.task_service.retry_task(task.id):
                    st.success("✅ 任务已重新提交")
                    st.rerun()
                else:
                    st.error("❌ 重试失败")
        
        # 取消按钮（对于未完成的任务）
        if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PAUSED]:
            if st.button("❌", key=f"cancel_{task.id}", help="取消任务"):
                if self.task_service.cancel_task(task.id):
                    st.success("✅ 任务已取消")
                    st.rerun()
                else:
                    st.error("❌ 取消失败")
    
    def _render_task_details(self, task: Task):
        """渲染任务详细信息"""
        # 基本信息
        st.write(f"**任务ID:** `{task.id}`")
        st.write(f"**任务类型:** {task.task_type.value}")
        st.write(f"**优先级:** {task.priority.value}")
        st.write(f"**创建者:** {task.created_by or '未知'}")
        
        # 配置信息
        st.write("**配置信息:**")
        config_info = {
            "最大重试次数": task.config.max_retries,
            "重试延迟": f"{task.config.retry_delay.total_seconds()}秒",
            "自动清理": "是" if task.config.auto_cleanup else "否"
        }
        for key, value in config_info.items():
            st.write(f"  - {key}: {value}")
        
        # 输入数据
        if task.input_data:
            st.write("**输入数据:**")
            st.json(task.input_data)
        
        # 输出数据
        if task.output_data:
            st.write("**输出数据:**")
            st.json(task.output_data)
        
        # 依赖关系
        if task.depends_on:
            st.write(f"**依赖任务:** {', '.join(task.depends_on)}")
    
    def _get_active_task_ids(self) -> List[str]:
        """获取活跃任务ID列表"""
        active_statuses = [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PAUSED, TaskStatus.RETRYING]
        active_tasks = []
        
        for status in active_statuses:
            active_tasks.extend(self.task_service.get_tasks_by_status(status))
        
        return [task.id for task in active_tasks]
    
    def _filter_and_sort_tasks(self, task_ids: List[str]) -> List[Task]:
        """过滤和排序任务"""
        tasks = []
        
        for task_id in task_ids:
            task = self.task_service.get_task(task_id)
            if task:
                # 状态过滤
                filter_status = st.session_state.progress_dashboard['filter_status']
                if filter_status != 'all' and task.status.value != filter_status:
                    continue
                
                tasks.append(task)
        
        # 按优先级和创建时间排序
        tasks.sort(key=lambda t: (t.priority.value, t.created_at), reverse=True)
        
        return tasks
    
    def _cleanup_completed_tasks(self):
        """清理已完成的任务"""
        completed_tasks = self.task_service.get_tasks_by_status(TaskStatus.COMPLETED)
        failed_tasks = self.task_service.get_tasks_by_status(TaskStatus.FAILED)
        
        # 从监控列表中移除
        monitoring_tasks = st.session_state.progress_dashboard['monitoring_tasks']
        for task in completed_tasks + failed_tasks:
            monitoring_tasks.discard(task.id)
    
    def _get_status_icon(self, status: TaskStatus) -> str:
        """获取状态图标"""
        icons = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.RUNNING: "🔄",
            TaskStatus.PAUSED: "⏸️",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.CANCELLED: "🚫",
            TaskStatus.RETRYING: "🔁"
        }
        return icons.get(status, "❓")
    
    def _get_status_color(self, status: TaskStatus) -> str:
        """获取状态颜色"""
        colors = {
            TaskStatus.PENDING: "#FFA500",      # 橙色
            TaskStatus.RUNNING: "#1E90FF",      # 蓝色
            TaskStatus.PAUSED: "#FFD700",       # 金色
            TaskStatus.COMPLETED: "#32CD32",    # 绿色
            TaskStatus.FAILED: "#FF4500",       # 红色
            TaskStatus.CANCELLED: "#808080",    # 灰色
            TaskStatus.RETRYING: "#9370DB"      # 紫色
        }
        return colors.get(status, "#000000")
    
    def _format_duration(self, duration: timedelta) -> str:
        """格式化时长显示"""
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}秒"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}分{seconds}秒"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}小时{minutes}分"
    
    def render_mini_dashboard(self, task_id: str):
        """渲染迷你进度面板（用于嵌入其他页面）"""
        task = self.task_service.get_task(task_id)
        if not task:
            st.error(f"❌ 任务不存在: {task_id}")
            return
        
        # 简化的进度显示
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            status_icon = self._get_status_icon(task.status)
            st.write(f"{status_icon} **{task.name}**")
        
        with col2:
            if task.progress.total_steps > 0:
                progress_value = task.progress.completed_steps / task.progress.total_steps
                st.progress(progress_value, text=f"{task.progress.percentage:.0f}%")
        
        with col3:
            status_color = self._get_status_color(task.status)
            st.markdown(f"<span style='color: {status_color}; font-weight: bold;'>{task.status.value}</span>", 
                       unsafe_allow_html=True)
        
        # 当前操作
        if task.progress.current_operation:
            st.caption(f"🔄 {task.progress.current_operation}")
        
        # 错误提示
        if task.errors:
            latest_error = task.errors[-1]
            st.error(f"⚠️ {latest_error.error_message}")
    
    def show_completion_notification(self, task_id: str):
        """显示任务完成通知"""
        task = self.task_service.get_task(task_id)
        if not task:
            return
        
        notification_key = f"notification_{task_id}"
        if notification_key not in st.session_state.progress_dashboard['notification_shown']:
            if task.status == TaskStatus.COMPLETED:
                st.success(f"🎉 任务完成: {task.name}")
                if self.config.enable_sound_notifications:
                    # 这里可以添加声音通知的逻辑
                    pass
            elif task.status == TaskStatus.FAILED:
                st.error(f"❌ 任务失败: {task.name}")
                if task.errors:
                    st.error(f"错误: {task.errors[-1].error_message}")
            
            st.session_state.progress_dashboard['notification_shown'].add(notification_key)


# 便捷函数
def render_progress_dashboard(task_ids: Optional[List[str]] = None, 
                            title: str = "📊 实时进度监控",
                            config: Optional[ProgressDisplayConfig] = None):
    """渲染进度监控面板的便捷函数"""
    dashboard = ProgressDashboard(config)
    dashboard.render(task_ids, title)


def render_mini_progress(task_id: str):
    """渲染迷你进度面板的便捷函数"""
    dashboard = ProgressDashboard()
    dashboard.render_mini_dashboard(task_id)