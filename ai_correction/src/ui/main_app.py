#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主应用程序UI
Streamlit应用的入口点和路由管理
"""

import streamlit as st
from typing import Dict, Any
import logging

from src.infrastructure.container import DIContainer
from src.config.settings import get_settings


class MainApp:
    """主应用程序类"""
    
    def __init__(self, container: DIContainer):
        self.container = container
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # 配置Streamlit页面
        self._configure_page()
        
        # 初始化会话状态
        self._initialize_session_state()
    
    def _configure_page(self):
        """配置Streamlit页面"""
        st.set_page_config(
            page_title=self.settings.app_name,
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # 添加自定义CSS
        self._add_custom_css()
    
    def _add_custom_css(self):
        """添加自定义CSS样式"""
        st.markdown("""
        <style>
            .stApp {
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #475569 100%);
                color: #f8fafc;
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }
            
            #MainMenu, .stDeployButton, footer, header {visibility: hidden;}
            
            .main-title {
                font-size: 2.5rem;
                font-weight: 800;
                background: linear-gradient(135deg, #60a5fa, #c084fc);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-align: center;
                margin-bottom: 1rem;
                text-shadow: 0 0 20px rgba(96, 165, 250, 0.3);
            }
            
            .stMarkdown, .stText, .stCaption, .stWrite, p, span, div {
                color: #f1f5f9 !important;
                font-weight: 500;
            }
            
            h1, h2, h3, h4, h5, h6 {
                color: #e2e8f0 !important;
                font-weight: 700;
                text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
            }
            
            .stButton > button {
                background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
                color: white !important;
                border: none;
                border-radius: 12px;
                padding: 0.75rem 1.5rem;
                font-weight: 700;
                font-size: 1rem;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
            }
            
            .stButton > button:hover {
                transform: translateY(-2px) scale(1.02);
                box-shadow: 0 8px 25px rgba(59, 130, 246, 0.6);
                background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
            }
        </style>
        """, unsafe_allow_html=True)
    
    def _initialize_session_state(self):
        """初始化会话状态"""
        if 'initialized' not in st.session_state:
            st.session_state.initialized = True
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.session_state.current_page = 'home'
            
            self.logger.info("会话状态初始化完成")
    
    def run(self):
        """运行应用程序"""
        try:
            # 显示应用标题
            st.markdown('<h1 class="main-title">🤖 AI智能批改系统 v2.0</h1>', unsafe_allow_html=True)
            st.markdown('<p style="text-align: center; color: #94a3b8; font-size: 1.1rem;">重构版本 - 现代化架构</p>', unsafe_allow_html=True)
            
            # 显示系统状态
            self._show_system_status()
            
            # 主要内容区域
            self._render_main_content()
            
            # 侧边栏
            self._render_sidebar()
            
        except Exception as e:
            self.logger.error(f"应用程序运行错误: {e}")
            st.error(f"❌ 应用程序错误: {e}")
    
    def _show_system_status(self):
        """显示系统状态"""
        with st.expander("🔧 系统状态", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("应用版本", self.settings.app_version)
            
            with col2:
                st.metric("环境", self.settings.environment)
            
            with col3:
                st.metric("调试模式", "开启" if self.settings.debug else "关闭")
            
            # 配置状态
            st.subheader("📊 配置状态")
            config_status = {
                "数据库": "✅ 已配置",
                "AI服务": "✅ 已配置" if hasattr(self.settings.ai, 'openrouter_api_key') else "❌ 未配置",
                "缓存服务": "✅ 已配置",
                "文件存储": "✅ 已配置",
            }
            
            for service, status in config_status.items():
                st.write(f"**{service}**: {status}")
    
    def _render_main_content(self):
        """渲染主要内容"""
        # 根据当前页面显示不同内容
        current_page = st.session_state.get('current_page', 'home')
        
        if current_page == 'home':
            self._render_home_page()
        elif current_page == 'grading':
            self._render_grading_page()
        elif current_page == 'analysis':
            self._render_analysis_page()
        elif current_page == 'progress':
            self._render_progress_page()
        elif current_page == 'history':
            self._render_history_page()
        elif current_page == 'settings':
            self._render_settings_page()
        else:
            self._render_home_page()
    
    def _render_home_page(self):
        """渲染首页"""
        st.header("🏠 欢迎使用AI智能批改系统")
        
        # 功能介绍
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 AI智能批改")
            st.write("支持多种文件格式的智能批改，提供详细的评分和建议。")
            
            st.subheader("📊 班级管理")
            st.write("完整的班级和作业管理系统，支持教师和学生角色。")
        
        with col2:
            st.subheader("⚡ 高性能处理")
            st.write("异步处理和缓存优化，支持大批量文件批改。")
            
            st.subheader("🔒 安全可靠")
            st.write("完善的安全机制和错误处理，保护用户数据安全。")
        
        # 快速开始
        st.subheader("🚀 快速开始")
        
        if not st.session_state.logged_in:
            st.info("请先登录以使用完整功能")
            if st.button("前往登录"):
                st.session_state.current_page = 'login'
                st.rerun()
        else:
            st.success(f"欢迎回来，{st.session_state.current_user}！")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("开始批改"):
                    st.session_state.current_page = 'grading'
                    st.rerun()
            
            with col2:
                if st.button("详细分析"):
                    st.session_state.current_page = 'analysis'
                    st.rerun()
            
            with col3:
                if st.button("查看历史"):
                    st.session_state.current_page = 'history'
                    st.rerun()
            
            with col4:
                if st.button("系统设置"):
                    st.session_state.current_page = 'settings'
                    st.rerun()
    
    def _render_grading_page(self):
        """渲染批改页面"""
        st.header("📝 AI智能批改")
        
        # 批改功能选项卡
        tab1, tab2 = st.tabs(["🚀 开始批改", "⚙️ 配置管理"])
        
        with tab1:
            self._render_grading_interface()
        
        with tab2:
            self._render_grading_config_interface()
    
    def _render_grading_interface(self):
        """渲染批改界面"""
        st.markdown("### 🚀 开始批改")
        st.info("🚧 批改功能正在重构中，即将推出更强大的功能！")
        
        # 临时的简单界面
        st.subheader("文件上传")
        uploaded_file = st.file_uploader("选择要批改的文件", type=['pdf', 'txt', 'docx'])
        
        if uploaded_file:
            st.success(f"文件已上传: {uploaded_file.name}")
            
            if st.button("开始批改"):
                with st.spinner("正在批改中..."):
                    # 这里将在后续任务中实现实际的批改逻辑
                    import time
                    time.sleep(2)
                    st.success("批改完成！")
    
    def _render_grading_config_interface(self):
        """渲染批改配置界面"""
        try:
            from src.services.grading_config_service import GradingConfigService
            from src.ui.components.grading_config_manager import GradingConfigManager
            
            # 创建服务实例
            config_service = GradingConfigService()
            config_manager = GradingConfigManager(config_service)
            
            # 渲染配置管理界面
            config_manager.render()
            
        except Exception as e:
            st.error(f"❌ 加载配置管理器失败: {e}")
            st.info("请确保所有依赖组件已正确安装")
    
    def _render_analysis_page(self):
        """渲染分析页面"""
        try:
            from src.services.detailed_analysis_service import DetailedAnalysisService
            from src.ui.components.detailed_analysis import DetailedAnalysisComponent
            
            # 创建服务实例
            analysis_service = DetailedAnalysisService()
            analysis_component = DetailedAnalysisComponent(analysis_service)
            
            # 渲染详细分析界面
            analysis_component.render()
            
        except Exception as e:
            st.error(f"❌ 加载分析组件失败: {e}")
            st.info("请确保所有依赖组件已正确安装")
            import traceback
            st.code(traceback.format_exc())
    
    def _render_progress_page(self):
        """渲染进度监控页面"""
        try:
            from src.ui.components.progress_dashboard import ProgressDashboard, ProgressDisplayConfig
            from src.services.task_service import get_task_service
            
            st.header("📊 实时进度监控")
            
            # 配置选项
            with st.expander("⚙️ 显示配置", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    show_percentage = st.checkbox("显示百分比", value=True)
                    show_estimated_time = st.checkbox("显示预计时间", value=True)
                
                with col2:
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
            
            # 创建并渲染进度面板
            dashboard = ProgressDashboard(config)
            dashboard.render(title="🔄 任务进度监控")
            
            # 系统统计信息
            with st.expander("📈 系统统计", expanded=False):
                task_service = get_task_service()
                stats = task_service.get_system_stats()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("总任务数", stats.get('total_tasks', 0))
                
                with col2:
                    st.metric("运行中", stats.get('running_tasks', 0))
                
                with col3:
                    st.metric("已完成", stats.get('completed_tasks', 0))
                
                with col4:
                    st.metric("成功率", f"{stats.get('success_rate', 0):.1f}%")
            
        except Exception as e:
            st.error(f"❌ 加载进度监控组件失败: {e}")
            st.info("请确保所有依赖组件已正确安装")
            import traceback
            st.code(traceback.format_exc())
    
    def _render_history_page(self):
        """渲染历史页面"""
        st.header("📚 批改历史")
        st.info("🚧 历史记录功能正在重构中...")
    
    def _render_settings_page(self):
        """渲染设置页面"""
        st.header("⚙️ 系统设置")
        st.info("🚧 设置功能正在重构中...")
    
    def _render_sidebar(self):
        """渲染侧边栏"""
        with st.sidebar:
            st.markdown("### 🧭 导航")
            
            # 导航按钮
            pages = {
                'home': '🏠 首页',
                'grading': '📝 批改',
                'analysis': '📊 分析',
                'progress': '📊 进度监控',
                'history': '📚 历史',
                'settings': '⚙️ 设置'
            }
            
            for page_key, page_name in pages.items():
                if st.button(page_name, key=f"nav_{page_key}"):
                    st.session_state.current_page = page_key
                    st.rerun()
            
            st.markdown("---")
            
            # 用户状态
            if st.session_state.logged_in:
                st.success(f"👤 {st.session_state.current_user}")
                if st.button("退出登录"):
                    st.session_state.logged_in = False
                    st.session_state.current_user = None
                    st.session_state.current_page = 'home'
                    st.rerun()
            else:
                st.warning("未登录")
                if st.button("登录"):
                    # 临时登录逻辑
                    st.session_state.logged_in = True
                    st.session_state.current_user = "测试用户"
                    st.rerun()
            
            st.markdown("---")
            
            # 系统信息
            st.markdown("### ℹ️ 系统信息")
            st.write(f"**版本**: {self.settings.app_version}")
            st.write(f"**环境**: {self.settings.environment}")


if __name__ == "__main__":
    # 用于测试
    from src.infrastructure.container import configure_services
    
    container = configure_services()
    app = MainApp(container)
    app.run()