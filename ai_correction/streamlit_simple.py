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
import base64
import html
from functions.api_correcting import (
    intelligent_correction_with_files, 
    img_to_base64,
    api_config,  # 导入API配置
    call_tongyiqianwen_api,  # 导入API调用函数
    batch_correction_with_standard,  # 添加批改函数
    batch_correction_without_standard,  # 添加批改函数
    simplified_batch_correction  # 添加简化批改函数
)
# 修复版批改函数已通过 functions.api_correcting 导入
FIXED_API_AVAILABLE = True
print("✅ 使用修复版API调用模块")
import logging
import io
from PIL import Image

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# 页面配置
st.set_page_config(
    page_title="AI智能批改系统",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 导入额外API函数
try:
    from functions.api_correcting import (
        correction_single_group,
        efficient_correction_single,
        batch_efficient_correction,
        generate_marking_scheme,
        correction_with_marking_scheme,
        correction_without_marking_scheme
    )
    
    # 检查API配置状态
    api_status = api_config.get_status()
    if api_config.is_valid():
        API_AVAILABLE = True
        st.success(f"✅ AI批改引擎已就绪 ({api_status['api_key_source']})")
    else:
        API_AVAILABLE = False
        st.error("❌ API配置无效")
        
        # 显示配置指导
        with st.expander("🔧 API配置指导", expanded=True):
            st.markdown("""
            ### 配置OpenRouter API密钥
            
            **方法1：环境变量 (推荐)**
            ```bash
            # Windows PowerShell
            $env:OPENROUTER_API_KEY="your_api_key_here"
            
            # Windows CMD
            set OPENROUTER_API_KEY=your_api_key_here
            
            # Linux/Mac
            export OPENROUTER_API_KEY=your_api_key_here
            ```
            
            **方法2：.env文件**
            1. 复制 `config_template.env` 为 `.env`
            2. 编辑 `.env` 文件，填入您的API密钥
            3. 重启应用程序
            
            **获取API密钥：**
            1. 访问 [OpenRouter](https://openrouter.ai)
            2. 注册账户并登录
            3. 前往 [API Keys](https://openrouter.ai/keys)
            4. 生成新的API密钥
            5. 复制密钥并按上述方法配置
            """)
            
            st.info(f"**当前状态：** {json.dumps(api_status, ensure_ascii=False, indent=2)}")
            
except ImportError as e:
    API_AVAILABLE = False
    st.warning(f"⚠️ AI批改引擎未就绪：{str(e)}")
    
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
    
    def efficient_correction_single(*files, **kwargs):
        return """📋 **高效批改结果** (演示模式)

**得分：8/10** | **等级：B+**

🔍 **主要问题**
• 计算步骤有错误
• 答案格式不规范

✅ **亮点**
• 思路清晰
• 基础扎实

💡 **建议**
• 检查计算
• 规范格式

*演示模式，请配置API*"""
    
    def batch_efficient_correction(*files, **kwargs):
        return f"""📊 **批量批改完成** (演示模式)

处理文件：{len(files)}个
平均得分：7.5/10
批改时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 批改概览
- 文件1：8/10 (B+)
- 文件2：7/10 (B)
- 文件3：8/10 (B+)

## 总体建议
注意计算精度，规范答题格式。

*演示模式，请配置API获得真实结果*"""
    
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

# 现代化CSS样式 - 增强版支持分栏布局
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #475569 100%);
        color: #ffffff;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    
    #MainMenu, .stDeployButton, footer, header {visibility: hidden;}
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white !important;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
    }
    
    .result-container {
        background: rgba(30, 41, 59, 0.9);
        border: 1px solid rgba(96, 165, 250, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        backdrop-filter: blur(15px);
    }
    
    /* 分栏布局样式 - 增强版 */
    .split-container {
        display: flex;
        gap: 1.5rem;
        height: 80vh;
        margin-top: 1rem;
        padding: 0;
    }
    
    .left-panel, .right-panel {
        background: rgba(30, 41, 59, 0.95);
        border: 2px solid rgba(96, 165, 250, 0.4);
        border-radius: 20px;
        padding: 0;
        backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        flex: 1;
        position: relative;
        overflow: hidden;
    }
    
    .panel-header {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2));
        border-bottom: 1px solid rgba(96, 165, 250, 0.3);
        padding: 1rem 1.5rem;
        font-weight: 600;
        font-size: 1.1rem;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        border-radius: 18px 18px 0 0;
    }
    
    .panel-content {
        height: calc(100% - 4rem);
        overflow-y: auto;
        overflow-x: hidden;
        padding: 1.5rem;
        position: relative;
    }
    
    /* 自定义滚动条样式 */
    .panel-content::-webkit-scrollbar {
        width: 8px;
    }
    
    .panel-content::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 4px;
    }
    
    .panel-content::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        border-radius: 4px;
        transition: all 0.3s ease;
    }
    
    .panel-content::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #2563eb, #7c3aed);
    }
    
    /* 文件预览容器 */
    .file-preview-inner {
        background: rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(96, 165, 250, 0.2);
        border-radius: 12px;
        padding: 1rem;
        min-height: 200px;
    }
    
    /* 批改结果容器 */
    .correction-result-inner {
        background: rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        min-height: 200px;
        font-family: 'Consolas', 'Monaco', monospace;
        line-height: 1.6;
        color: #e2e8f0;
    }
    
    /* 文件切换器增强样式 */
    .file-selector-container {
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(96, 165, 250, 0.2);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* 鼠标悬停效果 */
    .left-panel:hover, .right-panel:hover {
        border-color: rgba(96, 165, 250, 0.6);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        transform: translateY(-2px);
        transition: all 0.3s ease;
    }
    
    /* 确保容器可以正确滚动 */
    .stSelectbox > div > div,
    .stTextArea > div > div > textarea {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(96, 165, 250, 0.3) !important;
        color: #ffffff !important;
    }
    
    /* 确保独立滚动 */
    .panel-content {
        scroll-behavior: smooth;
    }
    
    /* 增强焦点效果 */
    .panel-content:focus-within {
        outline: 2px solid rgba(96, 165, 250, 0.5);
        outline-offset: -2px;
    }
    
    /* 文件预览图片样式 */
    .file-preview-inner img {
        max-width: 100%;
        height: auto;
        border-radius: 8px;
        border: 1px solid rgba(96, 165, 250, 0.2);
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
        color: #e2e8f0;
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
        background: rgba(59, 130, 246, 0.2) !important;
        color: #94a3b8 !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
        font-size: 0.9rem !important;
        transition: all 0.3s ease !important;
    }
    
    .file-switcher button:hover,
    .file-switcher button.active {
        background: rgba(59, 130, 246, 0.4) !important;
        color: #ffffff !important;
        border-color: rgba(59, 130, 246, 0.6) !important;
    }
    
    .stTextInput > div > div > input,
    .stSelectbox > div > div {
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px !important;
        color: white !important;
    }
    
    .css-1d391kg {
        background: rgba(15, 23, 42, 0.95) !important;
        backdrop-filter: blur(10px);
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

def safe_download_data(data):
    """
    安全转换下载数据为字符串格式，防止Streamlit下载按钮错误
    
    Args:
        data: 任意类型的数据
        
    Returns:
        str: 字符串格式的数据
    """
    if isinstance(data, dict):
        # 如果是字典格式的批改结果
        if data.get('has_separate_scheme', False):
            marking_scheme = data.get('marking_scheme', '')
            correction_content = data.get('correction_result', '')
            return f"=== 评分标准 ===\n\n{marking_scheme}\n\n=== 批改结果 ===\n\n{correction_content}"
        else:
            return str(data.get('correction_result', data))
    elif data is None:
        return ""
    else:
        return str(data)

def get_image_base64(image_path, max_size_mb=4):
    """将图片转换为base64编码，如果超过限制则压缩"""
    try:
        import base64
        import os
        from PIL import Image
        import io
        
        # 检查文件大小
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        
        if file_size_mb <= max_size_mb:
            # 文件不大，直接转换
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        else:
            # 文件太大，需要压缩
            print(f"图片文件过大 ({file_size_mb:.2f}MB)，正在压缩...")
            
            # 打开图片
            img = Image.open(image_path)
            
            # 转换为RGB模式（如果是RGBA）
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # 计算压缩比例
            quality = 85
            max_dimension = 1920  # 最大尺寸
            
            # 如果图片尺寸太大，先缩放
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # 压缩图片直到满足大小要求
            while quality > 20:
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                compressed_size_mb = len(buffer.getvalue()) / (1024 * 1024)
                
                if compressed_size_mb <= max_size_mb:
                    print(f"压缩完成: {file_size_mb:.2f}MB -> {compressed_size_mb:.2f}MB (质量: {quality})")
                    return base64.b64encode(buffer.getvalue()).decode()
                
                quality -= 10
            
            # 如果还是太大，进一步缩小尺寸
            while max_dimension > 800:
                max_dimension -= 200
                ratio = max_dimension / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
                
                buffer = io.BytesIO()
                img_resized.save(buffer, format='JPEG', quality=70, optimize=True)
                compressed_size_mb = len(buffer.getvalue()) / (1024 * 1024)
                
                if compressed_size_mb <= max_size_mb:
                    print(f"缩放压缩完成: {file_size_mb:.2f}MB -> {compressed_size_mb:.2f}MB (尺寸: {new_size})")
                    return base64.b64encode(buffer.getvalue()).decode()
            
            # 最后的尝试
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=50, optimize=True)
            final_size_mb = len(buffer.getvalue()) / (1024 * 1024)
            print(f"最终压缩: {file_size_mb:.2f}MB -> {final_size_mb:.2f}MB")
            return base64.b64encode(buffer.getvalue()).decode()
            
    except Exception as e:
        print(f"图片转换失败: {e}")
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
        st.session_state.uploaded_files_data = {}
    if 'current_file_index' not in st.session_state:
        st.session_state.current_file_index = 0
    if 'correction_settings' not in st.session_state:
        st.session_state.correction_settings = {}

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

def save_files(files, username, file_category=None):
    """
    保存文件并根据类别添加前缀
    
    Args:
        files: 上传的文件列表
        username: 用户名
        file_category: 文件类别 ('question', 'answer', 'marking')
    """
    user_dir = UPLOAD_DIR / username
    user_dir.mkdir(exist_ok=True)
    
    # 定义文件类别前缀
    category_prefixes = {
        'question': 'QUESTION_',
        'answer': 'ANSWER_', 
        'marking': 'MARKING_'
    }
    
    saved_files = []
    for file in files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(file.name).suffix
        safe_name = re.sub(r'[^\w\-_.]', '_', Path(file.name).stem)
        
        # 根据文件类别添加前缀
        if file_category and file_category in category_prefixes:
            prefix = category_prefixes[file_category]
            filename = f"{prefix}{timestamp}_{safe_name}{file_ext}"
        else:
            filename = f"{timestamp}_{safe_name}{file_ext}"
        
        file_path = user_dir / filename
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())
        
        # 返回包含路径和名称的字典
        saved_files.append({
            "path": str(file_path),
            "name": filename,
            "original_name": file.name,
            "category": file_category or "unknown"
        })
    
    return saved_files

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
    """显示批改页面"""
    st.header("📝 AI智能批改")
    
    # 获取批改设置
    batch_settings = st.session_state.get('batch_settings', {
        'enable_batch': True,
        'batch_size': 10,
        'skip_missing': True,
        'separate_summary': True,
        'generate_summary': True,
        'max_steps': 3
    })
    
    # 显示当前设置状态
    with st.expander("⚙️ 当前批改设置", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"🔄 分批处理: {'启用' if batch_settings['enable_batch'] else '禁用'}")
            st.write(f"📊 每批数量: {batch_settings['batch_size']}题")
            st.write(f"⏭️ 跳过缺失: {'是' if batch_settings['skip_missing'] else '否'}")
        with col2:
            st.write(f"📋 总结分离: {'是' if batch_settings['separate_summary'] else '否'}")
            st.write(f"📈 生成总结: {'是' if batch_settings['generate_summary'] else '否'}")
            st.write(f"🛑 最大步骤: {batch_settings['max_steps']}步")
    
    # 分类文件上传区域
    st.markdown("### 📤 文件上传")
    
    # 智能分类系统说明
    with st.expander("🤖 智能文件分类说明", expanded=False):
        st.markdown("""
        ### 🆕 自动文件分类系统
        
        为了提高AI批改的准确性，系统现在会自动为上传的文件添加类别前缀：
        
        - **📋 题目文件** → `QUESTION_前缀`：让AI准确识别题目内容
        - **✏️ 学生答案** → `ANSWER_前缀`：让AI专注于学生的解题过程  
        - **📊 批改标准** → `MARKING_前缀`：让AI准确识别评分标准
        
        **优势**：
        - 🎯 **精确分类**：100%准确的文件类型识别
        - ⚡ **快速处理**：无需内容分析即可分类
        - 🛡️ **错误防护**：杜绝文件类型混淆
        - 🤖 **智能批改**：AI能更准确地理解每个文件的作用
        
        您只需要按原来的方式上传文件，系统会自动处理文件命名！
        """)
    
    # 使用三列布局
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📋 题目文件**")
        st.caption("🤖 系统会自动将文件名改为 QUESTION_前缀")
        question_files = st.file_uploader(
            "上传题目",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            help="上传题目文件（可选）- 系统将自动添加QUESTION_前缀",
            key="question_upload"
        )
        if question_files:
            st.success(f"✅ {len(question_files)} 个题目文件")
            with st.expander("📝 文件预览"):
                for f in question_files:
                    st.text(f"原文件名: {f.name}")
                    st.text(f"保存为: QUESTION_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{f.name}")
                    st.divider()
    
    with col2:
        st.markdown("**✏️ 学生作答**")
        st.caption("🤖 系统会自动将文件名改为 ANSWER_前缀")
        answer_files = st.file_uploader(
            "上传学生答案",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            help="上传学生作答文件（必填）- 系统将自动添加ANSWER_前缀",
            key="answer_upload"
        )
        if answer_files:
            st.success(f"✅ {len(answer_files)} 个答案文件")
            with st.expander("📝 文件预览"):
                for f in answer_files:
                    st.text(f"原文件名: {f.name}")
                    st.text(f"保存为: ANSWER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{f.name}")
                    st.divider()
    
    with col3:
        st.markdown("**📊 批改标准**")
        st.caption("🤖 系统会自动将文件名改为 MARKING_前缀")
        marking_files = st.file_uploader(
            "上传评分标准",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            help="上传评分标准文件（可选）- 系统将自动添加MARKING_前缀",
            key="marking_upload"
        )
        if marking_files:
            st.success(f"✅ {len(marking_files)} 个标准文件")
            with st.expander("📝 文件预览"):
                for f in marking_files:
                    st.text(f"原文件名: {f.name}")
                    st.text(f"保存为: MARKING_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{f.name}")
                    st.divider()
    
    # 合并所有文件
    all_uploaded_files = []
    if question_files:
        all_uploaded_files.extend(question_files)
    if answer_files:
        all_uploaded_files.extend(answer_files)
    if marking_files:
        all_uploaded_files.extend(marking_files)
    
    # 修改批改按钮处理逻辑
    if st.button("🚀 开始AI批改", type="primary", use_container_width=True):
        if not all_uploaded_files:
            st.error("⚠️ 请先上传文件")
            return
            
        if not API_AVAILABLE:
            st.error("❌ AI批改引擎未就绪，请检查API配置")
            return
        
        # 显示批改进度
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # 文件分类和处理
            status_text.text("🔍 正在分析上传的文件...")
            progress_bar.progress(10)
            
            # 保存文件（分类保存）
            saved_files = []
            
            # 保存题目文件
            if question_files:
                saved_question_files = save_files(question_files, st.session_state.username, 'question')
                saved_files.extend(saved_question_files)
            
            # 保存答案文件
            if answer_files:
                saved_answer_files = save_files(answer_files, st.session_state.username, 'answer')
                saved_files.extend(saved_answer_files)
            
            # 保存批改标准文件
            if marking_files:
                saved_marking_files = save_files(marking_files, st.session_state.username, 'marking')
                saved_files.extend(saved_marking_files)
            
            file_paths = [f["path"] for f in saved_files]
            
            progress_bar.progress(30)
            status_text.text("🤖 正在进行AI批改...")
            
            # 根据设置选择批改方式
            if batch_settings['enable_batch']:
                # 使用增强版分批批改
                if any('MARKING' in f.name.upper() for f in all_uploaded_files):
                    # 有标准答案
                    from functions.api_correcting.calling_api import enhanced_batch_correction_with_standard
                    
                    # 分离文件
                    marking_files = [f["path"] for f in saved_files if 'MARKING' in f["name"].upper()]
                    answer_files = [f["path"] for f in saved_files if 'ANSWER' in f["name"].upper()]
                    
                    result = enhanced_batch_correction_with_standard(
                        answer_files,
                        file_info_list=saved_files,
                        batch_size=batch_settings['batch_size'],
                        generate_summary=batch_settings['generate_summary']
                    )
                else:
                    # 无标准答案
                    from functions.api_correcting.calling_api import enhanced_batch_correction_without_standard
                    
                    answer_files = [f["path"] for f in saved_files if 'ANSWER' in f["name"].upper()]
                    
                    result = enhanced_batch_correction_without_standard(
                        answer_files,
                        file_info_list=saved_files,
                        batch_size=batch_settings['batch_size'],
                        generate_summary=batch_settings['generate_summary']
                    )
            else:
                # 使用传统批改方式
                result = intelligent_correction_with_files(
                    answer_files=[f["path"] for f in saved_files if 'ANSWER' in f["name"].upper()],
                    marking_scheme_files=[f["path"] for f in saved_files if 'MARKING' in f["name"].upper()],
                    strictness_level="严格"
                )
            
            progress_bar.progress(90)
            status_text.text("✅ 批改完成，正在整理结果...")
            
            if result:
                # 保存结果
                grading_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 生成结果数据
                result_data = {
                    "result": result,
                    "time": grading_time,
                    "files": [f["name"] for f in saved_files],
                    "settings": batch_settings,
                    "type": "enhanced_batch" if batch_settings['enable_batch'] else "traditional"
                }
                
                # 保存到session
                if "grading_results" not in st.session_state:
                    st.session_state.grading_results = []
                st.session_state.grading_results.append(result_data)
                
                # 保存批改结果和文件数据到session state，供结果页面使用
                st.session_state.correction_result = result
                st.session_state.uploaded_files_data = saved_files
                st.session_state.current_file_index = 0  # 初始化文件索引
                
                # 保存批改任务信息
                st.session_state.correction_task = {
                    'status': 'completed',
                    'all_file_info': saved_files,
                    'question_files': [f["path"] for f in saved_files if 'QUESTION' in f["name"].upper()],
                    'answer_files': [f["path"] for f in saved_files if 'ANSWER' in f["name"].upper()],
                    'marking_files': [f["path"] for f in saved_files if 'MARKING' in f["name"].upper()]
                }
                
                # 保存批改设置
                st.session_state.correction_settings = {
                    'has_marking_scheme': bool(marking_files),
                    'strictness': '严格',
                    'use_batch_processing': batch_settings['enable_batch'],
                    'batch_size': batch_settings['batch_size']
                }
                
                progress_bar.progress(100)
                status_text.text("🎉 批改完成！")
                
                st.success("✅ 批改完成！即将跳转到批改详情页面...")
                st.balloons()
                
                # 短暂延迟后跳转到结果页面
                time.sleep(1)
                st.session_state.page = "result"
                st.rerun()
                
            else:
                st.error("❌ 批改失败，请检查文件格式或重试")
                
        except Exception as e:
            import traceback
            st.error(f"❌ 批改过程中出现错误：{str(e)}")
            # 显示详细错误信息
            with st.expander("🔍 查看详细错误信息", expanded=True):
                st.code(traceback.format_exc())
            
        finally:
            progress_bar.empty()
            status_text.empty()

