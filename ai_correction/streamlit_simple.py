#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能批改系统 - 简洁版
整合calling_api.py和main.py的所有功能，去除无意义空框
"""

import streamlit as st
import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
import time
import re

# 页面配置
st.set_page_config(
    page_title="AI智能批改系统",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 导入API函数
try:
    from functions.api_correcting.calling_api import (
        correction_single_group,
        generate_marking_scheme,
        correction_with_marking_scheme,
        correction_without_marking_scheme
    )
    API_AVAILABLE = True
    st.success("✅ AI批改引擎已就绪")
except ImportError as e:
    API_AVAILABLE = False
    st.warning(f"⚠️ AI批改引擎未就绪：{str(e)}")

# 导入LangGraph集成
try:
    from functions.langgraph_integration import (
        intelligent_correction_with_files_langgraph,
        get_langgraph_integration,
        show_langgraph_progress,
        show_langgraph_results
    )
    LANGGRAPH_AVAILABLE = True
    st.success("✅ LangGraph AI批改系统已就绪")
except ImportError as e:
    LANGGRAPH_AVAILABLE = False
    st.warning(f"⚠️ LangGraph系统未就绪：{str(e)}")

# 导入进度相关模块
try:
    from functions.progress_ui import show_progress_page, show_progress_modal
    from functions.correction_service import get_correction_service
    PROGRESS_AVAILABLE = True
except ImportError as e:
    PROGRESS_AVAILABLE = False
    st.warning(f"⚠️ 进度模块未就绪：{str(e)}")
    
    # 演示函数
    def correction_single_group(*files, **kwargs):
        return """# 📋 详细批改结果 (演示模式)

## 基本信息
- 科目：数学
- 得分：8/10 分
- 等级：B+

## 详细分析
### ✅ 优点
- 解题思路清晰正确
- 基础概念掌握扎实
- 步骤表述较为规范

### ❌ 问题
- 第3步计算有小错误
- 最终答案格式需要改进

### 💡 改进建议
1. 仔细检查计算过程
2. 注意答案的规范性
3. 可尝试多种解题方法

**注意：当前为演示模式，请配置API获得真实结果。**"""

    def generate_marking_scheme(*files, **kwargs):
        return """📋 **自动生成评分标准** (演示模式)

## 题目分析
- 科目：数学
- 类型：解答题
- 难度：中等
- 总分：10分

## 评分细则
1. **理解题意** (2分)
   - 正确理解题目要求：2分
   - 部分理解：1分
   - 未理解：0分

2. **解题思路** (3分)
   - 方法正确且优秀：3分
   - 方法基本正确：2分
   - 方法有缺陷：1分
   - 方法错误：0分

3. **计算过程** (3分)
   - 计算准确无误：3分
   - 有少量计算错误：2分
   - 有较多计算错误：1分
   - 计算错误严重：0分

4. **答案格式** (2分)
   - 格式规范完整：2分
   - 格式基本规范：1分
   - 格式不规范：0分

