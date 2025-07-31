#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进度监控面板演示
展示实时进度跟踪功能
"""

import streamlit as st
import time
import threading
from datetime import datetime, timedelta
from typing import List

from src.models.task import Task, TaskStatus, TaskType, TaskPriority
from src.services.task_service import get_task_service
from src.ui.components.progress_dashboard import ProgressDashboard, ProgressDisplayConfig


def create_demo_tasks() -> List[str]:
    """创建演示任务"""
    task_service = get_task_service()
    task_ids = []
    
    # 批改任务
    grading_task_id = task_service.create_task(
        name="批改数学作业",
        task_type=TaskType.GRADING,
        input_data={
            'files': [
                {'id': '1', 'name': '张三-数学作业.pdf'},
                {'id': '2', 'name': '李四-数学作业.pdf'},
                {'id': '3', 'name': '王五-数学作业.pdf'},
                {'id': '4', 'name': '赵六-数学作业.pdf'},
                {'id': '5', 'name': '钱七-数学作业.pdf'}
            ],
            'subject': '数学',
            'grade': '高一'
        },
        description="批改高一数学期中考试试卷",
        priority=TaskPriority.HIGH,
        created_by="张老师"
    )
    task_ids.append(grading_task_id)
    
    # 文件处理任务
    file_task_id = task_service.create_task(
        name="处理英语听力文件",
        task_type=TaskType.FILE_PROCESSING,
        input_data={
            'files': [
                {'id': '6', 'name': '听力材料1.mp3'},
                {'id': '7', 'name': '听力材料2.mp3'}
            ],
            'operation': '转换格式'
        },
        description="将听力文件转换为标准格式",
        priority=TaskPriority.NORMAL,
        created_by="李老师"
    )
    task_ids.append(file_task_id)
    
    # 报告生成任务
    report_task_id = task_service.create_task(
        name="生成班级成绩报告",
        task_type=TaskType.REPORT_GENERATION,
        input_data={
            'class_id': 'class_2024_1',
            'report_type': 'monthly',
            'subjects': ['数学', '语文', '英语', '物理', '化学']
        },
        description="生成高一1班月度成绩分析报告",
        priority=TaskPriority.NORMAL,
        created_by="王老师"
    )
    task_ids.append(report_task_id)
    
    return task_ids


def simulate_task_progress():
    """模拟任务进度更新"""
    task_service = get_task_service()
    
    def update_progress():
        while True:
            # 获取运行中的任务
            running_tasks = task_service.get_tasks_by_status(TaskStatus.RUNNING)
            
            for task in running_tasks:
                if task.progress.completed_steps < task.progress.total_steps:
                    # 更新进度
                    new_completed = min(
                        task.progress.completed_steps + 1,
                        task.progress.total_steps
                    )
                    
                    remaining_steps = task.progress.total_steps - new_completed
                    estimated_time = timedelta(seconds=remaining_steps * 30) if remaining_steps > 0 else None
                    
                    task.update_progress(
                        current_step=f"处理第 {new_completed} 项",
                        completed_steps=new_completed,
                        total_steps=task.progress.total_steps,
                        current_operation=f"正在处理: {task.input_data.get('files', [{}])[0].get('name', '未知文件')}",
                        estimated_remaining_time=estimated_time
                    )
                    
                    # 如果完成了，标记为完成状态
                    if new_completed >= task.progress.total_steps:
                        task.status = TaskStatus.COMPLETED
                        task.completed_at = datetime.now()
                        task.output_data = {
                            'completed_at': datetime.now().isoformat(),
                            'processed_items': new_completed,
                            'success_rate': 95.5
                        }
            
            time.sleep(2)  # 每2秒更新一次
    
    # 在后台线程中运行进度更新
    progress_thread = threading.Thread(target=update_progress, daemon=True)
    progress_thread.start()


def main():
    """主函数"""
    st.set_page_config(
        page_title="进度监控面板演示",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 进度监控面板演示")
    st.markdown("---")
    
    # 侧边栏控制
    with st.sidebar:
        st.header("🎛️ 控制面板")
        
        # 创建演示任务
        if st.button("🚀 创建演示任务"):
            with st.spinner("正在创建演示任务..."):
                task_ids = create_demo_tasks()
                st.session_state.demo_task_ids = task_ids
                st.success(f"✅ 已创建 {len(task_ids)} 个演示任务")
        
        # 启动进度模拟
        if st.button("▶️ 启动进度模拟"):
            simulate_task_progress()
            st.success("✅ 进度模拟已启动")
        
        # 配置选项
        st.subheader("⚙️ 显示配置")
        
        show_percentage = st.checkbox("显示百分比", value=True)
        show_estimated_time = st.checkbox("显示预计时间", value=True)
        show_current_operation = st.checkbox("显示当前操作", value=True)
        show_error_details = st.checkbox("显示错误详情", value=True)
        auto_refresh_interval = st.slider("刷新间隔(秒)", 0.5, 5.0, 1.0, 0.5)
        
        # 创建配置
        config = ProgressDisplayConfig(
            show_percentage=show_percentage,
            show_estimated_time=show_estimated_time,
            show_current_operation=show_current_operation,
            show_error_details=show_error_details,
            auto_refresh_interval=auto_refresh_interval
        )
    
    # 主要内容区域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📋 任务进度监控")
        
        # 获取任务ID
        task_ids = getattr(st.session_state, 'demo_task_ids', None)
        
        if task_ids:
            # 创建进度面板
            dashboard = ProgressDashboard(config)
            dashboard.render(task_ids, "🔄 实时任务进度")
        else:
            st.info("👈 请先在侧边栏创建演示任务")
    
    with col2:
        st.header("📈 系统状态")
        
        # 显示系统统计
        task_service = get_task_service()
        stats = task_service.get_system_stats()
        
        # 任务统计
        st.metric("总任务数", stats.get('total_tasks', 0))
        st.metric("运行中", stats.get('running_tasks', 0))
        st.metric("等待中", stats.get('pending_tasks', 0))
        st.metric("已完成", stats.get('completed_tasks', 0))
        
        # 性能指标
        st.subheader("⚡ 性能指标")
        st.metric("平均执行时间", f"{stats.get('average_duration', 0):.1f}秒")
        st.metric("成功率", f"{stats.get('success_rate', 0):.1f}%")
        
        # 队列状态
        queue_status = task_service.get_queue_status()
        st.subheader("🔄 队列状态")
        st.metric("工作线程", queue_status.get('active_workers', 0))
        st.metric("队列长度", queue_status.get('pending_count', 0))
    
    # 功能说明
    with st.expander("ℹ️ 功能说明", expanded=False):
        st.markdown("""
        ### 🎯 进度监控面板功能
        
        #### ✨ 核心功能
        - **实时状态显示**: 显示任务的当前状态和进度
        - **进度条和百分比**: 直观的进度可视化
        - **预计完成时间**: 基于当前进度估算剩余时间
        - **当前操作显示**: 显示任务正在执行的具体操作
        - **错误信息展示**: 详细的错误信息和处理建议
        
        #### 🎮 交互功能
        - **任务控制**: 暂停、恢复、取消、重试任务
        - **状态筛选**: 按状态筛选显示的任务
        - **自动刷新**: 可配置的自动刷新间隔
        - **详细信息**: 可展开查看任务的详细信息
        
        #### 🔄 WebSocket支持
        - **实时更新**: 通过WebSocket实现真正的实时更新
        - **客户端管理**: 支持多客户端连接和订阅
        - **心跳检测**: 自动检测和清理断开的连接
        - **消息推送**: 任务状态变化时主动推送通知
        
        #### 📊 监控特性
        - **系统统计**: 显示整体系统运行状态
        - **性能指标**: 平均执行时间、成功率等
        - **队列状态**: 工作线程和队列长度监控
        - **历史记录**: 任务执行历史和日志
        """)
    
    # 底部信息
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "📊 进度监控面板演示 | 实现需求 4.1 - 开发进度监控面板"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()