# 新的简化结果页面
def show_result():
    """使用iframe实现完全隔离的滚动区域，支持评分标准和批改结果的切换显示"""
    
    if not st.session_state.logged_in:
        st.warning("请先登录")
        st.session_state.page = "login"
        st.rerun()
        return
    
    # 检查是否有待处理的批改任务
    if 'correction_task' in st.session_state and st.session_state.correction_task.get('status') == 'pending':
        # 执行批改任务
        st.markdown('<h2 class="main-title">🤖 AI批改进行中...</h2>', unsafe_allow_html=True)
        
        # 显示加载动画和设置信息
        progress_container = st.container()
        with progress_container:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("""
                <div style="text-align: center; padding: 50px;">
                    <div class="spinner"></div>
                    <h3 style="color: #3b82f6; margin-top: 30px;">🤖 AI正在智能批改...</h3>
                    <p style="color: #94a3b8; margin-top: 10px;">启用增强版批改系统</p>
                    <p style="color: #64748b; font-size: 0.9em; margin-top: 15px;">🛡️ 防循环 | 🎯 题目范围控制 | ⏸️ 智能暂停</p>
                </div>
                <style>
                .spinner {
                    margin: 0 auto;
                    width: 60px;
                    height: 60px;
                    border: 5px solid rgba(59, 130, 246, 0.1);
                    border-radius: 50%;
                    border-top-color: #3b82f6;
                    animation: spin 1s ease-in-out infinite;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                </style>
                """, unsafe_allow_html=True)
        
        # 执行批改
        with st.spinner(""):
            try:
                task = st.session_state.correction_task
                settings = st.session_state.correction_settings
                
                # 调用AI批改 - 使用增强版API
                from functions.api_correcting.calling_api import enhanced_batch_correction_with_standard, enhanced_batch_correction_without_standard
                
                if settings.get('has_marking_scheme') and task['marking_files']:
                    # 有批改标准模式 - 使用增强版
                    result = enhanced_batch_correction_with_standard(
                        content_list=task['answer_files'],
                        file_info_list=task['all_file_info'],
                        batch_size=settings.get('batch_size', 10),
                        generate_summary=True
                    )
                else:
                    # 无批改标准模式 - 使用增强版
                    result = enhanced_batch_correction_without_standard(
                        content_list=task['answer_files'],
                        file_info_list=task['all_file_info'],
                        batch_size=settings.get('batch_size', 10),
                        generate_summary=True
                    )
                
                # 保存记录
                users = read_users()
                if st.session_state.username in users:
                    record = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'files': [f['display_name'] for f in task['all_file_info']],
                        'file_data': task['all_file_info'],
                        'settings': settings,
                        'result': result,
                        'files_count': len(task['all_file_info'])
                    }
                    users[st.session_state.username]['records'].append(record)
                    save_users(users)
                
                # 保存结果并更新状态
                st.session_state.correction_result = result
                st.session_state.correction_task['status'] = 'completed'
                
                # 刷新页面显示结果
                st.rerun()
                
            except Exception as e:
                st.error(f"批改失败：{str(e)}")
                st.session_state.correction_task['status'] = 'failed'
                if st.button("返回重试"):
                    st.session_state.page = "grading"
                    st.rerun()
                return
    
    st.markdown('<h2 class="main-title">📊 批改结果</h2>', unsafe_allow_html=True)
    
    # 检查批改结果和文件数据
    if not st.session_state.get('correction_result') or not st.session_state.get('uploaded_files_data'):
        st.warning("暂无批改结果或文件数据")
        if st.button("返回批改", use_container_width=True):
            st.session_state.page = "grading"
            st.rerun()
        return
    
    # 获取文件数据和批改结果
    files_data = st.session_state.get('uploaded_files_data', [])
    current_index = st.session_state.get('current_file_index', 0)
    correction_result = st.session_state.get('correction_result')
    
    # 确保索引在有效范围内
    if current_index >= len(files_data):
        st.session_state.current_file_index = 0
        current_index = 0
    
    # 处理新的返回格式（字典格式）
    has_separate_scheme = False
    marking_scheme = None
    correction_content = correction_result
    html_content = None
    
    if isinstance(correction_result, dict):
        # 检查是否是增强版格式（包含HTML）
        if correction_result.get('format') == 'enhanced':
            correction_content = correction_result.get('text', '')
            html_content = correction_result.get('html', '')
        else:
            has_separate_scheme = correction_result.get('has_separate_scheme', False)
            if has_separate_scheme:
                marking_scheme = correction_result.get('marking_scheme', '')
                correction_content = correction_result.get('correction_result', '')
            else:
                correction_content = correction_result.get('correction_result', str(correction_result))
    elif isinstance(correction_result, str):
        correction_content = correction_result
    else:
        correction_content = str(correction_result)
    
    # 创建两列布局
    col_left, col_right = st.columns(2)
    
    # 左侧：文件预览
    with col_left:
        st.markdown("### 📁 文件预览")
        
        # 创建一个包含所有内容的HTML字符串
        if files_data and current_index < len(files_data):
            current_file = files_data[current_index]
            
            # 生成预览内容
            preview_html = generate_file_preview_html(current_file)
            
            # 使用components.html显示
            st.components.v1.html(preview_html, height=520, scrolling=True)
            
            # 文件切换
            if len(files_data) > 1:
                st.markdown("---")
                new_index = st.selectbox(
                    "切换文件",
                    range(len(files_data)),
                    format_func=lambda i: f"{i+1}. {files_data[i]['name']}",
                    index=current_index,
                    key="file_selector_result"
                )
                if new_index != current_index:
                    st.session_state.current_file_index = new_index
                    st.rerun()
    
    # 右侧：批改结果（支持切换显示）
    with col_right:
        # 如果有分离的评分标准，显示切换选项
        if has_separate_scheme and marking_scheme:
            st.markdown("### 📝 批改内容")
            
            # 初始化显示模式
            if 'result_display_mode' not in st.session_state:
                st.session_state.result_display_mode = 'correction'
            
            # 切换按钮
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if st.button("📊 批改结果", use_container_width=True, 
                           type="primary" if st.session_state.result_display_mode == 'correction' else "secondary"):
                    st.session_state.result_display_mode = 'correction'
                    st.rerun()
            
            with col_r2:
                if st.button("📋 评分标准", use_container_width=True,
                           type="primary" if st.session_state.result_display_mode == 'scheme' else "secondary"):
                    st.session_state.result_display_mode = 'scheme'
                    st.rerun()
            
            # 根据选择显示内容
            display_content = marking_scheme if st.session_state.result_display_mode == 'scheme' else correction_content
            content_title = "评分标准" if st.session_state.result_display_mode == 'scheme' else "批改结果"
            
        else:
            st.markdown("### 📝 批改结果")
            display_content = correction_content
            content_title = "批改结果"
        
        # 创建结果HTML
        if html_content and st.session_state.get('result_display_mode', 'correction') == 'correction':
            # 使用增强版HTML格式
            result_html = html_content
        else:
            # 使用原始格式
            result_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        margin: 0;
                        padding: 20px;
                        background: #ffffff;
                        color: #333333;
                        font-family: 'SF Mono', Monaco, monospace;
                        min-height: 100vh;
                        box-sizing: border-box;
                    }}
                    pre {{
                        white-space: pre-wrap;
                        word-wrap: break-word;
                        margin: 0;
                        line-height: 1.6;
                        font-size: 14px;
                    }}
                    ::-webkit-scrollbar {{
                        width: 12px;
                    }}
                    ::-webkit-scrollbar-track {{
                        background: rgba(0, 0, 0, 0.3);
                        border-radius: 6px;
                    }}
                    ::-webkit-scrollbar-thumb {{
                        background: #4a5568;
                        border-radius: 6px;
                    }}
                    ::-webkit-scrollbar-thumb:hover {{
                        background: #60a5fa;
                    }}
                </style>
            </head>
            <body>
                <pre>{html.escape(str(display_content))}</pre>
            </body>
            </html>
            """
        
        # 使用components.html显示
        st.components.v1.html(result_html, height=480, scrolling=True)
    
    # 操作按钮
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # 下载批改结果
        download_content = correction_content
        if has_separate_scheme and marking_scheme:
            download_content = f"=== 评分标准 ===\n\n{marking_scheme}\n\n=== 批改结果 ===\n\n{correction_content}"
        
        st.download_button(
            "📥 下载结果",
            str(download_content),
            file_name="correction_result.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col2:
        # 单独下载评分标准（如果有）
        if has_separate_scheme and marking_scheme:
            st.download_button(
                "📋 下载标准",
                str(marking_scheme),
                file_name="marking_scheme.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.write("")  # 占位
    
    with col3:
        if st.button("🔄 重新批改", use_container_width=True):
            st.session_state.page = "grading"
            st.rerun()
    
    with col4:
        if st.button("📚 查看历史", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()

def generate_file_preview_html(file_data):
    """生成文件预览的完整HTML"""
    
    # 基础HTML模板
    base_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                margin: 0;
                padding: 20px;
                background: #ffffff;
                color: #333333;
                font-family: Arial, sans-serif;
                box-sizing: border-box;
            }}
            .error {{
                text-align: center;
                padding: 50px;
            }}
            img {{
                max-width: 100%;
                height: auto;
                display: block;
                margin: 0 auto;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            }}
            pre {{
                white-space: pre-wrap;
                word-wrap: break-word;
                line-height: 1.6;
                font-family: monospace;
                background: rgba(0,0,0,0.2);
                padding: 15px;
                border-radius: 8px;
                overflow-x: auto;
            }}
            h3 {{
                text-align: center;
                color: #60a5fa;
                margin-bottom: 20px;
            }}
            ::-webkit-scrollbar {{
                width: 12px;
            }}
            ::-webkit-scrollbar-track {{
                background: rgba(0, 0, 0, 0.3);
                border-radius: 6px;
            }}
            ::-webkit-scrollbar-thumb {{
                background: #4a5568;
                border-radius: 6px;
            }}
            ::-webkit-scrollbar-thumb:hover {{
                background: #60a5fa;
            }}
        </style>
    </head>
    <body>
        {content}
    </body>
    </html>
    """
    
    # 检查文件是否存在
    if not file_data.get('path') or not Path(file_data['path']).exists():
        content = '<div class="error"><h3>⚠️ 文件不可用</h3><p>原始文件可能已被移动或删除</p></div>'
        return base_template.format(content=content)
    
    file_type = get_file_type(file_data['name'])
    
    if file_type == 'image':
        # 图片预览
        try:
            image_base64 = get_image_base64(file_data['path'])
            if image_base64:
                content = f'<h3>🖼️ {html.escape(file_data["name"])}</h3><img src="data:image/png;base64,{image_base64}" alt="Preview" />'
            else:
                content = '<div class="error"><p>图片加载失败</p></div>'
        except Exception as e:
            content = f'<div class="error"><p>错误: {html.escape(str(e))}</p></div>'
    
    elif file_type == 'text':
        # 文本预览
        try:
            with open(file_data['path'], 'r', encoding='utf-8') as f:
                text_content = f.read()
            content = f'<h3>📄 {html.escape(file_data["name"])}</h3><pre>{html.escape(text_content)}</pre>'
        except Exception as e:
            content = f'<div class="error"><p>错误: {html.escape(str(e))}</p></div>'
    
    elif file_type == 'pdf':
        # PDF预览功能
        try:
            from functions.api_correcting.calling_api import pdf_pages_to_base64_images
            pdf_images = pdf_pages_to_base64_images(file_data['path'], zoom=1.5)
            
            if pdf_images:
                # 构建PDF预览HTML
                pdf_pages_html = ""
                total_pages = len(pdf_images)
                
                for i, img_base64 in enumerate(pdf_images):
                    # 页面指示器
                    page_indicator = f'<div style="position: sticky; top: 0; z-index: 5; background: rgba(74, 85, 104, 0.95); backdrop-filter: blur(8px); color: #e2e8f0; font-size: 0.85rem; margin: 0 -20px 20px -20px; padding: 12px 20px; font-weight: 600; text-align: center; border-bottom: 2px solid rgba(96, 165, 250, 0.3); box-shadow: 0 2px 8px rgba(0,0,0,0.3);">📄 第 {i+1} 页 / 共 {total_pages} 页</div>'
                    
                    # PDF页面图片
                    page_content = f'<div style="margin-bottom: 40px; width: 100%; text-align: center;"><img src="data:image/png;base64,{img_base64}" style="width: 100%; height: auto; max-width: 100%; border: 3px solid #4a5568; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.3); background-color: white; object-fit: contain; display: block; margin: 0 auto; transition: transform 0.3s ease, box-shadow 0.3s ease;" onmouseover="this.style.transform=\'scale(1.02)\'; this.style.boxShadow=\'0 12px 24px rgba(0,0,0,0.4)\'" onmouseout="this.style.transform=\'scale(1)\'; this.style.boxShadow=\'0 8px 16px rgba(0,0,0,0.3)\'" alt="PDF 第{i+1}页" /></div>'
                    
                    pdf_pages_html += page_indicator + page_content
                
                # 添加底部导航提示
                navigation_hint = '<div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 0.9rem; border-top: 1px solid rgba(74, 85, 104, 0.3); margin-top: 20px; background: rgba(45, 55, 72, 0.5); border-radius: 8px;"><span style="background: rgba(96, 165, 250, 0.1); padding: 6px 12px; border-radius: 20px; border: 1px solid rgba(96, 165, 250, 0.3);">💡 使用鼠标滚轮浏览多页PDF内容</span></div>'
                
                content = f'<h3>📄 {html.escape(file_data["name"])}</h3>{pdf_pages_html}{navigation_hint}'
            else:
                content = f'<div class="error"><h3>📄 PDF文件</h3><p>{html.escape(file_data["name"])}</p><p>PDF转换失败，请检查文件格式</p></div>'
        except Exception as e:
            content = f'<div class="error"><h3>📄 PDF文件</h3><p>{html.escape(file_data["name"])}</p><p>PDF预览失败: {html.escape(str(e))}</p><p>请确保PyMuPDF库已正确安装</p></div>'
    
    else:
        # 其他文件类型
        content = f'<div class="error"><h3>📄 {html.escape(file_data["name"])}</h3><p>文件类型: {file_type}</p><p>此类型暂不支持预览</p></div>'
    
    return base_template.format(content=content)