*演示标准，请配置API*"""

    def correction_with_marking_scheme(scheme, *files, **kwargs):
        return correction_single_group(*files, **kwargs)

    def correction_without_marking_scheme(*files, **kwargs):
        return correction_single_group(*files, **kwargs)

# 导入图片处理库
try:
    from PIL import Image
    import base64
    from io import BytesIO
    PREVIEW_AVAILABLE = True
except ImportError:
    PREVIEW_AVAILABLE = False

# 常量设置
DATA_FILE = Path("user_data.json")
UPLOAD_DIR = Path("uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = ['txt', 'md', 'pdf', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']

# 确保目录存在
UPLOAD_DIR.mkdir(exist_ok=True)

# 黑白纯色CSS样式
st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
        color: #000000;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }

    #MainMenu, .stDeployButton, footer, header {visibility: hidden;}

    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        color: #000000;
        text-align: center;
        margin-bottom: 1rem;
    }

    .stButton > button {
        background-color: #000000;
        color: white !important;
        border: 2px solid #000000;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        background-color: #333333;
        border-color: #333333;
        transform: translateY(-2px);
    }

    .result-container {
        background-color: #f5f5f5;
        border: 2px solid #000000;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    /* 分栏布局样式 - 黑白纯色 */
    .split-container {
        display: flex;
        gap: 1.5rem;
        height: 80vh;
        margin-top: 1rem;
        padding: 0;
    }

    .left-panel, .right-panel {
        background-color: #ffffff;
        border: 2px solid #000000;
        border-radius: 8px;
        padding: 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        flex: 1;
        position: relative;
        overflow: hidden;
    }

    .panel-header {
        background-color: #f0f0f0;
        border-bottom: 2px solid #000000;
        padding: 1rem 1.5rem;
        font-weight: 600;
        font-size: 1.1rem;
        color: #000000;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        border-radius: 6px 6px 0 0;
    }

    .panel-content {
        height: calc(100% - 4rem);
        overflow-y: auto;
        overflow-x: hidden;
        padding: 1.5rem;
        position: relative;
        color: #000000;
    }
    
    /* 自定义滚动条样式 */
    .panel-content::-webkit-scrollbar {
        width: 8px;
    }

    .panel-content::-webkit-scrollbar-track {
        background-color: #f0f0f0;
        border-radius: 4px;
    }

    .panel-content::-webkit-scrollbar-thumb {
        background-color: #666666;
        border-radius: 4px;
        transition: all 0.3s ease;
    }

    .panel-content::-webkit-scrollbar-thumb:hover {
        background-color: #333333;
    }

    /* 文件预览容器 */
    .file-preview-inner {
        background-color: #f5f5f5;
        border: 2px solid #cccccc;
        border-radius: 8px;
        padding: 1rem;
        min-height: 200px;
    }

    /* 批改结果容器 */
    .correction-result-inner {
        background-color: #f5f5f5;
        border: 2px solid #cccccc;
        border-radius: 8px;
        padding: 1.5rem;
        min-height: 200px;
        font-family: 'Consolas', 'Monaco', monospace;
        line-height: 1.6;
        color: #000000;
    }

    /* 文件切换器增强样式 */
    .file-selector-container {
        background-color: #f0f0f0;
        border: 2px solid #cccccc;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    /* 鼠标悬停效果 */
    .left-panel:hover, .right-panel:hover {
        border-color: #000000;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transform: translateY(-2px);
        transition: all 0.3s ease;
    }

    /* 确保容器可以正确滚动 */
    .stSelectbox > div > div,
    .stTextArea > div > div > textarea {
        background-color: #ffffff !important;
        border: 2px solid #cccccc !important;
        color: #000000 !important;
    }

    /* 确保独立滚动 */
    .panel-content {
        scroll-behavior: smooth;
    }

    /* 增强焦点效果 */
    .panel-content:focus-within {
        outline: 2px solid #000000;
        outline-offset: -2px;
    }

    /* 文件预览图片样式 */
    .file-preview-inner img {
        max-width: 100%;
        height: auto;
        border-radius: 8px;
        border: 2px solid #cccccc;
        transition: transform 0.3s ease;
    }

    .file-preview-inner img:hover {
        transform: scale(1.02);
    }

    /* 批改结果文本样式优化 */
    .correction-result-inner pre {
        font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
        font-size: 0.9rem;
        line-height: 1.6;
        color: #000000;
        background: transparent;
        border: none;
        padding: 0;
        margin: 0;
        white-space: pre-wrap;
        word-wrap: break-word;
    }

    /* 响应式设计 */
    @media (max-width: 768px) {
        .split-container {
            flex-direction: column;
            height: auto;
        }

        .left-panel, .right-panel {
            min-height: 400px;
        }

        .panel-content {
            height: 400px;
        }
    }

    .file-switcher {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }

    .file-switcher button {
        background-color: #e8e8e8 !important;
        color: #000000 !important;
        border: 2px solid #cccccc !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
        font-size: 0.9rem !important;
        transition: all 0.3s ease !important;
    }

    .file-switcher button:hover,
    .file-switcher button.active {
        background-color: #cccccc !important;
        color: #000000 !important;
        border-color: #000000 !important;
    }

    .stTextInput > div > div > input,
    .stSelectbox > div > div {
        background-color: #ffffff !important;
        border: 2px solid #cccccc !important;
        border-radius: 8px !important;
        color: #000000 !important;
    }

    .css-1d391kg {
        background-color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# 文件预览功能
def get_file_type(file_name):
    """获取文件类型"""
    ext = Path(file_name).suffix.lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        return 'image'
    elif ext == '.pdf':
        return 'pdf'
    elif ext in ['.txt', '.md']:
        return 'text'
    elif ext in ['.doc', '.docx']:
        return 'document'
    else:
        return 'unknown'

def get_image_base64(image_path):
    """将图片文件转换为base64编码"""
    import base64
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"图片base64转换失败: {e}")
        return None

def preview_file(file_path, file_name):
    """预览文件内容"""
    try:
        file_type = get_file_type(file_name)
        
        if file_type == 'image' and PREVIEW_AVAILABLE:
            try:
                image = Image.open(file_path)
                st.image(image, caption=file_name, use_column_width=True)
            except Exception as e:
                st.error(f"图片预览失败: {e}")
                
        elif file_type == 'text':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if len(content) > 5000:
                    content = content[:5000] + "\n...(内容过长，已截断)"
                st.text_area("文本内容", content, height=400, disabled=True)
            except Exception as e:
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                    if len(content) > 5000:
                        content = content[:5000] + "\n...(内容过长，已截断)"
                    st.text_area("文本内容", content, height=400, disabled=True)
                except Exception as e2:
                    st.error(f"文本预览失败: {e2}")
                    
        elif file_type == 'pdf':
            st.info(f"📄 PDF文件: {file_name}")
            st.write("PDF文件预览需要额外的库支持")
            
        elif file_type == 'document':
            st.info(f"📄 Word文档: {file_name}")
            st.write("Word文档预览需要额外的库支持")
            
        else:
            st.info(f"📄 文件: {file_name}")
            st.write("暂不支持此类型文件的预览")
            
    except Exception as e:
        st.error(f"文件预览失败: {e}")

# 初始化session state
def init_session():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'page' not in st.session_state:
        st.session_state.page = "home"
    if 'correction_result' not in st.session_state:
        st.session_state.correction_result = None
    if 'uploaded_files_data' not in st.session_state:
        st.session_state.uploaded_files_data = []
    if 'current_file_index' not in st.session_state:
        st.session_state.current_file_index = 0
    if 'correction_settings' not in st.session_state:
        st.session_state.correction_settings = {}
    if 'current_task_id' not in st.session_state:
        st.session_state.current_task_id = None

# 数据管理
def read_users():
    try:
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        
        # 确保demo用户存在
        if "demo" not in data:
            data["demo"] = {
                "password": hashlib.sha256("demo".encode()).hexdigest(),
                "email": "demo@example.com",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "records": []
            }
            save_users(data)
        
        return data
    except:
        return {}

def save_users(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"保存失败: {e}")

def save_files(files, username):
    user_dir = UPLOAD_DIR / username
    user_dir.mkdir(exist_ok=True)
    
    saved_paths = []
    for file in files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(file.name).suffix
        safe_name = re.sub(r'[^\w\-_.]', '_', Path(file.name).stem)
        filename = f"{timestamp}_{safe_name}{file_ext}"
        
        file_path = user_dir / filename
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())
        
        saved_paths.append(str(file_path))
    
    return saved_paths

# 主页面
def show_home():
    st.markdown('<h1 class="main-title">🤖 AI智能批改系统</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #94a3b8; font-size: 1.1rem;">AI赋能教育，智能批改新纪元</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 立即批改", use_container_width=True, type="primary"):
            if st.session_state.logged_in:
                st.session_state.page = "grading"
                st.rerun()
            else:
                st.session_state.page = "login"
                st.rerun()
    
    with col2:
        if st.button("📚 查看历史", use_container_width=True):
            if st.session_state.logged_in:
                st.session_state.page = "history"
                st.rerun()
            else:
                st.session_state.page = "login"
                st.rerun()
    
    with col3:
        if st.button("👤 用户中心", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()
    
    # 功能介绍
    st.markdown("---")
    st.markdown("### 💡 系统特色")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🎯 智能批改**")
        st.write("• 支持多种文件格式")
        st.write("• 智能识别内容")
        st.write("• 详细错误分析")
    
    with col2:
        st.markdown("**📊 多种模式**")
        st.write("• 高效模式：快速批改")
        st.write("• 详细模式：深度分析")
        st.write("• 批量模式：批量处理")
    
    with col3:
        st.markdown("**💎 增值功能**")
        st.write("• 自动生成评分标准")
        st.write("• 多语言支持")
        st.write("• 历史记录管理")

# 登录页面
def show_login():
    st.markdown('<h2 class="main-title">🔐 用户中心</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="输入用户名")
            password = st.text_input("密码", type="password", placeholder="输入密码")
            
            col1, col2 = st.columns(2)
            with col1:
                login_btn = st.form_submit_button("登录", use_container_width=True)
            with col2:
                demo_btn = st.form_submit_button("演示登录", use_container_width=True)
            
            if login_btn or demo_btn:
                if demo_btn:
                    username, password = "demo", "demo"
                
                if username and password:
                    users = read_users()
                    stored_pwd = users.get(username, {}).get('password')
                    input_pwd = hashlib.sha256(password.encode()).hexdigest()
                    
                    if stored_pwd == input_pwd:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.page = "grading"
                        st.success(f"欢迎，{username}！")
                        st.rerun()
                    else:
                        st.error("用户名或密码错误")
                else:
                    st.error("请输入用户名和密码")
        
        st.info("💡 演示账户：demo/demo")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("用户名")
            new_email = st.text_input("邮箱")
            new_password = st.text_input("密码", type="password")
            confirm_password = st.text_input("确认密码", type="password")
            
            register_btn = st.form_submit_button("注册", use_container_width=True)
            
            if register_btn:
                if all([new_username, new_password, confirm_password]):
                    if new_password == confirm_password:
                        users = read_users()
                        if new_username not in users:
                            users[new_username] = {
                                "password": hashlib.sha256(new_password.encode()).hexdigest(),
                                "email": new_email or f"{new_username}@example.com",
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "records": []
                            }
                            save_users(users)
                            st.success("注册成功！请登录")
                        else:
                            st.error("用户名已存在")
                    else:
                        st.error("密码不一致")
                else:
                    st.error("请填写所有必填字段")

# 批改页面
def show_grading():
    if not st.session_state.logged_in:
        st.warning("请先登录")
        st.session_state.page = "login"
        st.rerun()
        return
    
    st.markdown('<h2 class="main-title">📝 AI智能批改</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="text-align: center; color: #94a3b8;">欢迎，{st.session_state.username}！</p>', unsafe_allow_html=True)
    
    # 分类文件上传区域
    st.markdown("### 📤 文件上传")
    
    # 使用三列布局
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📋 题目文件**")
        question_files = st.file_uploader(
            "上传题目",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            help="上传题目文件（可选）",
            key="question_upload"
        )
        if question_files:
            st.success(f"✅ {len(question_files)} 个题目文件")
    
    with col2:
        st.markdown("**✏️ 学生作答**")
        answer_files = st.file_uploader(
            "上传学生答案",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            help="上传学生作答文件（必填）",
            key="answer_upload"
        )
        if answer_files:
            st.success(f"✅ {len(answer_files)} 个答案文件")
    
    with col3:
        st.markdown("**📊 批改标准**")
        marking_files = st.file_uploader(
            "上传评分标准",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            help="上传评分标准文件（可选）",
            key="marking_upload"
        )
        if marking_files:
            st.success(f"✅ {len(marking_files)} 个标准文件")
    
    # 合并所有文件
    all_uploaded_files = []
    if question_files:
        all_uploaded_files.extend(question_files)
    if answer_files:
        all_uploaded_files.extend(answer_files)
    if marking_files:
        all_uploaded_files.extend(marking_files)
    
    # 批改设置
    col1, col2, col3 = st.columns(3)
    
    with col1:
        strictness = st.selectbox("严格程度", ["宽松", "中等", "严格"], index=1)
    
    with col2:
        language = st.selectbox("语言", [("中文", "zh"), ("English", "en")], format_func=lambda x: x[0])[1]
    
    with col3:
        mode_options = [
            ("🎯 高效模式", "efficient"),
            ("📝 详细模式", "detailed"),
            ("🚀 批量模式", "batch"),
            ("📋 生成标准", "generate_scheme"),
            ("🤖 自动批改", "auto")
        ]

        # 如果LangGraph可用，添加LangGraph选项
        if LANGGRAPH_AVAILABLE:
            mode_options.append(("🧠 LangGraph智能批改", "langgraph"))

        mode = st.selectbox(
            "批改模式",
            mode_options,
            format_func=lambda x: x[0]
        )[1]
    
    # 批改按钮
    if answer_files:  # 至少需要有学生答案文件
        if st.button("🚀 开始AI批改", use_container_width=True, type="primary"):
            with st.spinner("🤖 AI批改中..."):
                try:
                    # 分别保存不同类型的文件
                    saved_question_files = save_files(question_files or [], st.session_state.username) if question_files else []
                    saved_answer_files = save_files(answer_files, st.session_state.username)
                    saved_marking_files = save_files(marking_files or [], st.session_state.username) if marking_files else []
                    
                    # 根据模式选择批改方法
                    if mode == "langgraph" and LANGGRAPH_AVAILABLE:
                        # 使用LangGraph进行批改
                        st.info("🧠 使用LangGraph智能批改系统...")

                        # 创建进度显示容器
                        progress_container = st.empty()

                        # 异步运行LangGraph批改
                        integration = get_langgraph_integration()
                        import asyncio

                        async def run_langgraph_correction():
                            return await integration.intelligent_correction_with_langgraph(
                                question_files=saved_question_files,
                                answer_files=saved_answer_files,
                                marking_scheme_files=saved_marking_files,
                                strictness_level=strictness,
                                language=language,
                                mode="auto",  # LangGraph内部使用auto模式
                                user_id=st.session_state.username
                            )

                        # 运行异步函数
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        try:
                            langgraph_result = loop.run_until_complete(run_langgraph_correction())

                            # 转换为文本格式（兼容现有显示逻辑）
                            if langgraph_result.get('success', False):
                                result = langgraph_result.get('feedback', '')

                                # 保存LangGraph结果到session_state
                                st.session_state.langgraph_result = langgraph_result

                            else:
                                result = f"LangGraph批改失败: {langgraph_result.get('error', '未知错误')}"

                        finally:
                            loop.close()
                    else:
                        # 使用传统批改方法
                        from functions.api_correcting.calling_api import intelligent_correction_with_files
                        result = intelligent_correction_with_files(
                            question_files=saved_question_files,
                            answer_files=saved_answer_files,
                            marking_scheme_files=saved_marking_files,
                            strictness_level=strictness,
                            language=language,
                            mode=mode
                        )
                    
                    # 保存记录
                    users = read_users()
                    if st.session_state.username in users:
                        all_file_names = []
                        if question_files:
                            all_file_names.extend([f"[题目]{f.name}" for f in question_files])
                        if answer_files:
                            all_file_names.extend([f"[答案]{f.name}" for f in answer_files])
                        if marking_files:
                            all_file_names.extend([f"[标准]{f.name}" for f in marking_files])
                        
                        record = {
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'files': all_file_names,
                            'settings': {'strictness': strictness, 'language': language, 'mode': mode},
                            'result': result,
                            'files_count': len(all_uploaded_files)
                        }
                        users[st.session_state.username]['records'].append(record)
                        save_users(users)
                    
                    # 保存批改结果和文件数据，跳转到结果页面
                    st.session_state.correction_result = result
                    st.session_state.uploaded_files_data = [
                        {'name': f.name, 'path': path, 'type': get_file_type(f.name)} 
                        for f, path in zip(all_uploaded_files, saved_question_files + saved_answer_files + saved_marking_files)
                    ]
                    st.session_state.correction_settings = {
                        'strictness': strictness, 
                        'language': language, 
                        'mode': mode
                    }
                    # 重置文件索引到第一个文件
                    st.session_state.current_file_index = 0
                    st.session_state.page = "result"
                    st.success("🎉 批改完成！正在跳转...")
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"批改失败：{str(e)}")
    else:
        st.warning("请先上传学生答案文件")

# 批改结果展示页面 - 左右对照布局
def show_result():
    if not st.session_state.logged_in:
        st.warning("请先登录")
        st.session_state.page = "login"
        st.rerun()
        return
    
    if not st.session_state.correction_result or not st.session_state.uploaded_files_data:
        st.warning("没有批改结果数据")
        st.session_state.page = "grading"
        st.rerun()
        return
    
    st.markdown('<h2 class="main-title">📊 批改结果对照</h2>', unsafe_allow_html=True)
    
    # 顶部操作栏
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        settings = st.session_state.correction_settings
        st.markdown(f"**设置：** {settings.get('mode', 'N/A')} | {settings.get('strictness', 'N/A')} | {settings.get('language', 'zh')}")
    
    with col2:
        if st.button("🔄 重新批改"):
            st.session_state.page = "grading"
            st.rerun()
    
    with col3:
        filename = f"correction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        st.download_button("💾 下载结果", 
                         data=st.session_state.correction_result, 
                         file_name=filename, 
                         mime="text/plain")
    
    with col4:
        if st.button("🏠 返回首页"):
            st.session_state.page = "home"
            st.rerun()
    
    st.markdown("---")
    
        # 使用Streamlit原生组件的简化版本
    # 创建左右两列
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### 📁 文件预览")
        
        # 文件预览容器
        preview_container = st.container()
        
        with preview_container:
            if st.session_state.uploaded_files_data:
                # 确保索引在有效范围内
                if st.session_state.current_file_index >= len(st.session_state.uploaded_files_data):
                    st.session_state.current_file_index = 0
                
                current_file = st.session_state.uploaded_files_data[st.session_state.current_file_index]
                
                # 显示当前文件信息
                st.info(f"📄 **{current_file['name']}** ({current_file['type']})")
                
                # 文件预览 - 固定高度与批改结果区域一致
                if current_file['path'] and Path(current_file['path']).exists():
                    file_type = get_file_type(current_file['name'])
                    
                    if file_type == 'image':
                        try:
                            # 获取图片的base64编码
                            image_base64 = get_image_base64(current_file['path'])
                            if image_base64:
                                # 使用容器和CSS创建固定高度的图片预览区域
                                st.markdown(f"""
                                <div style="
                                    height: 500px; 
                                    overflow: auto; 
                                    border: 1px solid #404040;
                                    border-radius: 8px;
                                    padding: 10px;
                                    background-color: #262730;
                                    display: flex;
                                    justify-content: center;
                                    align-items: flex-start;
                                ">
                                    <img src="data:image/jpeg;base64,{image_base64}" 
                                         style="max-width: 100%; height: auto; object-fit: contain;" 
                                         alt="{current_file['name']}" />
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                raise Exception("图片base64转换失败")
                        except Exception as e:
                            # 如果base64转换失败，使用st.image但限制高度
                            try:
                                # 创建一个固定高度的容器来包含图片
                                with st.container():
                                    st.markdown("""
                                    <style>
                                    .fixed-height-image {
                                        height: 500px;
                                        overflow: auto;
                                        border: 1px solid #404040;
                                        border-radius: 8px;
                                        padding: 10px;
                                        background-color: #262730;
                                    }
                                    </style>
                                    """, unsafe_allow_html=True)
                                    
                                    st.markdown('<div class="fixed-height-image">', unsafe_allow_html=True)
                                    st.image(current_file['path'], caption=current_file['name'], width=400)
                                    st.markdown('</div>', unsafe_allow_html=True)
                            except Exception as e2:
                                st.error(f"📷 图片预览失败: {str(e2)}")
                    
                    elif file_type == 'text':
                        try:
                            with open(current_file['path'], 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            if len(content) > 5000:
                                content = content[:5000] + "\n\n...(内容已截断，可滚动查看)"
                            
                            # 使用st.text_area显示文本内容，高度与批改结果一致
                            st.text_area("文件内容", content, height=500, disabled=True, label_visibility="collapsed")
                            
                        except Exception as e:
                            st.error(f"📄 文本预览失败: {str(e)}")
                    
                    else:
                        # 为其他文件类型创建一个固定高度的信息容器
                        st.markdown(f"""
                        <div style="
                            height: 500px; 
                            overflow: auto; 
                            border: 1px solid #404040;
                            border-radius: 8px;
                            padding: 20px;
                            background-color: #262730;
                            display: flex;
                            flex-direction: column;
                            justify-content: center;
                            align-items: center;
                            text-align: center;
                        ">
                            <h3>📄 {file_type.upper()} 文件</h3>
                            <p><strong>文件名:</strong> {current_file['name']}</p>
                            <p style="color: #94a3b8;">此文件类型暂不支持预览</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    # 为文件预览不可用创建一个固定高度的提示容器
                    warning_msg = "💡 历史记录，原始文件可能已被清理" if not current_file['path'] else "⚠️ 原始文件不存在"
                    st.markdown(f"""
                    <div style="
                        height: 500px; 
                        overflow: auto; 
                        border: 1px solid #404040;
                        border-radius: 8px;
                        padding: 20px;
                        background-color: #262730;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        text-align: center;
                    ">
                        <h3 style="color: #f59e0b;">⚠️ 文件预览不可用</h3>
                        <p style="color: #94a3b8;">{warning_msg}</p>
                        <p style="color: #6b7280; font-size: 0.9rem;">文件名: {current_file['name']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # 为没有可预览文件创建一个固定高度的提示容器
                st.markdown("""
                <div style="
                    height: 500px; 
                    overflow: auto; 
                    border: 1px solid #404040;
                    border-radius: 8px;
                    padding: 20px;
                    background-color: #262730;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    text-align: center;
                ">
                    <h3 style="color: #3b82f6;">📁 没有可预览的文件</h3>
                    <p style="color: #94a3b8;">请先上传文件进行批改</p>
                </div>
                """, unsafe_allow_html=True)
    
    with col_right:
        st.markdown("### 📝 批改结果")

        # 检查是否有LangGraph结果
        if hasattr(st.session_state, 'langgraph_result') and st.session_state.langgraph_result:
            # 显示LangGraph增强结果
            st.markdown("#### 🧠 LangGraph智能分析")

            # 显示LangGraph特殊结果
            if LANGGRAPH_AVAILABLE:
                show_langgraph_results(st.session_state.langgraph_result)

            # 显示传统文本结果
            with st.expander("📄 查看详细文本结果", expanded=False):
                st.text_area(
                    "批改详情",
                    st.session_state.correction_result,
                    height=300,
                    disabled=True,
                    label_visibility="collapsed"
                )
        else:
            # 传统结果显示
            result_container = st.container()

            with result_container:
                if st.session_state.correction_result:
                    # 使用st.text_area显示批改结果，避免HTML解析问题
                    st.text_area(
                        "批改详情",
                        st.session_state.correction_result,
                        height=500,
                        disabled=True,
                        label_visibility="collapsed"
                    )
                else:
                    st.info("没有批改结果")
    

    
    # 文件切换功能 (在HTML渲染后提供交互)
    if len(st.session_state.uploaded_files_data) > 1:
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            file_options = []
            for i, file_data in enumerate(st.session_state.uploaded_files_data):
                file_name = file_data['name']
                if 'question' in file_name.lower() or '题目' in file_name:
                    label = f"📋 题目: {file_name}"
                elif 'answer' in file_name.lower() or '答案' in file_name or '作答' in file_name:
                    label = f"✏️ 学生作答: {file_name}"
                elif 'scheme' in file_name.lower() or 'marking' in file_name.lower() or '标准' in file_name:
                    label = f"📊 评分标准: {file_name}"
                else:
                    label = f"📄 文件{i+1}: {file_name}"
                file_options.append(label)
            
            new_selection = st.selectbox(
                "快速切换文件:",
                options=range(len(file_options)),
                format_func=lambda x: file_options[x],
                index=st.session_state.current_file_index,
                key="file_switcher"
            )
            
            if new_selection != st.session_state.current_file_index:
                st.session_state.current_file_index = new_selection
                st.rerun()

# 历史页面
def show_history():
    if not st.session_state.logged_in:
        st.warning("请先登录")
        st.session_state.page = "login"
        st.rerun()
        return
    
    st.markdown('<h2 class="main-title">📚 批改历史</h2>', unsafe_allow_html=True)
    
    users = read_users()
    records = users.get(st.session_state.username, {}).get('records', [])
    
    if not records:
        st.info("暂无批改记录")
        if st.button("🚀 开始批改", use_container_width=True):
            st.session_state.page = "grading"
            st.rerun()
        return
    
    # 统计信息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总批改次数", len(records))
    with col2:
        total_files = sum(r.get('files_count', 0) for r in records)
        st.metric("处理文件数", total_files)
    with col3:
        if st.button("🗑️ 清空历史"):
            users[st.session_state.username]['records'] = []
            save_users(users)
            st.rerun()
    
    st.markdown("---")
    
    # 记录列表
    for i, record in enumerate(reversed(records), 1):
        with st.expander(f"📋 记录 {i} - {record['timestamp']}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**文件：** {', '.join(record.get('files', []))}")
                settings = record.get('settings', {})
                st.write(f"**设置：** {settings.get('mode', 'N/A')} | {settings.get('strictness', 'N/A')}")
                
                preview = record.get('result', '')[:200]
                if preview:
                    st.text_area("结果预览", preview + ("..." if len(record.get('result', '')) > 200 else ""), height=100, disabled=True)
            
            with col2:
                if st.button("👁️ 查看", key=f"view_{i}"):
                    st.session_state.correction_result = record.get('result', '')
                    # 尝试重建文件数据用于结果页面展示
                    file_names = record.get('files', [])
                    if file_names:
                        # 构建文件数据 - 注意：历史记录可能没有实际文件路径
                        st.session_state.uploaded_files_data = [
                            {'name': name, 'path': None, 'type': get_file_type(name)} 
                            for name in file_names
                        ]
                        st.session_state.correction_settings = record.get('settings', {})
                        # 重置文件索引到第一个文件
                        st.session_state.current_file_index = 0
                        st.session_state.page = "result"
                    else:
                        # 如果没有文件信息，回到批改页面
                        st.session_state.page = "grading"
                    st.rerun()
                
                if record.get('result'):
                    st.download_button(
                        "💾 下载",
                        data=record.get('result', ''),
                        file_name=f"record_{i}.txt",
                        mime="text/plain",
                        key=f"download_{i}"
                    )

# 侧边栏
def show_sidebar():
    with st.sidebar:
        st.markdown('<h3 style="color: #000000;">🤖 AI批改系统</h3>', unsafe_allow_html=True)

        if st.session_state.logged_in:
            st.markdown(f"👋 **{st.session_state.username}**")
            st.markdown("---")

            # 导航菜单
            if st.button("🏠 首页", use_container_width=True):
                st.session_state.page = "home"
                st.rerun()

            if st.button("📝 批改", use_container_width=True):
                st.session_state.page = "grading"
                st.rerun()

            if st.button("📊 进度", use_container_width=True):
                st.session_state.page = "progress"
                st.rerun()

            if st.button("📚 历史", use_container_width=True):
                st.session_state.page = "history"
                st.rerun()

            # 结果页面导航 (只在有结果时显示)
            if st.session_state.correction_result:
                if st.button("� 查看结果", use_container_width=True):
                    st.session_state.page = "result"
                    st.rerun()
            
            st.markdown("---")
            
            # 统计信息
            users = read_users()
            count = len(users.get(st.session_state.username, {}).get('records', []))
            st.metric("批改次数", count)
            
            st.markdown("---")
            
            # 系统状态
            if API_AVAILABLE:
                st.success("✅ AI引擎正常")
            else:
                st.warning("⚠️ 演示模式")
            
            st.markdown("---")
            
            # 退出按钮
            if st.button("🚪 退出登录", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.correction_result = None
                st.session_state.page = "home"
                st.rerun()
        else:
            # 未登录状态
            if st.button("👤 登录", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()
            
            st.markdown("---")
            st.markdown("### 💡 功能特色")
            st.markdown("""
            - 🎯 智能批改
            - 📊 多种模式
            - 📚 历史管理
            - 💾 结果导出
            """)
            
            st.markdown("---")
            
            # 系统状态
            if API_AVAILABLE:
                st.success("✅ 系统就绪")
            else:
                st.warning("⚠️ 演示模式")

# 主函数
def main():
    init_session()
    show_sidebar()

    # 页面路由
    if st.session_state.page == "home":
        show_home()
    elif st.session_state.page == "login":
        show_login()
    elif st.session_state.page == "grading":
        show_grading()
    elif st.session_state.page == "progress":
        if PROGRESS_AVAILABLE:
            show_progress_page()
        else:
            st.error("❌ 进度模块不可用")
    elif st.session_state.page == "history":
        show_history()
    elif st.session_state.page == "result":
        show_result()
    else:
        show_home()

if __name__ == "__main__":
    main() 