# 批改结果展示页面 - 左右对照布局（原始版本，备份）
def show_result_original():
    if not st.session_state.logged_in:
        st.warning("请先登录")
        st.session_state.page = "login"
        st.rerun()
        return
    
    # 检查是否有待处理的批改任务
    if 'correction_task' in st.session_state and st.session_state.correction_task.get('status') == 'pending':
        # 执行批改任务
        st.markdown('<h2 class="main-title">🤖 AI批改进行中...</h2>', unsafe_allow_html=True)
        
        # 显示加载动画
        progress_container = st.container()
        with progress_container:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("""
                <div style="text-align: center; padding: 50px;">
                    <div class="spinner"></div>
                    <h3 style="color: #3b82f6; margin-top: 30px;">🤖 AI正在分析文件...</h3>
                    <p style="color: #94a3b8; margin-top: 10px;">请稍候，这可能需要几秒钟</p>
                </div>
                <style>
                .spinner {
                    margin: 0 auto;
                    width: 60px;
                    height: 60px;
                    border: 5px solid rgba(59, 130, 246, 0.1);
                    border-radius: 50%;
                    border-top-color: #3b82f6;
                    animation: spin 1s ease-in-out infinite;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                </style>
                """, unsafe_allow_html=True)
        
        # 执行批改
        with st.spinner(""):
            try:
                task = st.session_state.correction_task
                settings = st.session_state.correction_settings
                
                # 调用AI批改 - 使用新的简化API
                if settings.get('has_marking_scheme') and task['marking_files']:
                    # 有批改标准模式
                    result = batch_correction_with_standard(
                    marking_scheme_files=task['marking_files'],
                        student_answer_files=task['answer_files'],
                        strictness_level=settings['strictness']
                    )
                else:
                    # 无批改标准模式
                    result = batch_correction_without_standard(
                        question_files=task['question_files'],
                        student_answer_files=task['answer_files'],
                        strictness_level=settings['strictness']
                )
                
                # 保存记录
                users = read_users()
                if st.session_state.username in users:
                    record = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'files': [f['display_name'] for f in task['all_file_info']],
                        'file_data': task['all_file_info'],
                        'settings': settings,
                        'result': result,
                        'files_count': len(task['all_file_info'])
                    }
                    users[st.session_state.username]['records'].append(record)
                    save_users(users)
                
                # 保存结果并更新状态
                st.session_state.correction_result = result
                st.session_state.correction_task['status'] = 'completed'
                
                # 刷新页面显示结果
                st.rerun()
                
            except Exception as e:
                st.error(f"批改失败：{str(e)}")
                st.session_state.correction_task['status'] = 'failed'
                if st.button("返回重试"):
                    st.session_state.page = "grading"
                    st.rerun()
                return
    
    # 检查是否有批改结果
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
        mode_text = "有批改标准" if settings.get('has_marking_scheme') else "自动生成标准"
        st.markdown(f"**设置：** {mode_text} | {settings.get('strictness', 'N/A')}")
    
    with col2:
        if st.button("🔄 重新批改"):
            st.session_state.page = "grading"
            st.rerun()
    
    with col3:
        filename = f"correction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        # 处理下载数据，确保是字符串格式
        result_data = st.session_state.correction_result
        if isinstance(result_data, dict):
            if result_data.get('has_separate_scheme', False):
                marking_scheme = result_data.get('marking_scheme', '')
                correction_content = result_data.get('correction_result', '')
                download_content = f"=== 评分标准 ===\n\n{marking_scheme}\n\n=== 批改结果 ===\n\n{correction_content}"
            else:
                download_content = str(result_data.get('correction_result', result_data))
        else:
            download_content = str(result_data)
        
        st.download_button("💾 下载结果", 
                         data=download_content, 
                         file_name=filename, 
                         mime="text/plain")
    
    with col4:
        if st.button("🏠 返回首页"):
            st.session_state.page = "home"
            st.rerun()
    
    st.markdown("---")
    
    # 添加CSS样式确保完美对齐
    st.markdown("""
    <style>
    .stColumn > div {
        height: auto;
    }
    .stTextArea > div > div > textarea {
        font-family: 'Courier New', monospace;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 创建左右两列，完全等宽
    col_left, col_right = st.columns([1, 1])
    
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
                
                # 创建统一的文件预览容器 - 强制限制在框内
                st.markdown("""
                <style>
                .file-preview-frame {
                    height: 520px !important;
                    max-height: 520px !important;
                    overflow: hidden !important;
                    border: 3px solid #4a5568;
                    border-radius: 12px;
                    padding: 0 !important;
                    margin: 0 !important;
                    background-color: #1a202c;
                    margin-bottom: 20px;
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
                    position: relative;
                    box-sizing: border-box !important;
                    cursor: default !important;
                }
                .preview-content-wrapper {
                    height: 100% !important;
                    max-height: 520px !important;
                    width: 100% !important;
                    overflow-y: auto !important;
                    overflow-x: hidden !important;
                    padding: 15px;
                    background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
                    box-sizing: border-box !important;
                    display: block !important;
                }
                .preview-image-container {
                    width: 100% !important;
                    height: auto !important;
                    max-width: 100% !important;
                    text-align: center;
                    padding: 10px;
                    box-sizing: border-box !important;
                }
                .preview-image {
                    max-width: calc(100% - 20px) !important;
                    max-height: 450px !important;
                    height: auto !important;
                    width: auto !important;
                    border: 2px solid #4a5568;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    background-color: white;
                    object-fit: contain !important;
                    display: block !important;
                    margin: 0 auto !important;
                }
                .pdf-page-container {
                    margin-bottom: 25px;
                    text-align: center;
                    width: 100% !important;
                    max-width: 100% !important;
                    box-sizing: border-box !important;
                    padding: 0 10px;
                }
                .pdf-page-container img {
                    max-width: calc(100% - 20px) !important;
                    max-height: 400px !important;
                    height: auto !important;
                    width: auto !important;
                    border: 2px solid #4a5568;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    background-color: white;
                    object-fit: contain !important;
                    display: block !important;
                    margin: 0 auto !important;
                }
                .page-number-badge {
                    color: #e2e8f0;
                    font-size: 0.9rem;
                    margin-bottom: 10px;
                    font-weight: 600;
                    background-color: #4a5568;
                    padding: 6px 16px;
                    border-radius: 20px;
                    display: inline-block;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }
                .preview-text-content {
                    width: calc(100% - 20px) !important;
                    height: calc(100% - 40px) !important;
                    max-height: 450px !important;
                    background-color: #2d3748;
                    border: 2px solid #4a5568;
                    border-radius: 8px;
                    padding: 20px;
                    color: #e2e8f0;
                    font-family: 'Courier New', monospace;
                    font-size: 0.9rem;
                    line-height: 1.6;
                    overflow-y: auto !important;
                    overflow-x: hidden !important;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
                    box-sizing: border-box !important;
                    margin: 10px auto;
                }
                .preview-placeholder {
                    display: flex !important;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    height: calc(100% - 30px) !important;
                    max-height: 490px !important;
                    text-align: center;
                    color: #a0aec0;
                    padding: 15px;
                    box-sizing: border-box !important;
                }
                .preview-placeholder h3 {
                    color: #f6ad55;
                    margin-bottom: 20px;
                    font-size: 1.5rem;
                }
                .preview-placeholder p {
                    font-size: 1.1rem;
                    margin-bottom: 10px;
                }
                /* 强制覆盖Streamlit默认样式 */
                .file-preview-frame * {
                    max-width: 100% !important;
                    box-sizing: border-box !important;
                }
                .file-preview-frame img {
                    max-width: calc(100% - 40px) !important;
                    max-height: 450px !important;
                    object-fit: contain !important;
                }
                /* 隐藏Streamlit的图片容器溢出 */
                .file-preview-frame .stImage {
                    max-width: 100% !important;
                    overflow: hidden !important;
                }
                .file-preview-frame .stImage > div {
                    max-width: 100% !important;
                    overflow: hidden !important;
                }
                /* 终极强制限制 - 不计一切代价 */
                .file-preview-frame,
                .file-preview-frame *,
                .file-preview-frame img,
                .file-preview-frame .preview-image,
                .file-preview-frame .preview-image-container,
                .file-preview-frame .preview-content-wrapper {
                    max-width: 100% !important;
                    max-height: 520px !important;
                    overflow: hidden !important;
                    box-sizing: border-box !important;
                }
                .file-preview-frame img {
                    width: auto !important;
                    height: auto !important;
                    max-width: calc(100% - 60px) !important;
                    max-height: 400px !important;
                    object-fit: contain !important;
                    object-position: center !important;
                }
                /* 强制所有子元素都不能超出父容器 */
                .file-preview-frame > * {
                    contain: layout size !important;
                }
                
                /* 自定义滚动条样式 - 针对预览框 */
                .file-preview-frame .preview-content-wrapper::-webkit-scrollbar {
                    width: 14px;
                    height: 14px;
                }
                .file-preview-frame .preview-content-wrapper::-webkit-scrollbar-track {
                    background: rgba(0, 0, 0, 0.4);
                    border-radius: 8px;
                    border: 1px solid rgba(74, 85, 104, 0.3);
                }
                .file-preview-frame .preview-content-wrapper::-webkit-scrollbar-thumb {
                    background: linear-gradient(135deg, #4a5568, #2d3748);
                    border-radius: 8px;
                    border: 2px solid rgba(0, 0, 0, 0.2);
                    transition: all 0.3s ease;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }
                .file-preview-frame .preview-content-wrapper::-webkit-scrollbar-thumb:hover {
                    background: linear-gradient(135deg, #60a5fa, #3b82f6);
                    transform: scale(1.05);
                    box-shadow: 0 4px 8px rgba(96, 165, 250, 0.3);
                }
                .file-preview-frame .preview-content-wrapper::-webkit-scrollbar-thumb:active {
                    background: linear-gradient(135deg, #2563eb, #1d4ed8);
                }
                .file-preview-frame .preview-content-wrapper::-webkit-scrollbar-corner {
                    background: rgba(0, 0, 0, 0.4);
                    border-radius: 8px;
                }
                
                /* 确保预览框可以正确响应滚轮事件 */
                .file-preview-frame {
                    position: relative;
                    z-index: 1;
                    user-select: none;
                    -webkit-user-select: none;
                    -moz-user-select: none;
                    -ms-user-select: none;
                }
                .file-preview-frame .preview-content-wrapper {
                    position: relative;
                    z-index: 2;
                    cursor: default;
                    scroll-behavior: smooth;
                    overflow-scrolling: touch; /* iOS平滑滚动 */
                }
                
                /* 增强滚轮响应性 */
                .file-preview-frame .preview-content-wrapper {
                    overscroll-behavior: contain;
                    scroll-snap-type: none;
                }
                
                /* 鼠标悬停时的视觉反馈 */
                .file-preview-frame:hover {
                    border-color: #60a5fa;
                    box-shadow: 0 12px 24px rgba(0,0,0,0.4), 0 0 0 1px rgba(96, 165, 250, 0.3);
                    transition: all 0.3s ease;
                }
                
                /* 滚动指示器 */
                .file-preview-frame::before {
                    content: "⚡ 可滚动预览";
                    position: absolute;
                    top: 8px;
                    right: 12px;
                    background: rgba(96, 165, 250, 0.8);
                    color: white;
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 0.7rem;
                    font-weight: 600;
                    z-index: 10;
                    opacity: 0;
                    transition: opacity 0.3s ease;
                    pointer-events: none;
                }
                .file-preview-frame:hover::before {
                    opacity: 1;
                }
                
                /* 键盘导航支持 */
                .file-preview-frame {
                    outline: none;
                }
                .file-preview-frame:focus {
                    border-color: #60a5fa;
                    box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.2);
                }
                </style>
                
                <script>
                // 增强滚轮响应性和键盘导航 - 修复页面滚动问题
                (function() {
                    // 立即执行的函数，不等待DOMContentLoaded
                    function setupPreviewScrolling() {
                        console.log('Setting up preview scrolling...');
                        
                        // 获取所有预览框和批改结果框
                        const previewFrames = document.querySelectorAll('.file-preview-frame');
                        const resultFrames = document.querySelectorAll('.correction-result-frame');
                        
                        console.log('Found preview frames:', previewFrames.length);
                        console.log('Found result frames:', resultFrames.length);
                        
                        // 处理预览框
                        previewFrames.forEach((previewFrame, index) => {
                            const contentWrapper = previewFrame.querySelector('.preview-content-wrapper');
                            
                            if (contentWrapper) {
                                console.log('Setting up preview frame', index);
                                
                                // 移除可能存在的旧事件监听器
                                const newFrame = previewFrame.cloneNode(true);
                                previewFrame.parentNode.replaceChild(newFrame, previewFrame);
                                
                                const newContentWrapper = newFrame.querySelector('.preview-content-wrapper');
                                
                                // 预览框滚轮事件 - 完全阻止冒泡
                                newFrame.addEventListener('wheel', function(e) {
                                    // 完全阻止事件传播
                                    e.preventDefault();
                                    e.stopPropagation();
                                    e.stopImmediatePropagation();
                                    
                                    // 检查是否可以滚动
                                    const canScrollDown = newContentWrapper.scrollTop < (newContentWrapper.scrollHeight - newContentWrapper.clientHeight - 1);
                                    const canScrollUp = newContentWrapper.scrollTop > 0;
                                    
                                    // 只有在可以滚动时才处理滚轮事件
                                    if ((e.deltaY > 0 && canScrollDown) || (e.deltaY < 0 && canScrollUp)) {
                                        // 自定义滚动行为
                                        const scrollAmount = e.deltaY;
                                        newContentWrapper.scrollTop += scrollAmount;
                                    }
                                    
                                    return false;
                                }, { passive: false, capture: true });
                                
                                // 鼠标进入预览框时的处理
                                newFrame.addEventListener('mouseenter', function(e) {
                                    // 添加视觉反馈
                                    newFrame.style.borderColor = '#60a5fa';
                                    newFrame.style.boxShadow = '0 12px 24px rgba(0,0,0,0.4), 0 0 0 1px rgba(96, 165, 250, 0.3)';
                                    
                                    // 设置焦点以支持键盘导航
                                    newFrame.setAttribute('tabindex', '0');
                                    newFrame.focus();
                                });
                                
                                // 鼠标离开预览框时的处理
                                newFrame.addEventListener('mouseleave', function(e) {
                                    // 恢复原始样式
                                    newFrame.style.borderColor = '#4a5568';
                                    newFrame.style.boxShadow = '0 8px 16px rgba(0,0,0,0.3)';
                                });
                                
                                // 键盘导航支持
                                newFrame.addEventListener('keydown', function(e) {
                                    switch(e.key) {
                                        case 'ArrowUp':
                                            e.preventDefault();
                                            e.stopPropagation();
                                            newContentWrapper.scrollBy({ top: -50, behavior: 'smooth' });
                                            break;
                                        case 'ArrowDown':
                                            e.preventDefault();
                                            e.stopPropagation();
                                            newContentWrapper.scrollBy({ top: 50, behavior: 'smooth' });
                                            break;
                                        case 'PageUp':
                                            e.preventDefault();
                                            e.stopPropagation();
                                            newContentWrapper.scrollBy({ top: -300, behavior: 'smooth' });
                                            break;
                                        case 'PageDown':
                                            e.preventDefault();
                                            e.stopPropagation();
                                            newContentWrapper.scrollBy({ top: 300, behavior: 'smooth' });
                                            break;
                                        case 'Home':
                                            e.preventDefault();
                                            e.stopPropagation();
                                            newContentWrapper.scrollTo({ top: 0, behavior: 'smooth' });
                                            break;
                                        case 'End':
                                            e.preventDefault();
                                            e.stopPropagation();
                                            newContentWrapper.scrollTo({ top: newContentWrapper.scrollHeight, behavior: 'smooth' });
                                            break;
                                    }
                                });
                            }
                        });
                         
                         // 处理批改结果框
                         resultFrames.forEach((resultFrame, index) => {
                             const contentWrapper = resultFrame.querySelector('.result-content-wrapper');
                             
                             if (contentWrapper) {
                                 console.log('Setting up result frame', index);
                                 
                                 // 移除可能存在的旧事件监听器
                                 const newFrame = resultFrame.cloneNode(true);
                                 resultFrame.parentNode.replaceChild(newFrame, resultFrame);
                                 
                                 const newContentWrapper = newFrame.querySelector('.result-content-wrapper');
                                 
                                 // 批改结果框滚轮事件 - 完全阻止冒泡
                                 newFrame.addEventListener('wheel', function(e) {
                                     // 完全阻止事件传播
                                     e.preventDefault();
                                     e.stopPropagation();
                                     e.stopImmediatePropagation();
                                     
                                     // 检查是否可以滚动
                                     const canScrollDown = newContentWrapper.scrollTop < (newContentWrapper.scrollHeight - newContentWrapper.clientHeight - 1);
                                     const canScrollUp = newContentWrapper.scrollTop > 0;
                                     
                                     // 只有在可以滚动时才处理滚轮事件
                                     if ((e.deltaY > 0 && canScrollDown) || (e.deltaY < 0 && canScrollUp)) {
                                         // 自定义滚动行为
                                         const scrollAmount = e.deltaY;
                                         newContentWrapper.scrollTop += scrollAmount;
                                     }
                                     
                                     return false;
                                 }, { passive: false, capture: true });
                                 
                                 // 鼠标进入批改结果框时的处理
                                 newFrame.addEventListener('mouseenter', function(e) {
                                     // 添加视觉反馈
                                     newFrame.style.borderColor = '#60a5fa';
                                     newFrame.style.boxShadow = '0 12px 24px rgba(0,0,0,0.4), 0 0 0 1px rgba(96, 165, 250, 0.3)';
                                     
                                     // 设置焦点以支持键盘导航
                                     newFrame.setAttribute('tabindex', '0');
                                     newFrame.focus();
                                 });
                                 
                                 // 鼠标离开批改结果框时的处理
                                 newFrame.addEventListener('mouseleave', function(e) {
                                     // 恢复原始样式
                                     newFrame.style.borderColor = '#4a5568';
                                     newFrame.style.boxShadow = '0 8px 16px rgba(0,0,0,0.3)';
                                 });
                                 
                                 // 键盘导航支持
                                 newFrame.addEventListener('keydown', function(e) {
                                     switch(e.key) {
                                         case 'ArrowUp':
                                             e.preventDefault();
                                             e.stopPropagation();
                                             newContentWrapper.scrollBy({ top: -50, behavior: 'smooth' });
                                             break;
                                         case 'ArrowDown':
                                             e.preventDefault();
                                             e.stopPropagation();
                                             newContentWrapper.scrollBy({ top: 50, behavior: 'smooth' });
                                             break;
                                         case 'PageUp':
                                             e.preventDefault();
                                             e.stopPropagation();
                                             newContentWrapper.scrollBy({ top: -300, behavior: 'smooth' });
                                             break;
                                         case 'PageDown':
                                             e.preventDefault();
                                             e.stopPropagation();
                                             newContentWrapper.scrollBy({ top: 300, behavior: 'smooth' });
                                             break;
                                         case 'Home':
                                             e.preventDefault();
                                             e.stopPropagation();
                                             newContentWrapper.scrollTo({ top: 0, behavior: 'smooth' });
                                             break;
                                         case 'End':
                                             e.preventDefault();
                                             e.stopPropagation();
                                             newContentWrapper.scrollTo({ top: newContentWrapper.scrollHeight, behavior: 'smooth' });
                                             break;
                                     }
                                 });
                             }
                         });
                     }
                     
                     // 延迟初始化，确保DOM完全加载
                     setTimeout(setupPreviewScrolling, 100);
                     setTimeout(setupPreviewScrolling, 500);
                     setTimeout(setupPreviewScrolling, 1000);
                    
                    // 监听DOM变化，重新初始化滚动
                    const observer = new MutationObserver(function(mutations) {
                        mutations.forEach(function(mutation) {
                            if (mutation.type === 'childList') {
                                const addedNodes = Array.from(mutation.addedNodes);
                                if (addedNodes.some(node => node.nodeType === 1 && (
                                    node.classList && (node.classList.contains('file-preview-frame') || node.classList.contains('correction-result-frame')) ||
                                    (node.querySelector && (node.querySelector('.file-preview-frame') || node.querySelector('.correction-result-frame')))
                                ))) {
                                    setTimeout(setupPreviewScrolling, 100);
                                }
                            }
                        });
                    });
                    
                    // 开始观察DOM变化
                    if (document.body) {
                        observer.observe(document.body, {
                            childList: true,
                            subtree: true
                        });
                    }
                    
                    // 确保在DOM加载完成后也执行
                    if (document.readyState === 'loading') {
                        document.addEventListener('DOMContentLoaded', setupPreviewScrolling);
                    } else {
                        setupPreviewScrolling();
                    }
                })();
                </script>
                
                /* 图片和内容的悬停效果 */
                .file-preview-frame img:hover {
                    transform: scale(1.02);
                    transition: transform 0.3s ease;
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
                }
                </style>
                """, unsafe_allow_html=True)
                
                # 完全自定义的文件预览容器 - 强制HTML内嵌
                preview_html = ""
                
                if current_file['path'] and Path(current_file['path']).exists():
                    file_type = get_file_type(current_file['name'])
                    
                    if file_type == 'image':
                        try:
                            # 获取图片的base64编码
                            image_base64 = get_image_base64(current_file['path'])
                            if not image_base64:
                                # 尝试重新获取base64
                                import base64
                                with open(current_file['path'], "rb") as img_file:
                                    image_base64 = base64.b64encode(img_file.read()).decode()
                            
                            if image_base64:
                                file_ext = current_file['path'].split('.')[-1].lower()
                                mime_type = f"image/{file_ext}" if file_ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'] else "image/jpeg"
                                
                                # 图片预览HTML - 优化滚动和缩放体验
                                image_info = f'<div class="image-info-bar" style="position: sticky; top: 0; z-index: 5; background: rgba(74, 85, 104, 0.95); backdrop-filter: blur(8px); color: #e2e8f0; font-size: 0.85rem; margin: 0 -10px 20px -10px; padding: 12px 20px; font-weight: 600; text-align: center; border-bottom: 2px solid rgba(96, 165, 250, 0.3); box-shadow: 0 2px 8px rgba(0,0,0,0.3);">🖼️ 图片预览: {current_file["name"]}</div>'
                                
                                image_content = f'<div class="image-container" style="text-align: center; width: 100%; position: relative; margin-bottom: 20px;"><img src="data:{mime_type};base64,{image_base64}" style="max-width: 100%; height: auto; max-height: 600px; border: 3px solid #4a5568; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.3); background-color: white; object-fit: contain; display: block; margin: 0 auto; transition: transform 0.3s ease, box-shadow 0.3s ease; cursor: zoom-in;" onmouseover="this.style.transform=\'scale(1.05)\'; this.style.boxShadow=\'0 12px 24px rgba(0,0,0,0.4)\'" onmouseout="this.style.transform=\'scale(1)\'; this.style.boxShadow=\'0 8px 16px rgba(0,0,0,0.3)\'" alt="{current_file["name"]}" /></div>'
                                
                                navigation_hint = '<div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 0.9rem; border-top: 1px solid rgba(74, 85, 104, 0.3); margin-top: 20px; background: rgba(45, 55, 72, 0.5); border-radius: 8px;"><span style="background: rgba(96, 165, 250, 0.1); padding: 6px 12px; border-radius: 20px; border: 1px solid rgba(96, 165, 250, 0.3);">💡 鼠标悬停可放大预览，滚轮可上下滚动</span></div>'
                                
                                preview_html = f'<div class="file-preview-frame" onwheel="event.preventDefault(); event.stopPropagation(); var wrapper = this.querySelector(\'.preview-content-wrapper\'); if(wrapper) {{ var canScrollDown = wrapper.scrollTop < (wrapper.scrollHeight - wrapper.clientHeight - 1); var canScrollUp = wrapper.scrollTop > 0; if ((event.deltaY > 0 && canScrollDown) || (event.deltaY < 0 && canScrollUp)) {{ wrapper.scrollTop += event.deltaY; }} }} return false;" style="overscroll-behavior: contain;"><div class="preview-content-wrapper" style="height: 520px; overflow-y: auto; overflow-x: hidden; padding: 10px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); scroll-behavior: smooth; position: relative; overscroll-behavior: contain; -webkit-overflow-scrolling: touch;">{image_info}{image_content}{navigation_hint}</div></div>'
                            else:
                                raise Exception("图片base64转换失败")
                        except Exception as e:
                            preview_html = f'<div class="file-preview-frame" style="overscroll-behavior: contain;"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); overscroll-behavior: contain;"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">📷 图片预览失败</h3><p style="font-size: 1.1rem; margin-bottom: 10px;">错误信息: {str(e)}</p></div></div>'
                    
                    elif file_type == 'pdf':
                        try:
                            # PDF文件转换为图片预览
                            from functions.api_correcting.calling_api import pdf_pages_to_base64_images
                            pdf_images = pdf_pages_to_base64_images(current_file['path'], zoom=1.5)
                            
                            if pdf_images:
                                # 构建PDF预览HTML - 优化滚动体验
                                pdf_pages_html = ""
                                total_pages = len(pdf_images)
                                
                                for i, img_base64 in enumerate(pdf_images):
                                    # 页面分隔和页码指示器
                                    page_indicator = f'<div class="pdf-page-indicator" style="position: sticky; top: 0; z-index: 5; background: rgba(74, 85, 104, 0.95); backdrop-filter: blur(8px); color: #e2e8f0; font-size: 0.85rem; margin: 0 -10px 20px -10px; padding: 12px 20px; font-weight: 600; text-align: center; border-bottom: 2px solid rgba(96, 165, 250, 0.3); box-shadow: 0 2px 8px rgba(0,0,0,0.3);">📄 第 {i+1} 页 / 共 {total_pages} 页</div>'
                                    
                                    # PDF页面图片
                                    page_content = f'<div class="pdf-page-container" style="margin-bottom: 40px; width: 100%; position: relative;"><img src="data:image/png;base64,{img_base64}" style="width: 100%; height: auto; max-width: 100%; border: 3px solid #4a5568; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.3); background-color: white; object-fit: contain; display: block; transition: transform 0.3s ease, box-shadow 0.3s ease;" onmouseover="this.style.transform=\'scale(1.02)\'; this.style.boxShadow=\'0 12px 24px rgba(0,0,0,0.4)\'" onmouseout="this.style.transform=\'scale(1)\'; this.style.boxShadow=\'0 8px 16px rgba(0,0,0,0.3)\'" alt="PDF 第{i+1}页" /></div>'
                                    
                                    pdf_pages_html += page_indicator + page_content
                                
                                # 添加底部导航提示
                                navigation_hint = '<div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 0.9rem; border-top: 1px solid rgba(74, 85, 104, 0.3); margin-top: 20px; background: rgba(45, 55, 72, 0.5); border-radius: 8px;"><span style="background: rgba(96, 165, 250, 0.1); padding: 6px 12px; border-radius: 20px; border: 1px solid rgba(96, 165, 250, 0.3);">💡 使用鼠标滚轮或拖拽滚动条浏览多页内容</span></div>'
                                
                                preview_html = f'<div class="file-preview-frame" onwheel="event.preventDefault(); event.stopPropagation(); var wrapper = this.querySelector(\'.preview-content-wrapper\'); if(wrapper) {{ var canScrollDown = wrapper.scrollTop < (wrapper.scrollHeight - wrapper.clientHeight - 1); var canScrollUp = wrapper.scrollTop > 0; if ((event.deltaY > 0 && canScrollDown) || (event.deltaY < 0 && canScrollUp)) {{ wrapper.scrollTop += event.deltaY; }} }} return false;" style="overscroll-behavior: contain;"><div class="preview-content-wrapper" style="height: 520px; overflow-y: auto; overflow-x: hidden; padding: 10px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); scroll-behavior: smooth; position: relative; overscroll-behavior: contain; -webkit-overflow-scrolling: touch;">{pdf_pages_html}{navigation_hint}</div></div>'
                            else:
                                raise Exception("PDF转换为图片失败")
                        except Exception as e:
                            preview_html = f'<div class="file-preview-frame"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">📄 PDF 预览失败</h3><p style="font-size: 1.1rem; margin-bottom: 10px;">错误信息: {str(e)}</p><p style="font-size: 0.9rem;">请确保PyMuPDF库已正确安装</p></div></div>'
                    
                    elif file_type == 'text':
                        try:
                            with open(current_file['path'], 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            if len(content) > 5000:
                                content = content[:5000] + "\n\n...(内容已截断，可滚动查看)"
                            
                            # HTML转义处理
                            import html
                            content_escaped = html.escape(content)
                            
                            # 文本文件预览HTML - 优化滚动和阅读体验
                            file_info = f'<div class="text-info-bar" style="position: sticky; top: 0; z-index: 5; background: rgba(74, 85, 104, 0.95); backdrop-filter: blur(8px); color: #e2e8f0; font-size: 0.85rem; margin: 0 -10px 20px -10px; padding: 12px 20px; font-weight: 600; text-align: center; border-bottom: 2px solid rgba(96, 165, 250, 0.3); box-shadow: 0 2px 8px rgba(0,0,0,0.3);">📄 文本预览: {current_file["name"]} ({len(content)} 字符)</div>'
                            
                            text_content = f'<div class="text-content-area" style="width: 100%; min-height: 400px; background-color: #2d3748; border: 3px solid #4a5568; border-radius: 12px; padding: 25px; color: #e2e8f0; font-family: \'SF Mono\', \'Monaco\', \'Inconsolata\', \'Roboto Mono\', \'Source Code Pro\', monospace; font-size: 0.95rem; line-height: 1.7; white-space: pre-wrap; word-wrap: break-word; box-shadow: 0 8px 16px rgba(0,0,0,0.3), inset 0 2px 4px rgba(0,0,0,0.1); box-sizing: border-box; transition: all 0.3s ease; position: relative;">{content_escaped}</div>'
                            
                            navigation_hint = '<div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 0.9rem; border-top: 1px solid rgba(74, 85, 104, 0.3); margin-top: 20px; background: rgba(45, 55, 72, 0.5); border-radius: 8px;"><span style="background: rgba(96, 165, 250, 0.1); padding: 6px 12px; border-radius: 20px; border: 1px solid rgba(96, 165, 250, 0.3);">💡 使用滚轮浏览文本内容，支持全文搜索</span></div>'
                            
                            preview_html = f'<div class="file-preview-frame" onwheel="event.preventDefault(); event.stopPropagation(); var wrapper = this.querySelector(\'.preview-content-wrapper\'); if(wrapper) {{ var canScrollDown = wrapper.scrollTop < (wrapper.scrollHeight - wrapper.clientHeight - 1); var canScrollUp = wrapper.scrollTop > 0; if ((event.deltaY > 0 && canScrollDown) || (event.deltaY < 0 && canScrollUp)) {{ wrapper.scrollTop += event.deltaY; }} }} return false;" style="overscroll-behavior: contain;"><div class="preview-content-wrapper" style="height: 520px; overflow-y: auto; overflow-x: hidden; padding: 10px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); scroll-behavior: smooth; position: relative; overscroll-behavior: contain; -webkit-overflow-scrolling: touch;">{file_info}{text_content}{navigation_hint}</div></div>'
                            
                        except Exception as e:
                            preview_html = f'<div class="file-preview-frame"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">📄 文本预览失败</h3><p style="font-size: 1.1rem; margin-bottom: 10px;">错误信息: {str(e)}</p></div></div>'
                    
                    else:
                        preview_html = f'<div class="file-preview-frame"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">📄 {file_type.upper()} 文件</h3><p style="font-size: 1.1rem; margin-bottom: 10px;">此文件类型暂不支持预览</p></div></div>'
                else:
                    # 文件不存在的情况
                    warning_msg = "💡 历史记录，原始文件可能已被清理" if not current_file['path'] else "⚠️ 原始文件不存在"
                    preview_html = f'<div class="file-preview-frame"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">⚠️ 文件预览不可用</h3><p style="font-size: 1.1rem; margin-bottom: 10px;">{warning_msg}</p></div></div>'
                
                # 显示完整的预览HTML
                st.markdown(preview_html, unsafe_allow_html=True)
                
                # 文件信息和切换器放在预览框下方
                st.markdown("---")
                
                # 当前文件信息
                category = current_file.get('category', 'other')
                category_icons = {
                    'question': '📋',
                    'answer': '✏️', 
                    'marking': '📊',
                    'other': '📄'
                }
                category_names = {
                    'question': '题目文件',
                    'answer': '学生作答',
                    'marking': '批改标准',
                    'other': '其他文件'
                }
                
                icon = category_icons.get(category, '📄')
                name = category_names.get(category, '其他文件')
                file_type_display = current_file.get('type', get_file_type(current_file['name']))
                
                st.info(f"{icon} **{name}**: {current_file['name']} ({file_type_display})")
                
            else:
                # 没有文件时的显示
                preview_html = '<div class="file-preview-frame"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">📁 没有可预览的文件</h3><p style="font-size: 1.1rem; margin-bottom: 10px;">请先上传文件进行批改</p></div></div>'
                st.markdown(preview_html, unsafe_allow_html=True)
    
    with col_right:
        st.markdown("### 📝 批改结果")
                
        # 批改结果容器 - 与左侧预览框对齐，支持独立滚轮控制
        if st.session_state.correction_result:
            # 创建与左侧相同样式的容器，使用相同的class名称
            import html
            result_html = f'''
            <div class="correction-result-frame" onwheel="event.preventDefault(); event.stopPropagation(); var wrapper = this.querySelector('.result-content-wrapper'); if(wrapper) {{ var canScrollDown = wrapper.scrollTop < (wrapper.scrollHeight - wrapper.clientHeight - 1); var canScrollUp = wrapper.scrollTop > 0; if ((event.deltaY > 0 && canScrollDown) || (event.deltaY < 0 && canScrollUp)) {{ wrapper.scrollTop += event.deltaY; }} }} return false;" style="height: 520px; border: 3px solid #4a5568; border-radius: 12px; background-color: #1a202c; box-shadow: 0 8px 16px rgba(0,0,0,0.3); overflow: hidden; position: relative; z-index: 1; user-select: none; -webkit-user-select: none; -moz-user-select: none; -ms-user-select: none; overscroll-behavior: contain;">
                <div class="result-content-wrapper" style="height: 100%; overflow-y: auto; overflow-x: hidden; padding: 20px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); scroll-behavior: smooth; position: relative; z-index: 2; cursor: default; overflow-scrolling: touch; overscroll-behavior: contain; scroll-snap-type: none; -webkit-overflow-scrolling: touch;">
                    <div class="result-info-bar" style="position: sticky; top: 0; z-index: 5; background: rgba(74, 85, 104, 0.95); backdrop-filter: blur(8px); color: #e2e8f0; font-size: 0.85rem; margin: 0 -20px 20px -20px; padding: 12px 20px; font-weight: 600; text-align: center; border-bottom: 2px solid rgba(96, 165, 250, 0.3); box-shadow: 0 2px 8px rgba(0,0,0,0.3);">📝 批改结果 ({len(st.session_state.correction_result)} 字符)</div>
                    <pre style="margin: 0; padding: 0; color: #e2e8f0; font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Source Code Pro', monospace; font-size: 0.95rem; line-height: 1.7; white-space: pre-wrap; word-wrap: break-word; background: rgba(45, 55, 72, 0.3); padding: 20px; border-radius: 8px; border: 1px solid rgba(74, 85, 104, 0.3);">{html.escape(st.session_state.correction_result)}</pre>
                    <div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 0.9rem; border-top: 1px solid rgba(74, 85, 104, 0.3); margin-top: 20px; background: rgba(45, 55, 72, 0.5); border-radius: 8px;"><span style="background: rgba(96, 165, 250, 0.1); padding: 6px 12px; border-radius: 20px; border: 1px solid rgba(96, 165, 250, 0.3);">💡 使用滚轮浏览批改结果，支持复制内容</span></div>
                </div>
            </div>
            <style>
            /* 批改结果滚动条样式 - 与预览框保持一致 */
            .correction-result-frame .result-content-wrapper::-webkit-scrollbar {{
                width: 14px;
                height: 14px;
            }}
            .correction-result-frame .result-content-wrapper::-webkit-scrollbar-track {{
                background: rgba(0, 0, 0, 0.4);
                border-radius: 8px;
                border: 1px solid rgba(74, 85, 104, 0.3);
            }}
            .correction-result-frame .result-content-wrapper::-webkit-scrollbar-thumb {{
                background: linear-gradient(135deg, #4a5568, #2d3748);
                border-radius: 8px;
                border: 2px solid rgba(0, 0, 0, 0.2);
                transition: all 0.3s ease;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
            .correction-result-frame .result-content-wrapper::-webkit-scrollbar-thumb:hover {{
                background: linear-gradient(135deg, #60a5fa, #3b82f6);
                transform: scale(1.05);
                box-shadow: 0 4px 8px rgba(96, 165, 250, 0.3);
            }}
            .correction-result-frame .result-content-wrapper::-webkit-scrollbar-thumb:active {{
                background: linear-gradient(135deg, #2563eb, #1d4ed8);
            }}
            .correction-result-frame .result-content-wrapper::-webkit-scrollbar-corner {{
                background: rgba(0, 0, 0, 0.4);
                border-radius: 8px;
            }}
            
            /* 批改结果框悬停效果 */
            .correction-result-frame:hover {{
                border-color: #60a5fa;
                box-shadow: 0 12px 24px rgba(0,0,0,0.4), 0 0 0 1px rgba(96, 165, 250, 0.3);
                transition: all 0.3s ease;
            }}
            
            /* 批改结果框焦点效果 */
            .correction-result-frame:focus {{
                border-color: #60a5fa;
                box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.2);
                outline: none;
            }}
            
            /* 滚动指示器 */
            .correction-result-frame::before {{
                content: "⚡ 可滚动预览";
                position: absolute;
                top: 8px;
                right: 12px;
                background: rgba(96, 165, 250, 0.8);
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.7rem;
                font-weight: 600;
                z-index: 10;
                opacity: 0;
                transition: opacity 0.3s ease;
                pointer-events: none;
            }}
            .correction-result-frame:hover::before {{
                opacity: 1;
            }}
            </style>
            '''
            st.markdown(result_html, unsafe_allow_html=True)
        else:
            # 空结果时的占位容器
            empty_html = '''
            <div class="correction-result-frame" style="height: 520px; border: 3px solid #4a5568; border-radius: 12px; background-color: #1a202c; box-shadow: 0 8px 16px rgba(0,0,0,0.3); display: flex; justify-content: center; align-items: center;">
                <div style="text-align: center; color: #a0aec0;">
                    <h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">📝 暂无批改结果</h3>
                    <p style="font-size: 1.1rem;">请先上传文件并执行批改</p>
                </div>
            </div>
            '''
            st.markdown(empty_html, unsafe_allow_html=True)
    
    # 文件切换功能 (放在左侧预览区域内)
    if len(st.session_state.uploaded_files_data) > 1:
            file_options = []
            for i, file_data in enumerate(st.session_state.uploaded_files_data):
                file_name = file_data['name']
            category = file_data.get('category', 'other')
            
            # 优先使用保存的category信息
            if category == 'question':
                label = f"📋 题目: {file_name}"
            elif category == 'answer':
                label = f"✏️ 学生作答: {file_name}"
            elif category == 'marking':
                label = f"📊 评分标准: {file_name}"
            else:
                # 兼容旧记录，通过文件名判断
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
            "🔄 切换文件:",
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
            if 'confirm_delete' not in st.session_state:
                st.session_state.confirm_delete = True
            else:
                users[st.session_state.username]['records'] = []
                save_users(users)
                del st.session_state.confirm_delete
                st.success('历史记录已清空')
                st.rerun()

    if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:
        st.warning("确定要清空所有历史记录吗？此操作无法撤销。")
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("✅ 是，清空", use_container_width=True):
                users[st.session_state.username]['records'] = []
                save_users(users)
                del st.session_state.confirm_delete
                st.success("历史记录已清空")
                st.rerun()
        with col_cancel:
            if st.button("❌ 否，取消", use_container_width=True):
                del st.session_state.confirm_delete
                st.rerun()
    
    st.markdown("---")
    
    # 记录列表
    for i, record in enumerate(reversed(records), 1):
        with st.expander(f"📋 记录 {i} - {record['timestamp']}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**文件：** {', '.join(record.get('files', ['无文件信息']))}")
                settings = record.get('settings', {})
                mode_text = "有批改标准" if settings.get('has_marking_scheme') else "自动生成标准"
                st.write(f"**设置：** {mode_text} | {settings.get('strictness', 'N/A')}")
            
            with col2:
                if st.button("👁️ 查看详情", key=f"view_{i}", use_container_width=True):
                    # 设置批改结果到session state
                    st.session_state.correction_result = record.get('result', '')
                    
                    # 重建文件数据用于结果页面展示
                    file_data = record.get('file_data', [])
                    if file_data:
                        # 使用保存的文件路径信息
                        st.session_state.uploaded_files_data = [
                            {
                                'name': f['name'],
                                'path': f.get('path'),
                                'type': f.get('type', get_file_type(f['name']))
                            }
                            for f in file_data
                        ]
                    else:
                        # 兼容旧记录（没有file_data字段）
                        file_names = record.get('files', [])
                        st.session_state.uploaded_files_data = [
                            {'name': name, 'path': None, 'type': get_file_type(name)} 
                            for name in file_names
                        ]
                    
                    st.session_state.correction_settings = record.get('settings', {})
                    # 重置文件索引到第一个文件
                    st.session_state.current_file_index = 0
                    st.session_state.page = "result"
                    st.rerun()
                    st.rerun()
                
                if record.get('result'):
                    # 处理结果数据，确保是字符串格式
                    result_data = record.get('result', '')
                    if isinstance(result_data, dict):
                        # 如果是字典格式，转换为字符串
                        if result_data.get('has_separate_scheme', False):
                            marking_scheme = result_data.get('marking_scheme', '')
                            correction_content = result_data.get('correction_result', '')
                            download_content = f"=== 评分标准 ===\n\n{marking_scheme}\n\n=== 批改结果 ===\n\n{correction_content}"
                        else:
                            download_content = str(result_data.get('correction_result', result_data))
                    else:
                        download_content = str(result_data)
                    
                    st.download_button(
                        "💾 下载",
                        data=download_content,
                        file_name=f"record_{record['timestamp'].replace(':', '-').replace(' ', '_')}.txt",
                        mime="text/plain",
                        key=f"download_{i}",
                        use_container_width=True
                    )

# 侧边栏
def show_sidebar():
    """显示侧边栏"""
    with st.sidebar:
        st.markdown('<h3 style="color: #3b82f6;">🤖 AI批改系统</h3>', unsafe_allow_html=True)
        
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
            
            if st.button("📚 历史", use_container_width=True):
                st.session_state.page = "history"
                st.rerun()
            
            # 结果页面导航 (只在有结果时显示)
            if st.session_state.correction_result:
                if st.button("📊 查看结果", use_container_width=True):
                    st.session_state.page = "result"
                    st.rerun()
            
            st.markdown("---")
            
            # 批改控制设置
            st.header("🛠️ 批改控制")
            
            # 分批处理设置
            enable_batch = st.checkbox("启用分批处理", value=True, help="处理大量题目时推荐启用")
            
            if enable_batch:
                batch_size = st.slider("每批题目数量", min_value=5, max_value=15, value=10, 
                                     help="每批处理的题目数量，较小的批次更稳定")
            else:
                batch_size = None
                
            # 新增功能控制
            st.subheader("🔧 高级设置")
            
            skip_missing = st.checkbox("跳过缺失文件的题目", value=True, 
                                     help="如果未找到作答文件，不计入总分")
            
            separate_summary = st.checkbox("总结分离模式", value=True,
                                         help="避免分批中出现总结，最后单独生成")
            
            generate_summary = st.checkbox("生成批改总结", value=True,
                                         help="完成批改后生成整体总结")
            
            # 循环控制设置
            st.subheader("🛑 循环防护")
            max_steps = st.selectbox("每题最大步骤数", [3, 5, 7], index=0,
                                   help="限制每题的最大步骤数，防止循环")
            
            # 在session_state中保存设置
            st.session_state.batch_settings = {
                'enable_batch': enable_batch,
                'batch_size': batch_size if enable_batch else 10,
                'skip_missing': skip_missing,
                'separate_summary': separate_summary,
                'generate_summary': generate_summary,
                'max_steps': max_steps
            }
            
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
            - 📊 两种模式（有标准/无标准）
            - 📚 历史管理
            - 💾 结果导出
            """)
            
            st.markdown("---")
            
            # 系统状态
            if API_AVAILABLE:
                st.success("✅ 系统就绪")
            else:
                st.warning("⚠️ 演示模式")
        
        # 设置信息部分（无论登录与否都显示）
        st.markdown("---")
        st.header("⚙️ 设置")
        
        # API状态显示
        st.subheader("🤖 AI模型")
        st.info(f"**模型**: {api_config.model}")
        st.info(f"**提供商**: OpenRouter (Google)")
        
        if API_AVAILABLE:
            st.success("✅ AI引擎已就绪")
        else:
            st.warning("⚠️ 演示模式运行中")
        
        st.markdown("---")
        
        # 使用说明
        st.subheader("📖 使用说明")
        st.markdown("""
        1. **上传文件**：支持图片、PDF、Word、文本等格式
        2. **选择批改方式**：有批改标准或自动生成标准
        3. **设置严格度**：调整批改的严格程度
        4. **开始批改**：点击"开始AI批改"按钮
        5. **查看结果**：在结果页面查看详细批改
        """)
        
        # 技术信息
        st.markdown("---")
        st.subheader("🔧 技术信息")
        st.markdown(f"""
        - **AI模型**: Google Gemini 2.5 Flash Lite Preview
        - **API提供商**: OpenRouter
        - **支持格式**: 图片、PDF、Word、文本
        - **最大文件**: 4MB (自动压缩)
        """)

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
    elif st.session_state.page == "history":
        show_history()
    elif st.session_state.page == "result":
        show_result()
    else:
        show_home()

if __name__ == "__main__":
    main() 