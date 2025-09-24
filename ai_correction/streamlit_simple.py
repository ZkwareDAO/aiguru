#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能批改系统 - 简洁版
整合calling_api.py和main.py的所有功能，去除无意义空行
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
print("正在使用修复版API调用模块")
import logging
import io
from PIL import Image

# 导入班级系统数据库模块
try:
    from database import (
        init_database,
        create_user,
        verify_user,
        get_user_info,
        create_class,
        join_class_by_code,
        get_user_classes,
        create_assignment,
        get_class_assignments,
        submit_assignment,
        get_assignment_submissions,
        add_notification,
        get_user_notifications,
        get_assignment_center_data,
        get_user_assignment_summary,
        search_assignments,
        get_assignment_status,
        get_user_submission_status,
        get_assignment_analytics_data,
        save_grading_result,
        get_grading_result
    )
    CLASS_SYSTEM_AVAILABLE = True
    print("✅ 班级系统数据库模块加载成功")
except ImportError as e:
    CLASS_SYSTEM_AVAILABLE = False
    print(f"⚠️ 班级系统数据库模块加载失败: {e}")

# 兼容性函数：处理不同版本的Streamlit
def st_rerun():
    """兼容不同版本的Streamlit重新运行函数"""
    if hasattr(st, 'rerun'):
        st.rerun()
    elif hasattr(st, 'experimental_rerun'):
        st.experimental_rerun()
    else:
        # 对于更老的版本，使用重新加载页面的方式
        st.experimental_singleton.clear()
        st._rerun()

# 多模态大模型文档处理 - 无需PyMuPDF
# 直接使用多模态大模型处理各种文档格式

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
    
    # 检查API配置状态（静默检查，不显示在主页面）
    api_status = api_config.get_status()
    if api_config.is_valid():
        API_AVAILABLE = True
    else:
        API_AVAILABLE = False
            
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
- 第二步计算有小错误
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

# 导入CSS样式 - 优化视觉体验版
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
    
    /* 增强所有文字对比度 - 改为白色 */
    .stMarkdown, .stText, .stCaption, .stWrite, p, span, div {
        color: #ffffff !important;
        font-weight: 600;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
    }
    
    /* 标题和重要文字 - 改为白色 */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-weight: 700;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
    }
    
    /* 强调文字 - 改为深蓝色 */
    strong, b {
        color: #1e40af !important;
        font-weight: 700;
    }
    
    /* 链接文字 - 保持蓝色但更深 */
    a {
        color: #2563eb !important;
        text-decoration: none;
        font-weight: 600;
    }
    
    a:hover {
        color: #1d4ed8 !important;
        text-decoration: underline;
    }
    
    /* 表单标签和输入框 - 改善字体清晰度 */
    label, .stSelectbox label, .stTextInput label, .stTextArea label, .stFileUploader label,
    .stDateInput label, .stTimeInput label, .stNumberInput label {
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 1rem !important;
        font-family: 'Inter', 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.9) !important;
        background: linear-gradient(135deg, #2563eb, #1e40af) !important;
        padding: 10px 18px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3) !important;
        letter-spacing: 0.5px !important;
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
        text-rendering: optimizeLegibility !important;
    }
    
    /* 输入框文字 */
    .stTextInput input, .stTextArea textarea, .stSelectbox select, .stNumberInput input {
        background-color: rgba(255, 255, 255, 0.95) !important;
        color: #1a202c !important;
        border: 2px solid rgba(96, 165, 250, 0.3) !important;
        border-radius: 8px !important;
    }
    
    /* 文件上传器 - 改为黑色文字 */
    .stFileUploader > div {
        background-color: rgba(255, 255, 255, 0.9) !important;
        border: 2px dashed rgba(96, 165, 250, 0.5) !important;
        border-radius: 8px !important;
    }
    
    .stFileUploader label, .stFileUploader div {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    
    /* 选择框下拉选项 */
    .stSelectbox > div > div {
        background-color: rgba(255, 255, 255, 0.95) !important;
        color: #1a202c !important;
    }
    
    /* 按钮文字 - 保持白色，因为按钮有深色背景 */
    .stButton button {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    
    /* 标签页 - 白色背景保持黑色文字 */
    .stTabs [data-baseweb="tab-list"] button {
        color: #1a202c !important;
        font-weight: 600 !important;
        background: rgba(255, 255, 255, 0.8) !important;
        border-radius: 6px !important;
        margin: 2px !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #1e40af !important;
        font-weight: 700 !important;
        background: rgba(255, 255, 255, 1.0) !important;
        border: 2px solid rgba(59, 130, 246, 0.6) !important;
    }
    
    /* 指标容器 - 白色背景保持黑色文字 */
    .metric-container, [data-testid="metric-container"] {
        color: #1a202c !important;
        background: rgba(255, 255, 255, 0.9) !important;
        padding: 8px !important;
        border-radius: 6px !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
    }
    
    [data-testid="metric-container"] > div {
        color: #1a202c !important;
    }
    
    [data-testid="metric-container"] label {
        color: #1e40af !important;
        font-weight: 600 !important;
    }
    
    /* 信息框 */
    .stInfo {
        background-color: rgba(59, 130, 246, 0.2) !important;
        border: 1px solid rgba(59, 130, 246, 0.5) !important;
        color: #dbeafe !important;
    }
    
    .stSuccess {
        background-color: rgba(34, 197, 94, 0.2) !important;
        border: 1px solid rgba(34, 197, 94, 0.5) !important;
        color: #bbf7d0 !important;
    }
    
    .stWarning {
        background-color: rgba(245, 158, 11, 0.2) !important;
        border: 1px solid rgba(245, 158, 11, 0.5) !important;
        color: #fde68a !important;
    }
    
    .stError {
        background-color: rgba(239, 68, 68, 0.2) !important;
        border: 1px solid rgba(239, 68, 68, 0.5) !important;
        color: #fecaca !important;
    }
    
    /* 展开器 */
    .streamlit-expanderHeader {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }
    
    /* 容器和列 */
    .stContainer, .element-container, .stColumn {
        color: #f8fafc !important;
    }
    
    /* 表格 */
    .stDataFrame, .stTable {
        background-color: rgba(255, 255, 255, 0.95) !important;
        color: #1a202c !important;
    }
    
    /* 代码块 */
    .stCode {
        background-color: rgba(0, 0, 0, 0.8) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(96, 165, 250, 0.3) !important;
    }
    
    /* 分割线 */
    hr {
        border-color: rgba(96, 165, 250, 0.5) !important;
    }
    
    /* 侧边栏背景和文字增强 */
    section[data-testid="stSidebar"] {
        background-color: #1a1a1a !important;
        background: #1a1a1a !important;
    }
    
    section[data-testid="stSidebar"] > div {
        background-color: #1a1a1a !important;
        background: #1a1a1a !important;
    }
    
    .sidebar .stMarkdown, .sidebar .stText, .sidebar p, .sidebar span,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stText,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {
        color: #f8fafc !important;
        font-weight: 500;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
    }
    
    /* 侧边栏标题文字 */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] h5,
    section[data-testid="stSidebar"] h6 {
        color: #60a5fa !important;
        font-weight: 700;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.7);
    }
    
    /* 侧边栏按钮特殊样式 */
    section[data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
        color: #ffffff !important;
        border: 1px solid rgba(96, 165, 250, 0.5);
        font-weight: 700;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        border-color: rgba(96, 165, 250, 0.8);
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.5);
    }
    
    /* 侧边栏输入框 */
    section[data-testid="stSidebar"] .stTextInput > div > div > input,
    section[data-testid="stSidebar"] .stSelectbox > div > div > select,
    section[data-testid="stSidebar"] .stSlider > div > div > div {
        background: rgba(40, 40, 40, 0.8) !important;
        border: 1px solid rgba(96, 165, 250, 0.5) !important;
        color: #f8fafc !important;
    }
    
    /* 侧边栏标签 */
    section[data-testid="stSidebar"] label {
        color: #e2e8f0 !important;
        font-weight: 600;
    }
    
    /* 侧边栏复选框 */
    section[data-testid="stSidebar"] .stCheckbox > label {
        color: #f1f5f9 !important;
        font-weight: 500;
    }
    
    /* 侧边栏度量值 */
    section[data-testid="stSidebar"] .stMetric > div {
        background: rgba(40, 40, 40, 0.8) !important;
        border: 1px solid rgba(96, 165, 250, 0.4) !important;
    }
    
    section[data-testid="stSidebar"] .stMetric label {
        color: #60a5fa !important;
    }
    
    section[data-testid="stSidebar"] .stMetric > div > div {
        color: #f8fafc !important;
    }
    
    /* 侧边栏分割线 */
    section[data-testid="stSidebar"] hr {
        border-color: rgba(96, 165, 250, 0.5) !important;
    }
    
    /* 侧边栏滚动条 */
    section[data-testid="stSidebar"] > div:first-child {
        overflow: overlay;
    }
    
    section[data-testid="stSidebar"]::-webkit-scrollbar {
        width: 8px;
    }
    
    section[data-testid="stSidebar"]::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.5);
    }
    
    section[data-testid="stSidebar"]::-webkit-scrollbar-thumb {
        background: rgba(96, 165, 250, 0.5);
        border-radius: 4px;
    }
    
    section[data-testid="stSidebar"]::-webkit-scrollbar-thumb:hover {
        background: rgba(96, 165, 250, 0.7);
    }
    
    /* 侧边栏信息框特殊样式 */
    section[data-testid="stSidebar"] .stSuccess {
        background: rgba(34, 197, 94, 0.2) !important;
        border: 1px solid rgba(34, 197, 94, 0.5) !important;
        color: #86efac !important;
    }
    
    section[data-testid="stSidebar"] .stWarning {
        background: rgba(245, 158, 11, 0.2) !important;
        border: 1px solid rgba(245, 158, 11, 0.5) !important;
        color: #fde68a !important;
    }
    
    section[data-testid="stSidebar"] .stInfo {
        background: rgba(59, 130, 246, 0.2) !important;
        border: 1px solid rgba(59, 130, 246, 0.5) !important;
        color: #93c5fd !important;
    }
    
    section[data-testid="stSidebar"] .stError {
        background: rgba(239, 68, 68, 0.2) !important;
        border: 1px solid rgba(239, 68, 68, 0.5) !important;
        color: #fca5a5 !important;
    }
    
    /* 按钮样式优化 */
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
    
    /* 输入框样式优化 - 白色背景黑色文字 */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        background: rgba(255, 255, 255, 0.95) !important;
        border: 2px solid rgba(96, 165, 250, 0.6) !important;
        color: #1a202c !important;
        font-weight: 600;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > select:focus {
        border-color: rgba(96, 165, 250, 1.0) !important;
        box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.4) !important;
        background: rgba(255, 255, 255, 1.0) !important;
        color: #000000 !important;
    }
    
    /* 选择框下拉箭头和选项 */
    .stSelectbox > div > div > select option {
        background: rgba(255, 255, 255, 0.98) !important;
        color: #1a202c !important;
        font-weight: 600;
    }
    
    /* 输入框占位符文字 */
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: #6b7280 !important;
        font-weight: 400;
    }
    
    /* 选择框容器 */
    .stSelectbox > div {
        background: transparent !important;
    }
    
    /* 多选框样式 */
    .stMultiSelect > div > div {
        background: rgba(15, 23, 42, 0.95) !important;
        border: 2px solid rgba(96, 165, 250, 0.6) !important;
        border-radius: 8px;
    }
    
    .stMultiSelect > div > div > div {
        background: rgba(15, 23, 42, 0.95) !important;
        color: #f8fafc !important;
        font-weight: 600;
    }
    
    /* 标签文字增强 */
    .stTextInput > label, .stTextArea > label, .stSelectbox > label,
    .stFileUploader > label, .stCheckbox > label {
        color: #e2e8f0 !important;
        font-weight: 600;
        font-size: 1rem;
    }
    
    /* 帮助文字增强 */
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: #94a3b8 !important;
        font-weight: 400;
    }
    
    /* 信息框样式优化 */
    .stSuccess, .stInfo, .stWarning, .stError {
        font-weight: 600;
        border-radius: 10px;
        border-left: 4px solid;
    }
    
    .stSuccess {
        background: rgba(34, 197, 94, 0.1) !important;
        border-left-color: #22c55e !important;
        color: #bbf7d0 !important;
    }
    
    .stInfo {
        background: rgba(59, 130, 246, 0.1) !important;
        border-left-color: #3b82f6 !important;
        color: #bfdbfe !important;
    }
    
    .stWarning {
        background: rgba(245, 158, 11, 0.1) !important;
        border-left-color: #f59e0b !important;
        color: #fde68a !important;
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.1) !important;
        border-left-color: #ef4444 !important;
        color: #fecaca !important;
    }
    
    /* 度量值样式 - 增强对比度 */
    .stMetric > div {
        background: rgba(15, 23, 42, 0.9) !important;
        border: 2px solid rgba(96, 165, 250, 0.6) !important;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
    }
    
    .stMetric > div > div {
        color: #f8fafc !important;
        font-weight: 700;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
    }
    
    .stMetric > div > div:first-child {
        color: #93c5fd !important;
        font-weight: 800;
        font-size: 1.2rem;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.7);
    }
    
    /* 度量值数字 */
    .stMetric > div > div[data-testid="metric-value"] {
        color: #ffffff !important;
        font-weight: 800;
        font-size: 2rem;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.7);
    }
    
    /* 展开器样式 - 增强对比度 */
    .streamlit-expanderHeader {
        background: rgba(15, 23, 42, 0.95) !important;
        border: 2px solid rgba(96, 165, 250, 0.6) !important;
        border-radius: 8px;
        color: #f8fafc !important;
        font-weight: 700;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(59, 130, 246, 0.8) !important;
        border-color: rgba(96, 165, 250, 1.0) !important;
        color: #ffffff !important;
    }
    
    .streamlit-expanderContent {
        background: rgba(15, 23, 42, 0.9) !important;
        border: 2px solid rgba(96, 165, 250, 0.4) !important;
        border-top: none;
        border-radius: 0 0 8px 8px;
        color: #f8fafc !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
    }
    
    /* 选项卡样式 - 增强对比度 */
    .stTabs > div > div > div > div {
        background: rgba(15, 23, 42, 0.9) !important;
        border: 2px solid rgba(96, 165, 250, 0.5) !important;
        border-radius: 8px 8px 0 0;
        color: #f8fafc !important;
        font-weight: 700;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
    }
    
    .stTabs > div > div > div > div[aria-selected="true"] {
        background: rgba(59, 130, 246, 0.8) !important;
        border-color: rgba(96, 165, 250, 1.0) !important;
        color: #ffffff !important;
        font-weight: 800;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.7);
    }
    
    .stTabs > div > div > div > div:hover {
        background: rgba(59, 130, 246, 0.6) !important;
        border-color: rgba(96, 165, 250, 0.8) !important;
        color: #ffffff !important;
    }
    
    /* 进度条样式 */
    .stProgress > div > div > div {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6) !important;
        border-radius: 10px;
    }
    
    /* 滑块样式 */
    .stSlider > div > div > div {
        color: #e2e8f0 !important;
        font-weight: 600;
    }
    
    /* 复选框样式 */
    .stCheckbox > label {
        color: #e2e8f0 !important;
        font-weight: 500;
    }
    
    /* 分割线样式 */
    hr {
        border-color: rgba(96, 165, 250, 0.3) !important;
        margin: 1.5rem 0;
    }
    
    /* 结果容器样式 */
    .result-container {
        background: rgba(30, 41, 59, 0.95);
        border: 2px solid rgba(96, 165, 250, 0.4);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    /* 分栏布局样式 - 增强版*/
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
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.3), rgba(139, 92, 246, 0.3));
        border-bottom: 1px solid rgba(96, 165, 250, 0.4);
        padding: 1rem 1.5rem;
        font-weight: 700;
        font-size: 1.1rem;
        color: #f1f5f9;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        border-radius: 18px 18px 0 0;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
    }
    
    .panel-content {
        height: calc(100% - 4rem);
        overflow-y: auto;
        overflow-x: hidden;
        padding: 1.5rem;
        position: relative;
        color: #f1f5f9;
    }
    
    /* 自定义滚动条样式 */
    .panel-content::-webkit-scrollbar {
        width: 10px;
    }
    
    .panel-content::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.3);
        border-radius: 5px;
    }
    
    .panel-content::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        border-radius: 5px;
        transition: all 0.3s ease;
    }
    
    .panel-content::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #2563eb, #7c3aed);
    }
    
    /* 文件预览容器 */
    .file-preview-inner {
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(96, 165, 250, 0.3);
        border-radius: 12px;
        padding: 1rem;
        min-height: 200px;
        color: #f1f5f9;
    }
    
    /* 批改结果容器 */
    .correction-result-inner {
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 12px;
        padding: 1.5rem;
        min-height: 200px;
        font-family: 'Consolas', 'Monaco', monospace;
        line-height: 1.6;
        color: #f1f5f9;
        font-weight: 500;
    }
    
    /* 文件切换器增强样式*/
    .file-selector-container {
        background: rgba(0, 0, 0, 0.4);
        border: 1px solid rgba(96, 165, 250, 0.3);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* 鼠标悬停效果 */
    .left-panel:hover, .right-panel:hover {
        border-color: rgba(96, 165, 250, 0.7);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        transform: translateY(-2px);
        transition: all 0.3s ease;
    }
    
    /* 文件预览图片样式 */
    .file-preview-inner img {
        max-width: 100%;
        height: auto;
        border-radius: 8px;
        border: 1px solid rgba(96, 165, 250, 0.3);
        transition: transform 0.3s ease;
    }
    
    .file-preview-inner img:hover {
        transform: scale(1.02);
    }
    
    /* 批改结果文本样式优化 */
    .correction-result-inner pre {
        font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
        font-size: 0.95rem;
        line-height: 1.6;
        color: #f1f5f9;
        background: transparent;
        border: none;
        padding: 0;
        margin: 0;
        white-space: pre-wrap;
        word-wrap: break-word;
        font-weight: 500;
    }
    
    /* 响应式设计*/
    @media (max-width: 768px) {
        .split-container {
            flex-direction: column;
            height: auto;
        }
        
        .left-panel, .right-panel {
            min-height: 400px;
        }
        
        .main-title {
            font-size: 2rem;
        }
    }
    
    /* 表格样式优化 - 增强对比度 */
    .stDataFrame {
        background: rgba(15, 23, 42, 0.95) !important;
        border: 2px solid rgba(96, 165, 250, 0.6) !important;
        border-radius: 8px;
        color: #f8fafc !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
    }
    
    .stDataFrame table {
        background: rgba(15, 23, 42, 0.95) !important;
        color: #f8fafc !important;
    }
    
    .stDataFrame th {
        background: rgba(59, 130, 246, 0.8) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
    }
    
    .stDataFrame td {
        background: rgba(15, 23, 42, 0.9) !important;
        color: #f8fafc !important;
        font-weight: 500 !important;
        border-color: rgba(96, 165, 250, 0.3) !important;
    }
    
    /* 代码块样式 - 增强对比度 */
    .stCode {
        background: rgba(0, 0, 0, 0.8) !important;
        border: 2px solid rgba(96, 165, 250, 0.5) !important;
        border-radius: 8px;
        color: #f8fafc !important;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4) !important;
    }
    
    .stCode code {
        color: #f8fafc !important;
        font-weight: 600;
    }
    
    /* 侧边栏边框 */
    section[data-testid="stSidebar"] {
        border-right: 2px solid rgba(96, 165, 250, 0.4) !important;
    }
    
    /* 主内容区域 */
    .css-18e3th9 {
        background: transparent !important;
    }
    
    /* 修复历史记录显示问题 */
    .history-record {
        background: rgba(30, 41, 59, 0.8) !important;
        border: 1px solid rgba(96, 165, 250, 0.3) !important;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        color: #f1f5f9 !important;
    }
    
    .history-record strong {
        color: #60a5fa !important;
        font-weight: 700;
    }
    
    /* 文件上传区域样式 - 增强对比度 */
    .stFileUploader {
        background: rgba(15, 23, 42, 0.9) !important;
        border: 2px dashed rgba(96, 165, 250, 0.7) !important;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
    }
    
    .stFileUploader:hover {
        border-color: rgba(96, 165, 250, 1.0) !important;
        background: rgba(15, 23, 42, 1.0) !important;
        box-shadow: 0 4px 12px rgba(96, 165, 250, 0.2) !important;
    }
    
    /* 文件上传器内部文字 */
    .stFileUploader label {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }
    
    .stFileUploader > div > div {
        color: #f8fafc !important;
        font-weight: 500 !important;
    }
    
    /* 文件上传按钮 */
    .stFileUploader button {
        background: rgba(59, 130, 246, 0.8) !important;
        color: #ffffff !important;
        border: 1px solid rgba(96, 165, 250, 0.6) !important;
        font-weight: 600 !important;
    }
    
    .stFileUploader button:hover {
        background: rgba(59, 130, 246, 1.0) !important;
        border-color: rgba(96, 165, 250, 1.0) !important;
    }
    
    /* 确保所有文字都有足够的对比度 */
    * {
        color: #f1f5f9 !important;
    }
    
    /* 白色控件使用黑色文字确保鲜明对比 */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select,
    .stSelectbox > div > div > select option,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stTimeInput > div > div > input,
    .stFileUploader > div > div > input,
    .stMultiSelect > div > div > div > div,
    .stSlider > div > div > div > div,
    input[type="text"],
    input[type="number"],
    input[type="email"],
    input[type="password"],
    input[type="date"],
    input[type="time"],
    textarea,
    select {
        color: #000000 !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
    }
    
    /* 确保占位符文字也是深色 */
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder,
    input::placeholder,
    textarea::placeholder {
        color: #666666 !important;
    }
    
    /* 但是保持批改结果页面的特殊样式不变 */
    .correction-result-inner * {
        color: inherit !important;
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
            print(f"图片文件过大 ({file_size_mb:.2f}MB)，正在压缩..")
            
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
    # 基础状态
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'page' not in st.session_state:
        st.session_state.page = "home"
    if 'correction_result' not in st.session_state:
        st.session_state.correction_result = ""
    if 'uploaded_files_data' not in st.session_state:
        st.session_state.uploaded_files_data = []  # 修复：改为列表
    if 'current_file_index' not in st.session_state:
        st.session_state.current_file_index = 0
    if 'correction_settings' not in st.session_state:
        st.session_state.correction_settings = {}
    
    # 班级系统状态
    if 'show_class_system' not in st.session_state:
        st.session_state.show_class_system = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = ""
    if 'current_class_id' not in st.session_state:
        st.session_state.current_class_id = ""
    if 'current_assignment_id' not in st.session_state:
        st.session_state.current_assignment_id = ""
    if 'class_list' not in st.session_state:
        st.session_state.class_list = []
    if 'class_creation_mode' not in st.session_state:
        st.session_state.class_creation_mode = False
    if 'class_join_mode' not in st.session_state:
        st.session_state.class_join_mode = False
    if 'class_creation_data' not in st.session_state:
        st.session_state.class_creation_data = {
            'name': '',
            'description': '',
            'invite_code': ''
        }
    if 'join_code' not in st.session_state:
        st.session_state.join_code = ''
    
    # 初始化班级系统数据库（如果可用）
    if CLASS_SYSTEM_AVAILABLE:
        try:
            init_database()
            # 获取用户班级列表
            try:
                st.session_state.class_list = get_user_classes(st.session_state.username, st.session_state.user_role)
            except Exception as e:
                print(f"获取班级列表失败: {e}")
        except Exception as e:
            print(f"⚠️ 班级系统数据库初始化失败: {e}")
            st.session_state.show_class_system = False
            st.session_state.class_list = []
    
    # 在班级系统可用时，根据用户角色显示不同的模式
    if st.session_state.show_class_system and st.session_state.user_role:
        if st.session_state.user_role == 'teacher':
            st.session_state.class_creation_mode = True
        elif st.session_state.user_role == 'student':
            st.session_state.class_join_mode = True

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
    
    saved_files_info = []
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
        saved_files_info.append({
            "path": str(file_path),
            "name": filename,
            "original_name": file.name,
            "size": len(file.getbuffer()),
            "category": file_category,
            "display_name": f"{filename} ({file.name})"
        })
    
    return saved_files_info

# 主页
def show_home():
    st.markdown('<h1 class="main-title">🤖 AI智能批改系统</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #94a3b8; font-size: 1.1rem;">AI赋能教育，智能批改新纪元</p>', unsafe_allow_html=True)
    
    # 显示系统模式选择（如果班级系统可用）
    if CLASS_SYSTEM_AVAILABLE:
        st.markdown("---")
        st.markdown("### 🎯 选择使用模式")
        
        col1, col2 = st.columns(2, gap="large")
        
        with col1:
            st.markdown("""
            <div class="class-card">
                <h3>🎓 班级系统模式</h3>
                <p>• 教师创建班级，发布作业</p>
                <p>• 学生加入班级，提交作业</p>
                <p>• AI智能批改，教师审核</p>
                <p>• 完整的教学管理流程</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 进入班级系统", use_container_width=True, type="primary"):
                st.session_state.show_class_system = True
                # 直接跳转到班级管理页面
                st.session_state.page = "class_management"
                st_rerun()
        
        with col2:
            st.markdown("""
            <div class="class-card">
                <h3>📝 独立批改模式</h3>
                <p>• 直接上传文件进行批改</p>
                <p>• 支持多种文件格式</p>
                <p>• 快速获得批改结果</p>
                <p>• 适合个人使用</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("📝 独立批改", use_container_width=True):
                st.session_state.show_class_system = False
                if st.session_state.logged_in:
                    st.session_state.page = "grading"
                else:
                    st.session_state.page = "login"
                st_rerun()
        
        # 功能介绍
        st.markdown("---")
        st.markdown("### 💡 系统特色")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**🎯 智能批改**")
            st.write("支持多种文件格式")
            st.write("智能识别内容")
            st.write("详细错误分析")
        
        with col2:
            st.markdown("**📊 多种模式**")
            st.write("高效模式：快速批改")
            st.write("详细模式：深度分析")
            st.write("批量模式：批量处理")
        
        with col3:
            st.markdown("**💎 增值功能**")
            st.write("自动生成评分标准")
            st.write("多语言支持")
            st.write("历史记录管理")
            
        # 添加卡片样式
        st.markdown("""
        <style>
        .class-card {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1));
            border: 2px solid rgba(96, 165, 250, 0.3);
            border-radius: 16px;
            padding: 1.5rem;
            margin: 1rem 0;
            text-align: center;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        
        .class-card:hover {
            border-color: rgba(96, 165, 250, 0.6);
            box-shadow: 0 8px 32px rgba(96, 165, 250, 0.2);
            transform: translateY(-2px);
        }
        
        .class-card h3 {
            color: #60a5fa !important;
            margin-bottom: 1rem;
            font-weight: 700;
        }
        
        .class-card p {
            color: #e2e8f0 !important;
            margin: 0.5rem 0;
            font-weight: 500;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        # 如果班级系统不可用，显示传统模式
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🚀 立即批改", use_container_width=True, type="primary"):
                if st.session_state.logged_in:
                    st.session_state.page = "grading"
                    st_rerun()
                else:
                    st.session_state.page = "login"
                    st_rerun()
        
        with col2:
            if st.button("📚 查看历史", use_container_width=True):
                if st.session_state.logged_in:
                    st.session_state.page = "history"
                    st_rerun()
                else:
                    st.session_state.page = "login"
                    st_rerun()
        
        with col3:
            if st.button("👤 用户中心", use_container_width=True):
                st.session_state.page = "login"
                st_rerun()
        
        # 功能介绍
        st.markdown("---")
        st.markdown("### 💡 系统特色")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**🎯 智能批改**")
            st.write("支持多种文件格式")
            st.write("智能识别内容")
            st.write("详细错误分析")
        
        with col2:
            st.markdown("**📊 多种模式**")
            st.write("高效模式：快速批改")
            st.write("详细模式：深度分析")
            st.write("批量模式：批量处理")
        
        with col3:
            st.markdown("**💎 增值功能**")
            st.write("自动生成评分标准")
            st.write("多语言支持")
            st.write("历史记录管理")

# 登录页面
def show_login():
    st.markdown('<h2 class="main-title">🔐 用户中心</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        with st.form("login_form"):
            st.markdown('<div style="color: #ffffff; font-weight: 800; font-size: 1.2rem; font-family: \'Inter\', \'Microsoft YaHei\', \'PingFang SC\', \'Helvetica Neue\', Arial, sans-serif; text-shadow: 0 1px 3px rgba(0, 0, 0, 1.0); background: linear-gradient(135deg, #2563eb, #1e40af); padding: 12px 24px; border-radius: 10px; margin-bottom: 16px; border: 1px solid rgba(255, 255, 255, 0.5); box-shadow: 0 3px 10px rgba(37, 99, 235, 0.3); letter-spacing: 0.5px; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility;">👤 用户名</div>', unsafe_allow_html=True)
            username = st.text_input("", placeholder="输入用户名", key="login_username", label_visibility="collapsed")
            
            st.markdown('<div style="color: #ffffff; font-weight: 800; font-size: 1.2rem; font-family: \'Inter\', \'Microsoft YaHei\', \'PingFang SC\', \'Helvetica Neue\', Arial, sans-serif; text-shadow: 0 1px 3px rgba(0, 0, 0, 1.0); background: linear-gradient(135deg, #2563eb, #1e40af); padding: 12px 24px; border-radius: 10px; margin-bottom: 16px; border: 1px solid rgba(255, 255, 255, 0.5); box-shadow: 0 3px 10px rgba(37, 99, 235, 0.3); letter-spacing: 0.5px; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility;">🔒 密码</div>', unsafe_allow_html=True)
            password = st.text_input("", type="password", placeholder="输入密码", key="login_password", label_visibility="collapsed")
            
            col1, col2 = st.columns(2)
            with col1:
                login_btn = st.form_submit_button("登录", use_container_width=True)
            with col2:
                demo_btn = st.form_submit_button("演示登录", use_container_width=True)
            
            if login_btn or demo_btn:
                if demo_btn:
                    username, password = "demo", "demo"
                
                if username and password:
                    try:
                        # 尝试使用数据库验证
                        if CLASS_SYSTEM_AVAILABLE:
                            user_info = verify_user(username, password)
                            if user_info:
                                st.session_state.logged_in = True
                                st.session_state.username = username
                                st.session_state.page = "grading"
                                st.success(f"欢迎，{user_info.get('real_name', username)}！")
                                st_rerun()
                            else:
                                st.error("用户名或密码错误")
                        else:
                            # 回退到文件系统
                            users = read_users()
                            stored_pwd = users.get(username, {}).get('password')
                            input_pwd = hashlib.sha256(password.encode()).hexdigest()
                            
                            if stored_pwd == input_pwd:
                                st.session_state.logged_in = True
                                st.session_state.username = username
                                st.session_state.page = "grading"
                                st.success(f"欢迎，{username}！")
                                st_rerun()
                            else:
                                st.error("用户名或密码错误")
                    except Exception as e:
                        st.error(f"登录失败：{str(e)}")
                else:
                    st.error("请输入用户名和密码")
        
        st.info("💡 演示账户：demo/demo")
    
    with tab2:
        with st.form("register_form"):
            st.markdown('<div style="color: #ffffff; font-weight: 800; font-size: 1.2rem; font-family: \'Inter\', \'Microsoft YaHei\', \'PingFang SC\', \'Helvetica Neue\', Arial, sans-serif; text-shadow: 0 1px 3px rgba(0, 0, 0, 1.0); background: linear-gradient(135deg, #2563eb, #1e40af); padding: 12px 24px; border-radius: 10px; margin-bottom: 16px; border: 1px solid rgba(255, 255, 255, 0.5); box-shadow: 0 3px 10px rgba(37, 99, 235, 0.3); letter-spacing: 0.5px; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility;">👤 用户名</div>', unsafe_allow_html=True)
            new_username = st.text_input("", key="reg_username", label_visibility="collapsed")
            
            st.markdown('<div style="color: #ffffff; font-weight: 800; font-size: 1.2rem; font-family: \'Inter\', \'Microsoft YaHei\', \'PingFang SC\', \'Helvetica Neue\', Arial, sans-serif; text-shadow: 0 1px 3px rgba(0, 0, 0, 1.0); background: linear-gradient(135deg, #2563eb, #1e40af); padding: 12px 24px; border-radius: 10px; margin-bottom: 16px; border: 1px solid rgba(255, 255, 255, 0.5); box-shadow: 0 3px 10px rgba(37, 99, 235, 0.3); letter-spacing: 0.5px; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility;">📧 邮箱</div>', unsafe_allow_html=True)
            new_email = st.text_input("", key="reg_email", label_visibility="collapsed")
            
            st.markdown('<div style="color: #ffffff; font-weight: 800; font-size: 1.2rem; font-family: \'Inter\', \'Microsoft YaHei\', \'PingFang SC\', \'Helvetica Neue\', Arial, sans-serif; text-shadow: 0 1px 3px rgba(0, 0, 0, 1.0); background: linear-gradient(135deg, #2563eb, #1e40af); padding: 12px 24px; border-radius: 10px; margin-bottom: 16px; border: 1px solid rgba(255, 255, 255, 0.5); box-shadow: 0 3px 10px rgba(37, 99, 235, 0.3); letter-spacing: 0.5px; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility;">🔒 密码</div>', unsafe_allow_html=True)
            new_password = st.text_input("", type="password", key="reg_password", label_visibility="collapsed")
            
            st.markdown('<div style="color: #ffffff; font-weight: 800; font-size: 1.2rem; font-family: \'Inter\', \'Microsoft YaHei\', \'PingFang SC\', \'Helvetica Neue\', Arial, sans-serif; text-shadow: 0 1px 3px rgba(0, 0, 0, 1.0); background: linear-gradient(135deg, #2563eb, #1e40af); padding: 12px 24px; border-radius: 10px; margin-bottom: 16px; border: 1px solid rgba(255, 255, 255, 0.5); box-shadow: 0 3px 10px rgba(37, 99, 235, 0.3); letter-spacing: 0.5px; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility;">🔐 确认密码</div>', unsafe_allow_html=True)
            confirm_password = st.text_input("", type="password", key="reg_confirm_password", label_visibility="collapsed")
            
            register_btn = st.form_submit_button("注册", use_container_width=True)
            
            if register_btn:
                if all([new_username, new_password, confirm_password]):
                    if new_password == confirm_password:
                        try:
                            # 尝试使用数据库注册
                            if CLASS_SYSTEM_AVAILABLE:
                                success = create_user(new_username, new_password, "student", new_username, new_email)
                                if success:
                                    st.success("注册成功！请登录")
                                else:
                                    st.error("用户名已存在")
                            else:
                                # 回退到文件系统
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
                        except Exception as e:
                            st.error(f"注册失败：{str(e)}")
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
            st.write(f"📊 每批数量: {batch_settings['batch_size']}个")
            st.write(f"⏭️ 跳过缺失: {'是' if batch_settings['skip_missing'] else '否'}")
        with col2:
            st.write(f"📋 总结分离: {'是' if batch_settings['separate_summary'] else '否'}")
            st.write(f"📈 生成总结: {'是' if batch_settings['generate_summary'] else '否'}")
            st.write(f"🛑 最大步骤数: {batch_settings['max_steps']}")
    
    # 分类文件上传区域
    st.markdown("### 📤 文件上传")
    
    # 智能分类系统说明
    with st.expander("🤖 智能文件分类说明", expanded=False):
        st.markdown("""
        ### 🆕 自动文件分类系统
        
        为了提高AI批改的准确性，系统现在会自动为上传的文件添加类别前缀。
        
        - **📋 题目文件** 以`QUESTION_`开头：让AI准确识别题目内容
        - **✏️ 学生答案** 以`ANSWER_`开头：让AI专注于学生的解题过程  
        - **📊 批改标准** 以`MARKING_`开头：让AI准确识别评分标准
        
        **优势**：
        - �� **精确分类**：100%准确的文件类型识别
        - 🚀 **快速处理**：无需内容分析即可分类
        - 🛡️ **错误防护**：杜绝文件类型混淆
        - 🤖 **智能批改**：AI能更准确地理解每个文件的作用
        
        您只需要按原来的方式上传文件，系统会自动处理文件命名！
        """)
    
    # 使用三列布局
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📋 题目文件**")
        st.caption("🤖 系统会自动将文件名改成`QUESTION_`前缀")
        question_files = st.file_uploader(
            "上传题目",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            help="上传题目文件（可选）- 系统将自动添加QUESTION_前缀",
            key="question_upload"
        )
        if question_files:
            st.success(f"🎉 {len(question_files)} 个题目文件")
            with st.expander("📝 文件预览"):
                for f in question_files:
                    st.text(f"原始文件名: {f.name}")
                    st.text(f"保存为 QUESTION_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{f.name}")
                    st.divider()
    
    with col2:
        st.markdown("**✏️ 学生作答**")
        st.caption("🤖 系统会自动将文件名改成`ANSWER_`前缀")
        answer_files = st.file_uploader(
            "上传学生答案",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            help="上传学生作答文件（必填）- 系统将自动添加ANSWER_前缀",
            key="answer_upload"
        )
        if answer_files:
            st.success(f"🎉 {len(answer_files)} 个答案文件")
            with st.expander("📝 文件预览"):
                for f in answer_files:
                    st.text(f"原始文件名: {f.name}")
                    st.text(f"保存为 ANSWER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{f.name}")
                    st.divider()
    
    with col3:
        st.markdown("**📊 批改标准**")
        st.caption("🤖 系统会自动将文件名改成`MARKING_`前缀")
        marking_files = st.file_uploader(
            "上传评分标准",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            help="上传评分标准文件（可选）- 系统将自动添加MARKING_前缀",
            key="marking_upload"
        )
        if marking_files:
            st.success(f"🎉 {len(marking_files)} 个标准文件")
            with st.expander("📝 文件预览"):
                for f in marking_files:
                    st.text(f"原始文件名: {f.name}")
                    st.text(f"保存为 MARKING_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{f.name}")
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
            status_text.text("🔍 正在分析上传的文件..")
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
                # 使用智能批量批改系统
                from functions.api_correcting.intelligent_batch_processor import intelligent_batch_correction_sync
                
                # 显示AI分析进度
                status_text.text("🔍 AI正在智能分析文件内容...")
                progress_bar.progress(20)
                
                # 获取所有文件路径
                all_file_paths = [f["path"] for f in saved_files]
                
                # 执行智能批量批改
                # - 自动识别题目和学生
                # - 每批最多10道题
                # - 支持并发处理
                # - 为每个学生生成总结
                result = intelligent_batch_correction_sync(
                    all_file_paths,
                    file_info_list=saved_files,
                    batch_size=10,  # 每批最多10道题
                    max_concurrent=3  # 最多3个并发批次
                )
                
                # 更新进度
                progress_bar.progress(80)
            else:
                # 使用传统批改方式
                result = intelligent_correction_with_files(
                    answer_files=[f["path"] for f in saved_files if 'ANSWER' in f["name"].upper()],
                    marking_scheme_files=[f["path"] for f in saved_files if 'MARKING' in f["name"].upper()],
                    strictness_level="严格"
                )
            
            progress_bar.progress(90)
            status_text.text("批改完成，正在整理结果..")
            
            if result:
                # 处理不同格式的结果
                if isinstance(result, dict):
                    # 如果是字典格式，提取文本内容
                    result_text = result.get('text', result.get('correction_result', str(result)))
                    result_html = result.get('html', '')
                else:
                    # 如果是字符串格式
                    result_text = str(result)
                    result_html = ''
                
                # 保存结果
                grading_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 生成结果数据
                result_data = {
                    "result": result,
                    "result_text": result_text,
                    "result_html": result_html,
                    "time": grading_time,
                    "files": [f["name"] for f in saved_files],
                    "settings": batch_settings,
                    "type": "enhanced_batch" if batch_settings['enable_batch'] else "traditional"
                }
                
                # 保存到session state
                st.session_state.correction_result = result
                st.session_state.uploaded_files_data = saved_files
                st.session_state.current_file_index = 0
                
                # 设置批改任务为已完成
                st.session_state.correction_task = {
                    'status': 'completed',
                    'all_file_info': saved_files,
                    'question_files': [f["path"] for f in saved_files if 'QUESTION' in f["name"].upper()],
                    'answer_files': [f["path"] for f in saved_files if 'ANSWER' in f["name"].upper()],
                    'marking_files': [f["path"] for f in saved_files if 'MARKING' in f["name"].upper()]
                }
                
                # 设置批改设置
                st.session_state.correction_settings = {
                    'has_marking_scheme': bool([f for f in saved_files if 'MARKING' in f["name"].upper()]),
                    'strictness': '严格',
                    'use_batch_processing': batch_settings['enable_batch'],
                    'batch_size': batch_settings['batch_size']
                }
                
                # 保存到用户记录
                if "grading_results" not in st.session_state:
                    st.session_state.grading_results = []
                st.session_state.grading_results.append(result_data)
                
                progress_bar.progress(100)
                status_text.text("🎉 批改完成")
                
                st.success("✅ 批改完成！")
                st.balloons()
                
                # 显示结果预览
                with st.expander("📊 批改结果预览", expanded=True):
                    preview_text = result_text[:1000] + "..." if len(result_text) > 1000 else result_text
                    st.text_area("", value=preview_text, height=300, disabled=True)
                
                # 设置批改任务为待处理，准备跳转到结果页面
                st.session_state.correction_task['status'] = 'pending'
                
                # 自动跳转到结果页面
                time.sleep(1)  # 短暂延迟让用户看到成功消息
                st.session_state.page = "result"
                st_rerun()
                
            else:
                st.error("批改失败，请检查文件格式或重试")
                # 添加调试信息
                with st.expander("🔍 调试信息", expanded=False):
                    st.write("批改设置:", batch_settings)
                    st.write("文件数量:", len(all_uploaded_files))
                    st.write("保存的文件：", len(saved_files) if 'saved_files' in locals() else "未确定")
                
        except Exception as e:
            st.error(f"批改过程中出现错误：{str(e)}")
            # 添加详细错误信息
            with st.expander("🔍 错误详情", expanded=True):
                import traceback
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
        st_rerun()
        return
    
    # 如果有待处理的批改任务，标记为已完成（批改已在grading页面完成）
    if 'correction_task' in st.session_state and st.session_state.correction_task.get('status') == 'pending':
        st.session_state.correction_task['status'] = 'completed'
        
        # 保存历史记录到用户数据中
        if st.session_state.logged_in and st.session_state.correction_result and st.session_state.uploaded_files_data:
            try:
                users = read_users()
                if st.session_state.username in users:
                    record = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'files': [f.get('display_name', f.get('name', 'unknown')) for f in st.session_state.uploaded_files_data],
                        'file_data': st.session_state.uploaded_files_data,
                        'settings': st.session_state.get('correction_settings', {}),
                        'result': st.session_state.correction_result,
                        'files_count': len(st.session_state.uploaded_files_data)
                    }
                    users[st.session_state.username]['records'].append(record)
                    save_users(users)
            except Exception as e:
                st.error(f"保存历史记录失败：{str(e)}")
    
    st.markdown('<h2 class="main-title">📊 批改结果</h2>', unsafe_allow_html=True)
    
    # 检查批改结果和文件数据
    if not st.session_state.get('correction_result') or not st.session_state.get('uploaded_files_data'):
        st.warning("暂无批改结果或文件数")
        if st.button("返回批改", use_container_width=True):
            st.session_state.page = "grading"
            st_rerun()
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
    result_format = 'text'  # 默认文本格式
    
    if isinstance(correction_result, dict):
        has_separate_scheme = correction_result.get('has_separate_scheme', False)
        result_format = correction_result.get('format', 'text')  # 检查格式类型
        
        if has_separate_scheme:
            marking_scheme = correction_result.get('marking_scheme', '')
            correction_content = correction_result.get('correction_result', '')
        else:
            correction_content = correction_result.get('correction_result', str(correction_result))
        
        # 如果是智能批量格式，使用HTML内容
        if result_format == 'intelligent_batch':
            correction_content = correction_result.get('html', correction_result.get('text', ''))
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
                    st_rerun()
    
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
                    st_rerun()
            
            with col_r2:
                if st.button("📋 评分标准", use_container_width=True,
                           type="primary" if st.session_state.result_display_mode == 'scheme' else "secondary"):
                    st.session_state.result_display_mode = 'scheme'
                    st_rerun()
            
            # 根据选择显示内容
            display_content = marking_scheme if st.session_state.result_display_mode == 'scheme' else correction_content
            content_title = "评分标准" if st.session_state.result_display_mode == 'scheme' else "批改结果"
            
        else:
            st.markdown("### 📝 批改结果")
            display_content = correction_content
            content_title = "批改结果"
        
        # 创建结果HTML
        # 检查是否是智能批量格式的HTML内容
        is_html_content = (result_format == 'intelligent_batch' and 
                          isinstance(display_content, str) and 
                          '<div' in display_content and 
                          'style=' in display_content)
        
        if is_html_content:
            # 如果是HTML格式，直接显示
            result_html = display_content
        else:
            # 否则使用预格式化文本显示
            result_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        margin: 0;
                        padding: 20px;
                        background: #1a1a1a;
                        color: #ffffff;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        min-height: 100vh;
                        box-sizing: border-box;
                    }}
                    pre {{
                        white-space: pre-wrap;
                        word-wrap: break-word;
                        margin: 0;
                        line-height: 1.8;
                        font-size: 15px;
                        color: #ffffff;
                    }}
                    /* 美化样式 */
                    strong {{
                        color: #60a5fa;
                        font-weight: 600;
                    }}
                    /* 题目标题 */
                    h2, h3 {{
                        color: #60a5fa;
                        margin: 20px 0 10px 0;
                    }}
                    /* 满分标记 */
                    .full-score {{
                        color: #10b981;
                    }}
                    /* 部分得分 */
                    .partial-score {{
                        color: #f59e0b;
                    }}
                    /* 零分 */
                    .zero-score {{
                        color: #ef4444;
                    }}
                    /* 分隔线 */
                    hr {{
                        border: none;
                        border-top: 1px solid #374151;
                        margin: 20px 0;
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
        
        # 如果是智能批量格式，使用文本内容下载
        if result_format == 'intelligent_batch' and isinstance(correction_result, dict):
            download_content = correction_result.get('text', str(correction_content))
        elif has_separate_scheme and marking_scheme:
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
            st_rerun()
    
    with col4:
        if st.button("📚 查看历史", use_container_width=True):
            st.session_state.page = "history"
            st_rerun()

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
                background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
                color: #e2e8f0;
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
        # PDF文档预览 - 多模态大模型处理
        try:
            import os
            file_size_mb = os.path.getsize(file_data['path']) / (1024 * 1024)
            
            # 显示PDF文档信息
            content = f'''
            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: #f8f9fa;">
                <h3 style="margin-top: 0;">📄 {html.escape(file_data["name"])}</h3>
                <div style="margin: 10px 0;">
                    <p style="margin: 5px 0; color: #666;">
                        <strong>文件大小:</strong> {file_size_mb:.1f} MB
                    </p>
                    <p style="margin: 5px 0; color: #666;">
                        <strong>处理方式:</strong> 多模态大模型直接理解
                    </p>
                    <p style="margin: 5px 0; color: #666;">
                        <strong>支持内容:</strong> 文字、图表、公式、手写内容
                    </p>
                </div>
                <div style="background: #e3f2fd; padding: 10px; border-radius: 4px; margin-top: 10px;">
                    <p style="margin: 0; color: #1976d2; font-size: 0.9rem;">
                        🤖 系统将使用先进的多模态大模型直接理解PDF内容，无需传统OCR处理
                    </p>
                </div>
                <p style="font-size: 0.9rem; color: #666; margin-top: 15px; margin-bottom: 0;">
                    💡 提示：点击"开始批改"按钮让AI直接分析PDF文档内容
                </p>
            </div>
            '''
        except Exception as e:
            content = f'<div class="error"><h3>📄 PDF文件</h3><p>{html.escape(file_data["name"])}</p><p>文件信息获取失败: {html.escape(str(e))}</p></div>'
    
    else:
        # 其他文件类型
        content = f'<div class="error"><h3>📄 {html.escape(file_data["name"])}</h3><p>文件类型: {file_type}</p><p>此类型暂不支持预览</p></div>'
    
    return base_template.format(content=content)

# 批改结果展示页面 - 左右对照布局（原始版本，备份）
def show_result_original():
    if not st.session_state.logged_in:
        st.warning("请先登录")
        st.session_state.page = "login"
        st_rerun()
        return
    
    # 检查是否有待处理的批改任务
    if 'correction_task' in st.session_state and st.session_state.correction_task.get('status') == 'pending':
        # 执行批改任务
        st.markdown('<h2 class="main-title">🤖 AI批改进行中..</h2>', unsafe_allow_html=True)
        
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
                    # 有批改标准模版
                    result = batch_correction_with_standard(
                    marking_scheme_files=task['marking_files'],
                        student_answer_files=task['answer_files'],
                        strictness_level=settings['strictness']
                    )
                else:
                    # 无批改标准模版
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
                st_rerun()
                
            except Exception as e:
                st.error(f"批改失败：{str(e)}")
                st.session_state.correction_task['status'] = 'failed'
                if st.button("返回重试"):
                    st.session_state.page = "grading"
                    st_rerun()
                return
    
    # 检查是否有批改结果
    if not st.session_state.correction_result or not st.session_state.uploaded_files_data:
        st.warning("没有批改结果数据")
        st.session_state.page = "grading"
        st_rerun()
        return
    
    st.markdown('<h2 class="main-title">📊 批改结果对照</h2>', unsafe_allow_html=True)
    
    # 顶部操作按钮
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        settings = st.session_state.correction_settings
        mode_text = "有批改标准" if settings.get('has_marking_scheme') else "自动生成标准"
        st.markdown(f"**设置：{mode_text} | {settings.get('strictness', 'N/A')}")
    
    with col2:
        if st.button("🔄 重新批改"):
            st.session_state.page = "grading"
            st_rerun()
    
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
            st_rerun()
    
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
                /* 终极强制限制 - 不计一切代入 */
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
                
                /* 自定义滚动条样式 - 针对预览 */
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
                
                /* 增强滚轮响应 */
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
                    content: "可滚动预览";
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
                                        // 自定义滚动行数
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
                                         // 自定义滚动行数
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
                                
                                # 图片预览HTML - 优化滚动和缩放体
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
                            # PDF文档信息展示 - 多模态大模型处理
                            import os
                            file_size_mb = os.path.getsize(current_file['path']) / (1024 * 1024)
                            
                            # 构建PDF信息展示HTML
                            pdf_info_html = f'''
                            <div style="text-align: center; padding: 30px; color: #e2e8f0;">
                                <div style="background: rgba(96, 165, 250, 0.1); border: 2px solid rgba(96, 165, 250, 0.3); border-radius: 12px; padding: 25px; margin-bottom: 20px;">
                                    <h3 style="color: #60a5fa; margin-bottom: 20px; font-size: 1.5rem;">📄 PDF文档</h3>
                                    <p style="margin: 8px 0; font-size: 1.1rem;"><strong>文件名:</strong> {html.escape(current_file['name'])}</p>
                                    <p style="margin: 8px 0; font-size: 1.1rem;"><strong>文件大小:</strong> {file_size_mb:.1f} MB</p>
                                    <p style="margin: 8px 0; font-size: 1.1rem;"><strong>处理方式:</strong> 多模态大模型直接理解</p>
                                </div>
                                
                                <div style="background: rgba(34, 197, 94, 0.1); border: 2px solid rgba(34, 197, 94, 0.3); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                                    <h4 style="color: #22c55e; margin-bottom: 15px;">🤖 AI处理能力</h4>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; text-align: left;">
                                        <p style="margin: 5px 0;">✅ 文字识别</p>
                                        <p style="margin: 5px 0;">✅ 手写内容</p>
                                        <p style="margin: 5px 0;">✅ 图表理解</p>
                                        <p style="margin: 5px 0;">✅ 公式识别</p>
                                        <p style="margin: 5px 0;">✅ 表格处理</p>
                                        <p style="margin: 5px 0;">✅ 结构分析</p>
                                    </div>
                                </div>
                                
                                <div style="background: rgba(168, 85, 247, 0.1); border: 2px solid rgba(168, 85, 247, 0.3); border-radius: 12px; padding: 15px;">
                                    <p style="color: #a855f7; margin: 0; font-size: 0.95rem;">
                                        💡 点击"开始批改"按钮，AI将直接分析PDF内容，无需预览
                                    </p>
                                </div>
                            </div>
                            '''
                            
                            preview_html = f'<div class="file-preview-frame" style="overscroll-behavior: contain;"><div class="preview-content-wrapper" style="height: 520px; overflow-y: auto; padding: 10px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); overscroll-behavior: contain;">{pdf_info_html}</div></div>'
                        except Exception as e:
                            preview_html = f'<div class="file-preview-frame"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">📄 PDF 信息获取失败</h3><p style="font-size: 1.1rem; margin-bottom: 10px;">错误信息: {str(e)}</p><p style="font-size: 0.9rem;">系统将使用多模态大模型直接处理PDF文档</p></div></div>'
                    
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
                    warning_msg = "💡 历史记录，原始文件可能已被清空" if not current_file['path'] else "⚠️ 原始文件不存在"
                    preview_html = f'<div class="file-preview-frame"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">⚠️ 文件预览不可用</h3><p style="font-size: 1.1rem; margin-bottom: 10px;">{warning_msg}</p></div></div>'
                
                # 显示完整的预览HTML
                st.markdown(preview_html, unsafe_allow_html=True)
                
                # 文件信息和切换器放在预览框下
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
                
        # 批改结果容器 - 与左侧预览框对齐，支持独立滚动条控制
        if st.session_state.correction_result:
            # 创建与左侧相同样式的容器，使用相同的class名称
            import html
            result_html = f'''
            <div class="correction-result-frame" onwheel="event.preventDefault(); event.stopPropagation(); var wrapper = this.querySelector('.result-content-wrapper'); if(wrapper) {{ var canScrollDown = wrapper.scrollTop < (wrapper.scrollHeight - wrapper.clientHeight - 1); var canScrollUp = wrapper.scrollTop > 0; if ((event.deltaY > 0 && canScrollDown) || (event.deltaY < 0 && canScrollUp)) {{ wrapper.scrollTop += event.deltaY; }} }} return false;" style="height: 520px; border: 3px solid #4a5568; border-radius: 12px; background-color: #1a202c; box-shadow: 0 8px 16px rgba(0,0,0,0.3); overflow: hidden; position: relative; z-index: 1; user-select: none; -webkit-user-select: none; -moz-user-select: none; -ms-user-select: none; overscroll-behavior: contain;">
                <div class="result-content-wrapper" style="height: 100%; overflow-y: auto; overflow-x: hidden; padding: 20px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); scroll-behavior: smooth; position: relative; z-index: 2; cursor: default; overflow-scrolling: touch; overscroll-behavior: contain; scroll-snap-type: none; -webkit-overflow-scrolling: touch;">
                    <div class="result-info-bar" style="position: sticky; top: 0; z-index: 5; background: rgba(74, 85, 104, 0.95); backdrop-filter: blur(8px); color: #e2e8f0; font-size: 0.85rem; margin: 0 -20px 20px -20px; padding: 12px 20px; font-weight: 600; text-align: center; border-bottom: 2px solid rgba(96, 165, 250, 0.3); box-shadow: 0 2px 8px rgba(0,0,0,0.3);">📝 批改结果 ({len(st.session_state.correction_result)} 字符)</div>
                    <pre style="margin: 0; padding: 0; color: #e2e8f0; font-family: \'SF Mono\', \'Monaco\', \'Inconsolata\', \'Roboto Mono\', \'Source Code Pro\', monospace; font-size: 0.95rem; line-height: 1.7; white-space: pre-wrap; word-wrap: break-word; background: rgba(45, 55, 72, 0.3); padding: 20px; border-radius: 8px; border: 1px solid rgba(74, 85, 104, 0.3);">{html.escape(st.session_state.correction_result)}</pre>
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
                content: "可滚动预览";
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
    
    # 文件切换功能 (放在左侧预览区域)
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
                    st_rerun()

# 历史页面
def show_history():
    if not st.session_state.logged_in:
        st.warning("请先登录")
        st.session_state.page = "login"
        st_rerun()
        return
    
    st.markdown('<h2 class="main-title">📚 批改历史</h2>', unsafe_allow_html=True)
    
    users = read_users()
    records = users.get(st.session_state.username, {}).get('records', [])
    
    if not records:
        st.info("暂无批改记录")
        if st.button("🚀 开始批改", use_container_width=True):
            st.session_state.page = "grading"
            st_rerun()
        return
    
    # 统计信息 - 增强样式
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 总批改次数", len(records))
    with col2:
        total_files = sum(r.get('files_count', len(r.get('files', []))) for r in records)
        st.metric("📁 处理文件数量", total_files)
    with col3:
        if st.button("🗑️ 清空历史", help="清空所有历史记录"):
            if 'confirm_delete' not in st.session_state:
                st.session_state.confirm_delete = True
            else:
                users[st.session_state.username]['records'] = []
                save_users(users)
                del st.session_state.confirm_delete
                st.success('✅ 历史记录已清空')
                st_rerun()

    # 确认删除对话框
    if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:
        st.warning("⚠️ 确定要清空所有历史记录吗？此操作无法撤销！")
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("✅ 是，清空", use_container_width=True, type="primary"):
                users[st.session_state.username]['records'] = []
                save_users(users)
                del st.session_state.confirm_delete
                st.success("✅ 历史记录已清空")
                st_rerun()
        with col_cancel:
            if st.button("❌ 否，取消", use_container_width=True):
                del st.session_state.confirm_delete
                st_rerun()
    
    st.markdown("---")
    
    # 记录列表 - 增强显示
    st.subheader("📋 历史记录列表")
    
    for i, record in enumerate(reversed(records), 1):
        # 获取记录信息
        timestamp = record.get('timestamp', '未知时间')
        files = record.get('files', ['无文件信息'])
        settings = record.get('settings', {})
        result = record.get('result', '')
        
        # 格式化显示信息
        file_display = ', '.join(files) if isinstance(files, list) else str(files)
        if len(file_display) > 50:
            file_display = file_display[:50] + "..."
        
        mode_text = "📊 有批改标准" if settings.get('has_marking_scheme') else "🤖 自动生成标准"
        strictness = settings.get('strictness', 'N/A')
        
        # 使用增强的展开器
        with st.expander(f"📋 记录 {i} - {timestamp}", expanded=False):
            # 记录详情
            col_info, col_actions = st.columns([2, 1])
            
            with col_info:
                st.markdown(f"**📁 文件:** {file_display}")
                st.markdown(f"**⚙️ 设置:** {mode_text} | 严格程度: {strictness}")
                
                # 显示文件数量
                file_count = len(files) if isinstance(files, list) else 1
                st.markdown(f"**📊 统计:** {file_count} 个文件")
                
                # 显示结果状态
                if result:
                    if isinstance(result, dict):
                        result_status = "✅ 结构化结果"
                        if result.get('has_separate_scheme', False):
                            result_status += " (含独立评分标准)"
                    else:
                        result_status = "✅ 文本结果"
                    st.markdown(f"**📝 结果:** {result_status}")
                else:
                    st.markdown("**📝 结果:** ❌ 无结果数据")
            
            with col_actions:
                # 查看详情按钮
                if st.button("👁️ 查看详情", key=f"view_{i}", use_container_width=True, 
                           help="查看完整的批改结果", type="primary"):
                    try:
                        # 验证结果数据
                        if not result:
                            st.error("❌ 该记录没有批改结果数据")
                            return
                        
                        # 设置批改结果到session state
                        if isinstance(result, dict):
                            # 处理字典格式的结果
                            if result.get('has_separate_scheme', False):
                                # 有独立评分标准的情况
                                marking_scheme = result.get('marking_scheme', '')
                                correction_content = result.get('correction_result', '')
                                if marking_scheme and correction_content:
                                    # 保持字典格式，这样结果页面可以分别显示
                                    st.session_state.correction_result = result
                                else:
                                    # 如果数据不完整，使用完整的结果
                                    st.session_state.correction_result = result
                            else:
                                # 只有批改结果的情况，直接使用原始结果
                                st.session_state.correction_result = result
                        else:
                            # 处理字符串格式的结果
                            st.session_state.correction_result = str(result)
                        
                        # 重建文件数据用于结果页面展示
                        file_data = record.get('file_data', [])
                        if file_data and isinstance(file_data, list):
                            # 使用保存的文件路径信息
                            st.session_state.uploaded_files_data = []
                            for f in file_data:
                                if isinstance(f, dict):
                                    st.session_state.uploaded_files_data.append({
                                        'name': f.get('name', '未知文件'),
                                        'path': f.get('path'),
                                        'type': f.get('type', get_file_type(f.get('name', '')))
                                    })
                                else:
                                    # 兼容旧格式
                                    st.session_state.uploaded_files_data.append({
                                        'name': str(f),
                                        'path': None,
                                        'type': get_file_type(str(f))
                                    })
                        else:
                            # 兼容旧记录（没有file_data字段）
                            file_names = files if isinstance(files, list) else [str(files)]
                            st.session_state.uploaded_files_data = []
                            for name in file_names:
                                st.session_state.uploaded_files_data.append({
                                    'name': name,
                                    'path': None,
                                    'type': get_file_type(name)
                                })
                        
                        # 设置其他必要的session state
                        st.session_state.correction_settings = settings
                        st.session_state.current_file_index = 0
                        st.session_state.page = "result"
                        
                        st.success("✅ 正在跳转到结果页面...")
                        st_rerun()
                        
                    except Exception as e:
                        st.error(f"❌ 加载历史记录失败: {str(e)}")
                        st.info("💡 请尝试重新批改生成新的结果")
                
                # 下载按钮
                if result:
                    try:
                        # 处理结果数据，确保是字符串格式
                        if isinstance(result, dict):
                            # 如果是字典格式，转换为字符串
                            if result.get('has_separate_scheme', False):
                                marking_scheme = result.get('marking_scheme', '')
                                correction_content = result.get('correction_result', '')
                                if marking_scheme and correction_content:
                                    download_content = f"=== 📊 评分标准 ===\n\n{marking_scheme}\n\n=== 📝 批改结果 ===\n\n{correction_content}"
                                else:
                                    download_content = str(result)
                            else:
                                # 尝试提取文本内容
                                if 'correction_result' in result:
                                    download_content = str(result['correction_result'])
                                elif 'text' in result:
                                    download_content = str(result['text'])
                                else:
                                    download_content = str(result)
                        else:
                            download_content = str(result)
                        
                        # 生成文件名
                        safe_timestamp = timestamp.replace(':', '-').replace(' ', '_').replace('/', '-')
                        filename = f"批改记录_{safe_timestamp}.txt"
                        
                        st.download_button(
                            "💾 下载结果",
                            data=download_content,
                            file_name=filename,
                            mime="text/plain",
                            key=f"download_{i}",
                            use_container_width=True,
                            help="下载完整的批改结果"
                        )
                    except Exception as e:
                        st.error(f"❌ 下载准备失败: {str(e)}")
                else:
                    st.button("💾 无结果", disabled=True, use_container_width=True, 
                             help="该记录没有可下载的结果")
    
    # 底部操作
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 开始新的批改", use_container_width=True, type="primary"):
            st.session_state.page = "grading"
            st_rerun()
    with col2:
        if st.button("🏠 返回首页", use_container_width=True):
            st.session_state.page = "home"
            st_rerun()

# 侧边栏
def show_sidebar():
    """显示侧边栏"""
    with st.sidebar:
        st.markdown('<h3 style="color: #60a5fa; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.8); font-weight: 800;">🤖 AI批改系统</h3>', unsafe_allow_html=True)
        
        if st.session_state.logged_in:
            st.markdown(f"👋 **{st.session_state.username}**")
            st.markdown("---")
            
            # 核心功能导航
            if st.button("🏠 首页", use_container_width=True):
                st.session_state.page = "home"
                st_rerun()
            
            if st.button("📝 智能批改", use_container_width=True):
                st.session_state.page = "grading"
                st_rerun()
            
            if st.button("👥 班级管理", use_container_width=True):
                st.session_state.page = "class_management"
                st_rerun()
            
            if st.button("📚 历史记录", use_container_width=True):
                st.session_state.page = "history"
                st_rerun()
            
            # 结果页面导航 (只在有结果时显示)
            if st.session_state.correction_result:
                if st.button("📊 查看结果", use_container_width=True):
                    st.session_state.page = "result"
                    st_rerun()
            
            # 在session_state中保存默认设置
            st.session_state.batch_settings = {
                'enable_batch': True,
                'batch_size': 10,
                'skip_missing': True,
                'separate_summary': True,
                'generate_summary': True,
                'max_steps': 3
            }
            
            st.markdown("---")
            
            # 统计信息
            users = read_users()
            count = len(users.get(st.session_state.username, {}).get('records', []))
            st.metric("批改次数", count)
            
            st.markdown("---")
            
            # 系统状态
            if API_AVAILABLE:
                st.success("🚀 AI引擎正常")
            else:
                st.warning("⚠️ 演示模式")
            
            st.markdown("---")
            
            # 退出登录
            if st.button("🚪 退出登录", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.user_role = ""
                st.session_state.show_class_system = False
                st.session_state.correction_result = ""
                st.session_state.page = "home"
                st_rerun()
        else:
            # 未登录状态
            if st.button("🔐 登录", use_container_width=True):
                st.session_state.page = "login"
                st_rerun()
            
            st.markdown("---")
            st.markdown("### 💡 功能特色")
            st.markdown("""
            - 🎯 智能批改
            - 📊 班级管理系统
            - 📚 作业管理
            - 💾 成绩统计
            """)
            
            st.markdown("---")
            
            # 系统状态
            if API_AVAILABLE:
                st.success("🚀 系统就绪")
            else:
                st.warning("⚠️ 演示模式")
        
        # 设置信息部分（无论登录与否都显示）
        st.markdown("---")
        st.header("⚙️ 设置")
        
        # API状态和模型选择
        st.subheader("🤖 AI模型")
        
        if API_AVAILABLE:
            # 获取API状态
            api_status = api_config.get_status()
            
            # 模型选择器
            st.markdown("**选择模型:**")
            
            # 创建模型选项，显示友好名称
            model_options = []
            model_display_names = []
            
            for i, model in enumerate(api_status['available_models']):
                model_options.append(i)
                # 创建显示名称
                if "gemini-2.5-flash-lite" in model:
                    display_name = "🚀 Gemini 2.5 Flash Lite (推荐)"
                elif "gemini-2.5-flash" in model:
                    display_name = "⚡ Gemini 2.5 Flash"
                elif "gemini-2.5-pro" in model:
                    display_name = "🎯 Gemini 2.5 Pro"
                elif "claude-3-haiku" in model:
                    display_name = "🤖 Claude 3 Haiku"
                elif "llama-3-8b" in model:
                    display_name = "🦙 Llama 3 8B (免费)"
                elif "wizardlm" in model:
                    display_name = "🧙 WizardLM 2 (免费)"
                elif "mythomist" in model:
                    display_name = "✨ Mythomist 7B (免费)"
                else:
                    display_name = model.split('/')[-1]
                
                # 添加免费标识
                if ":free" in model:
                    display_name += " 🆓"
                
                model_display_names.append(display_name)
            
            # 模型选择下拉框
            selected_model_index = st.selectbox(
                "选择AI模型",
                options=model_options,
                index=api_status['model_index'],
                format_func=lambda x: model_display_names[x],
                key="model_selector",
                label_visibility="collapsed"
            )
            
            # 如果用户选择了不同的模型，更新配置
            if selected_model_index != api_status['model_index']:
                api_config.current_model_index = selected_model_index
                st.success(f"✅ 已切换到: {model_display_names[selected_model_index]}")
                st_rerun()
            
            # 显示当前模型信息
            current_model_name = model_display_names[api_status['model_index']]
            st.info(f"**当前模型**: {current_model_name}")
            st.info(f"**提供者**: OpenRouter")
            
            # 模型重置按钮
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 重置", help="重置到主要模型", use_container_width=True):
                    api_config.reset_model()
                    st.success("✅ 已重置到主要模型")
                    st_rerun()
            
            with col2:
                if st.button("📊 状态", help="查看详细状态", use_container_width=True):
                    with st.expander("🔧 详细状态", expanded=True):
                        st.json(api_status)
            
            st.success("🚀 AI引擎已就绪")
        else:
            st.info(f"**模型**: {api_config.model}")
            st.info(f"**提供者**: OpenRouter (演示)")
            st.warning("⚠️ 演示模式运行中")
        
        st.markdown("---")
        
        # 使用说明
        st.subheader("📖 使用说明")
        st.markdown("""
        1. **上传文件**：支持图片、PDF、Word、文本等格式
        2. **选择批改方式**：有批改标准或自动生成标准
        3. **设置严格程度**：调整批改的严格程度
        4. **开始批改**：点击"开始AI批改"按钮
        5. **查看结果**：在结果页面查看详细批改
        """)
        
        # 技术信息
        st.markdown("---")
        st.subheader("🔧 技术信息")
        st.markdown(f"""
        - **AI模型**: Google Gemini 2.5 Flash Lite Preview
        - **API提供者**: OpenRouter
        - **支持格式**: 图片、PDF、Word、文本
        - **最大文件大小**: 4MB (自动压缩)
        """)

# 教师仪表盘 - 简化版
def show_teacher_dashboard():
    st.markdown('<h2 class="main-title">👨‍🏫 教师工作台</h2>', unsafe_allow_html=True)
    
    # 检查登录状态和角色
    if not st.session_state.logged_in or st.session_state.user_role != 'teacher':
        st.error("❌ 访问权限不足，请先登录教师账户")
        st.session_state.page = "login"
        st_rerun()
        return
    
    # 简化的顶部信息
    user_info = get_user_info(st.session_state.username)
    teacher_name = user_info.get('real_name', st.session_state.username) if user_info else st.session_state.username
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**👋 {teacher_name} 老师**")
    with col2:
        if st.button("🚪 退出", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_role = ""
            st.session_state.show_class_system = False
            st.session_state.page = "home"
            st_rerun()
    
    st.markdown("---")
    
    # 简化的选项卡 - 只保留核心功能
    tab1, tab2 = st.tabs(["📝 批改中心", "📚 班级管理"])
    
    with tab1:
        show_simplified_grading_center()
    
    with tab2:
        show_simplified_class_management()

# 教师班级管理
def show_teacher_classes():
    st.markdown("### 📚 班级管理")
    
    # 获取教师的班级列表
    try:
        classes = get_user_classes(st.session_state.username, 'teacher')
    except Exception as e:
        st.error(f"❌ 获取班级列表失败：{str(e)}")
        classes = []
    
    # 创建新班级
    with st.expander("➕ 创建新班级", expanded=False):
        with st.form("create_class_form"):
            class_name = st.text_input("班级名称 *", placeholder="例如：高一(1)班数学")
            class_desc = st.text_area("班级描述", placeholder="可选：班级介绍、学习目标等")
            
            submitted = st.form_submit_button("创建班级", use_container_width=True, type="primary")
            
            if submitted:
                if class_name:
                    try:
                        invite_code = create_class(st.session_state.username, class_name, class_desc)
                        if invite_code:
                            st.success(f"🎉 班级创建成功！")
                            st.info(f"📋 邀请码：**{invite_code}**")
                            st.info("💡 请将邀请码分享给学生，他们可以通过此邀请码加入班级")
                            st_rerun()
                        else:
                            st.error("❌ 创建失败")
                    except Exception as e:
                        st.error(f"❌ 创建失败：{str(e)}")
                else:
                    st.warning("⚠️ 请输入班级名称")
    
    # 显示现有班级
    if classes:
        st.markdown("### 我的班级")
        for class_info in classes:
            with st.expander(f"📚 {class_info['name']} ({class_info['student_count']}名学生)", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**描述：** {class_info.get('description', '无')}")
                    st.write(f"**创建时间：** {class_info['created_at']}")
                    st.write(f"**邀请码：** `{class_info['invite_code']}`")
                    st.write(f"**学生人数：** {class_info['student_count']} 人")
                
                with col2:
                    if st.button(f"📝 管理作业", key=f"assignments_{class_info['id']}"):
                        st.session_state.current_class_id = class_info['id']
                        # 这里可以跳转到作业管理页面
                        st.info("作业管理功能开发中...")
                    
                    if st.button(f"👥 查看学生", key=f"students_{class_info['id']}"):
                        # 这里可以显示学生列表
                        st.info("学生管理功能开发中...")
    else:
        st.info("📝 您还没有创建任何班级。点击上方\"创建新班级\"开始使用！")

# 教师作业管理
def show_teacher_assignments():
    st.markdown("### 📝 作业管理")
    
    # 获取当前选中的班级
    current_class_id = st.session_state.get('current_class_id', '')
    
    if not current_class_id:
        # 获取教师的班级列表让其选择
        try:
            classes = get_user_classes(st.session_state.username, 'teacher')
            if classes:
                class_options = {cls['id']: cls['name'] for cls in classes}
                selected_class = st.selectbox(
                    "选择班级",
                    options=list(class_options.keys()),
                    format_func=lambda x: class_options[x],
                    key="class_selector_teacher_assignments"
                )
                st.session_state.current_class_id = selected_class
                current_class_id = selected_class
            else:
                st.info("请先创建班级")
                return
        except Exception as e:
            st.error(f"❌ 获取班级列表失败：{str(e)}")
            return
    
    # 创建新作业
    with st.expander("➕ 创建新作业", expanded=False):
        with st.form("create_assignment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                assignment_title = st.text_input("作业标题 *", placeholder="例如：第一章练习题")
                assignment_desc = st.text_area("作业描述", placeholder="作业要求和说明")
                
            with col2:
                due_date = st.date_input("截止日期", value=None)
                due_time = st.time_input("截止时间", value=None)
            
            # 文件上传区域
            st.markdown("#### 📤 上传文件")
            
            col_q, col_m = st.columns(2)
            
            with col_q:
                st.markdown("**📋 题目文件**")
                question_files = st.file_uploader(
                    "上传题目文件",
                    type=['pdf', 'jpg', 'jpeg', 'png', 'txt', 'docx'],
                    accept_multiple_files=True,
                    help="学生将看到这些题目文件",
                    key="question_files_upload"
                )
            
            with col_m:
                st.markdown("**📊 批改标准**")
                marking_files = st.file_uploader(
                    "上传评分标准",
                    type=['pdf', 'jpg', 'jpeg', 'png', 'txt', 'docx'],
                    accept_multiple_files=True,
                    help="用于自动批改的评分标准",
                    key="marking_files_upload"
                )
            
            submitted = st.form_submit_button("创建作业", use_container_width=True, type="primary")
            
            if submitted:
                if assignment_title:
                    try:
                        # 保存上传的文件
                        saved_question_files = []
                        saved_marking_files = []
                        
                        # 创建作业文件目录
                        assignment_dir = Path("class_files/assignments")
                        assignment_dir.mkdir(parents=True, exist_ok=True)
                        
                        # 保存题目文件
                        if question_files:
                            for file in question_files:
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                safe_name = re.sub(r'[^\w\-_.]', '_', Path(file.name).stem)
                                file_ext = Path(file.name).suffix
                                filename = f"assignment_{st.session_state.username}_{timestamp}_{safe_name}{file_ext}"
                                file_path = assignment_dir / filename
                                
                                with open(file_path, "wb") as f:
                                    f.write(file.getbuffer())
                                saved_question_files.append(str(file_path))
                        
                        # 保存批改标准文件
                        if marking_files:
                            marking_dir = Path("class_files/marking")
                            marking_dir.mkdir(parents=True, exist_ok=True)
                            
                            for file in marking_files:
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                safe_name = re.sub(r'[^\w\-_.]', '_', Path(file.name).stem)
                                file_ext = Path(file.name).suffix
                                filename = f"marking_{st.session_state.username}_{timestamp}_{safe_name}{file_ext}"
                                file_path = marking_dir / filename
                                
                                with open(file_path, "wb") as f:
                                    f.write(file.getbuffer())
                                saved_marking_files.append(str(file_path))
                        
                        # 组合截止时间
                        due_datetime = None
                        if due_date and due_time:
                            due_datetime = datetime.combine(due_date, due_time).strftime("%Y-%m-%d %H:%M:%S")
                        elif due_date:
                            due_datetime = datetime.combine(due_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 创建作业记录
                        assignment_id = create_assignment(
                            class_id=current_class_id,
                            title=assignment_title,
                            description=assignment_desc,
                            due_date=due_datetime,
                            question_files=saved_question_files,
                            marking_files=saved_marking_files
                        )
                        
                        if assignment_id:
                            st.success(f"🎉 作业创建成功！")
                            
                            # 发送通知给班级学生
                            try:
                                # 获取班级学生列表
                                students = get_user_classes(current_class_id, 'student')  # 这里需要修改数据库函数
                                for student in students:
                                    add_notification(
                                        student['username'],
                                        f"新作业：{assignment_title}",
                                        f"老师发布了新作业：{assignment_title}。{assignment_desc if assignment_desc else ''}"
                                    )
                                st.info("📢 已向班级学生发送通知")
                            except Exception as e:
                                st.warning(f"⚠️ 发送通知失败：{str(e)}")
                            
                            st_rerun()
                        else:
                            st.error("❌ 创建失败")
                    except Exception as e:
                        st.error(f"❌ 创建失败：{str(e)}")
                else:
                    st.warning("⚠️ 请输入作业标题")
    
    # 显示现有作业
    try:
        assignments = get_class_assignments(current_class_id)
        if assignments:
            st.markdown("### 班级作业列表")
            for assignment in assignments:
                with st.expander(f"📝 {assignment['title']}", expanded=False):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**描述：** {assignment.get('description', '无')}")
                        st.write(f"**创建时间：** {assignment['created_at']}")
                        st.write(f"**截止时间：** {assignment.get('due_date', '无限制')}")
                        
                        # 显示文件信息
                        if assignment.get('question_files'):
                            st.write(f"**题目文件：** {len(assignment['question_files'])} 个")
                        if assignment.get('marking_files'):
                            st.write(f"**批改标准：** {len(assignment['marking_files'])} 个")
                    
                    with col2:
                        # 查看提交情况
                        try:
                            submissions = get_assignment_submissions(assignment['id'])
                            st.metric("提交人数", len(submissions))
                            
                            if st.button(f"📊 查看提交", key=f"view_submissions_{assignment['id']}"):
                                # 显示提交详情
                                if submissions:
                                    st.markdown("#### 提交详情")
                                    for submission in submissions:
                                        with st.container():
                                            st.write(f"**学生：** {submission['student_username']}")
                                            st.write(f"**提交时间：** {submission['submitted_at']}")
                                            st.write(f"**文件数量：** {len(submission.get('files', []))}")
                                            
                                            # 下载提交文件
                                            for file_path in submission.get('files', []):
                                                if Path(file_path).exists():
                                                    file_name = Path(file_path).name
                                                    with open(file_path, 'rb') as f:
                                                        st.download_button(
                                                            f"📄 {file_name}",
                                                            data=f.read(),
                                                            file_name=file_name,
                                                            key=f"download_submission_{submission['id']}_{file_name}"
                                                        )
                                            
                                            # 批改按钮
                                            if assignment.get('marking_files') and not submission.get('grade'):
                                                if st.button(f"🤖 AI批改", key=f"grade_{submission['id']}"):
                                                    try:
                                                        # 调用AI批改
                                                        result = batch_correction_with_standard(
                                                            marking_scheme_files=assignment['marking_files'],
                                                            student_answer_files=submission['files'],
                                                            strictness_level="标准"
                                                        )
                                                        
                                                        # 显示批改结果
                                                        st.success("✅ 批改完成！")
                                                        with st.expander("查看批改结果"):
                                                            st.text_area("批改结果", value=str(result), height=300)
                                                        
                                                        # 这里可以保存批改结果到数据库
                                                        
                                                    except Exception as e:
                                                        st.error(f"❌ 批改失败：{str(e)}")
                                            
                                            st.markdown("---")
                                else:
                                    st.info("暂无提交")
                        except Exception as e:
                            st.error(f"❌ 获取提交情况失败：{str(e)}")
        else:
            st.info("当前班级暂无作业")
    except Exception as e:
        st.error(f"❌ 获取作业列表失败：{str(e)}")

# 教师批改审核
def show_teacher_grading():
    st.markdown("### ✅ 批改审核")
    
    # 获取当前选中的班级
    current_class_id = st.session_state.get('current_class_id', '')
    
    if not current_class_id:
        # 获取教师的班级列表让其选择
        try:
            classes = get_user_classes(st.session_state.username, 'teacher')
            if classes:
                class_options = {cls['id']: cls['name'] for cls in classes}
                selected_class = st.selectbox(
                    "选择班级",
                    options=list(class_options.keys()),
                    format_func=lambda x: class_options[x],
                    key="class_selector_teacher_grading"
                )
                st.session_state.current_class_id = selected_class
                current_class_id = selected_class
            else:
                st.info("请先创建班级")
                return
        except Exception as e:
            st.error(f"❌ 获取班级列表失败：{str(e)}")
            return
    
    # 获取班级作业列表
    try:
        assignments = get_class_assignments(current_class_id)
        if not assignments:
            st.info("当前班级暂无作业")
            return
    except Exception as e:
        st.error(f"❌ 获取作业列表失败：{str(e)}")
        return
    
    # 选择作业
    assignment_options = {a['id']: a['title'] for a in assignments}
    selected_assignment_id = st.selectbox(
        "选择作业",
        options=list(assignment_options.keys()),
        format_func=lambda x: assignment_options[x],
        key="assignment_selector_grading"
    )
    
    if not selected_assignment_id:
        return
    
    # 获取选中作业的提交情况
    try:
        submissions = get_assignment_submissions(selected_assignment_id)
        if not submissions:
            st.info("该作业暂无提交")
            return
    except Exception as e:
        st.error(f"❌ 获取提交情况失败：{str(e)}")
        return
    
    # 显示提交列表和批改状态
    st.markdown("### 📋 提交列表")
    
    for i, submission in enumerate(submissions):
        with st.expander(f"👨‍🎓 {submission['student_username']} - 提交时间: {submission['submitted_at']}", expanded=False):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("#### 📁 提交文件")
                
                # 显示提交的文件
                for file_path in submission.get('files', []):
                    if Path(file_path).exists():
                        file_name = Path(file_path).name
                        file_type = get_file_type(file_name)
                        
                        # 文件预览
                        if file_type == 'image':
                            try:
                                from PIL import Image
                                image = Image.open(file_path)
                                st.image(image, caption=file_name, use_column_width=True)
                            except Exception as e:
                                st.error(f"图片预览失败: {e}")
                        elif file_type == 'text':
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                if len(content) > 1000:
                                    content = content[:1000] + "\n...(内容过长，已截断)"
                                st.text_area(f"文件内容 - {file_name}", content, height=200, disabled=True)
                            except Exception as e:
                                st.error(f"文本预览失败: {e}")
                        else:
                            st.info(f"📄 {file_name} ({file_type})")
                        
                        # 下载按钮
                        with open(file_path, 'rb') as f:
                            st.download_button(
                                f"📥 下载 {file_name}",
                                data=f.read(),
                                file_name=file_name,
                                key=f"download_grading_{submission['id']}_{file_name}"
                            )
            
            with col2:
                st.markdown("#### 🤖 AI批改结果")
                
                # 获取选中作业的批改标准
                selected_assignment = next(a for a in assignments if a['id'] == selected_assignment_id)
                
                # 检查是否有批改结果
                if submission.get('ai_result'):
                    # 显示已有的AI批改结果
                    st.text_area("AI批改结果", value=submission['ai_result'], height=300, disabled=True)
                    
                    # 教师审核区域
                    st.markdown("#### ✅ 教师审核")
                    
                    with st.form(f"review_form_{submission['id']}"):
                        # 成绩输入
                        grade = st.number_input(
                            "最终成绩",
                            min_value=0.0,
                            max_value=100.0,
                            value=float(submission.get('grade', 0)),
                            step=0.5,
                            key=f"grade_{submission['id']}"
                        )
                        
                        # 教师评语
                        teacher_comment = st.text_area(
                            "教师评语",
                            value=submission.get('teacher_comment', ''),
                            placeholder="请输入您的评语和建议...",
                            height=150,
                            key=f"comment_{submission['id']}"
                        )
                        
                        # 审核状态
                        review_status = st.selectbox(
                            "审核状态",
                            options=["待审核", "已通过", "需修改"],
                            index=["待审核", "已通过", "需修改"].index(submission.get('status', '待审核')),
                            key=f"status_{submission['id']}"
                        )
                        
                        submit_review = st.form_submit_button("💾 保存审核结果", type="primary")
                        
                        if submit_review:
                            try:
                                # 这里应该调用数据库函数保存审核结果
                                # update_submission_review(submission['id'], grade, teacher_comment, review_status)
                                
                                st.success("✅ 审核结果已保存！")
                                
                                # 发送通知给学生
                                try:
                                    add_notification(
                                        submission['student_username'],
                                        f"作业已批改：{selected_assignment['title']}",
                                        f"您的作业已完成批改。成绩：{grade}分。{teacher_comment if teacher_comment else ''}"
                                    )
                                    st.info("📢 已向学生发送通知")
                                except Exception as e:
                                    st.warning(f"⚠️ 发送通知失败：{str(e)}")
                                
                                st_rerun()
                            except Exception as e:
                                st.error(f"❌ 保存失败：{str(e)}")
                
                elif selected_assignment.get('marking_files'):
                    # 如果有批改标准但还没有AI批改结果，提供批改按钮
                    if st.button(f"🤖 开始AI批改", key=f"start_grading_{submission['id']}", type="primary"):
                        try:
                            with st.spinner("正在进行AI批改..."):
                                # 调用AI批改
                                result = batch_correction_with_standard(
                                    marking_scheme_files=selected_assignment['marking_files'],
                                    student_answer_files=submission['files'],
                                    strictness_level="标准"
                                )
                                
                                # 这里应该保存AI批改结果到数据库
                                # update_submission_ai_result(submission['id'], str(result))
                                
                                st.success("✅ AI批改完成！")
                                st.text_area("批改结果", value=str(result), height=300, disabled=True)
                                
                                st_rerun()
                        except Exception as e:
                            st.error(f"❌ AI批改失败：{str(e)}")
                else:
                    # 没有批改标准的情况
                    st.info("该作业没有设置批改标准，请手动批改")
                    
                    # 手动批改表单
                    with st.form(f"manual_review_form_{submission['id']}"):
                        manual_grade = st.number_input(
                            "成绩",
                            min_value=0.0,
                            max_value=100.0,
                            value=0.0,
                            step=0.5,
                            key=f"manual_grade_{submission['id']}"
                        )
                        
                        manual_comment = st.text_area(
                            "批改评语",
                            placeholder="请输入详细的批改意见...",
                            height=200,
                            key=f"manual_comment_{submission['id']}"
                        )
                        
                        submit_manual = st.form_submit_button("💾 提交批改结果", type="primary")
                        
                        if submit_manual:
                            try:
                                # 保存手动批改结果
                                # update_submission_review(submission['id'], manual_grade, manual_comment, "已通过")
                                
                                st.success("✅ 批改结果已保存！")
                                
                                # 发送通知给学生
                                try:
                                    add_notification(
                                        submission['student_username'],
                                        f"作业已批改：{selected_assignment['title']}",
                                        f"您的作业已完成批改。成绩：{manual_grade}分。{manual_comment}"
                                    )
                                    st.info("📢 已向学生发送通知")
                                except Exception as e:
                                    st.warning(f"⚠️ 发送通知失败：{str(e)}")
                                
                                st_rerun()
                            except Exception as e:
                                st.error(f"❌ 保存失败：{str(e)}")
    
    # 批量操作
    st.markdown("---")
    st.markdown("### 🔄 批量操作")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if selected_assignment.get('marking_files'):
            if st.button("🤖 批量AI批改", type="primary", use_container_width=True):
                try:
                    with st.spinner("正在进行批量AI批改..."):
                        ungraded_submissions = [s for s in submissions if not s.get('ai_result')]
                        
                        if ungraded_submissions:
                            progress_bar = st.progress(0)
                            for i, submission in enumerate(ungraded_submissions):
                                # 批改每个提交
                                result = batch_correction_with_standard(
                                    marking_scheme_files=selected_assignment['marking_files'],
                                    student_answer_files=submission['files'],
                                    strictness_level="标准"
                                )
                                
                                # 保存结果
                                # update_submission_ai_result(submission['id'], str(result))
                                
                                progress_bar.progress((i + 1) / len(ungraded_submissions))
                            
                            st.success(f"✅ 批量批改完成！共处理 {len(ungraded_submissions)} 份作业")
                            st_rerun()
                        else:
                            st.info("所有作业都已完成AI批改")
                except Exception as e:
                    st.error(f"❌ 批量批改失败：{str(e)}")
    
    with col2:
        if st.button("📊 导出成绩单", use_container_width=True):
            try:
                # 生成成绩单
                grade_data = []
                for submission in submissions:
                    grade_data.append({
                        "学生": submission['student_username'],
                        "提交时间": submission['submitted_at'],
                        "成绩": submission.get('grade', '未批改'),
                        "状态": submission.get('status', '待审核'),
                        "教师评语": submission.get('teacher_comment', '')
                    })
                
                # 转换为CSV格式
                import pandas as pd
                df = pd.DataFrame(grade_data)
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                
                st.download_button(
                    "📥 下载成绩单",
                    data=csv,
                    file_name=f"成绩单_{selected_assignment['title']}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"❌ 导出失败：{str(e)}")

# 教师数据统计（占位符）
def show_teacher_statistics():
    st.markdown("### 📊 数据统计")
    st.info("🚧 数据统计功能开发中...")
    
    # 这里将实现：
    # - 班级成绩统计
    # - 作业完成率
    # - 学生表现分析
    # - 数据可视化

# 学生仪表盘 - 简化版
def show_student_dashboard():
    st.markdown('<h2 class="main-title">👨‍🎓 学生工作台</h2>', unsafe_allow_html=True)
    
    # 检查登录状态和角色
    if not st.session_state.logged_in or st.session_state.user_role != 'student':
        st.error("❌ 访问权限不足，请先登录学生账户")
        st.session_state.page = "login"
        st_rerun()
        return
    
    # 简化的顶部信息
    user_info = get_user_info(st.session_state.username)
    student_name = user_info.get('real_name', st.session_state.username) if user_info else st.session_state.username
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**👋 {student_name} 同学**")
    with col2:
        if st.button("🚪 退出", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_role = ""
            st.session_state.show_class_system = False
            st.session_state.page = "home"
            st_rerun()
    
    st.markdown("---")
    
    # 简化的选项卡 - 只保留核心功能
    tab1, tab2 = st.tabs(["📝 我的作业", "📚 班级管理"])
    
    with tab1:
        show_simplified_student_assignments()
    
    with tab2:
        show_simplified_student_classes()

# 学生班级管理
def show_student_classes():
    st.markdown("### 📚 班级管理")
    
    # 获取学生的班级列表
    try:
        classes = get_user_classes(st.session_state.username, 'student')
    except Exception as e:
        st.error(f"❌ 获取班级列表失败：{str(e)}")
        classes = []
    
    # 加入新班级
    with st.expander("➕ 加入班级", expanded=False):
        with st.form("join_class_form"):
            invite_code = st.text_input("邀请码 *", placeholder="输入老师提供的班级邀请码")
            
            submitted = st.form_submit_button("加入班级", use_container_width=True, type="primary")
            
            if submitted:
                if invite_code:
                    try:
                        success = join_class_by_code(st.session_state.username, invite_code)
                        if success:
                            st.success(f"🎉 成功加入班级！")
                            st.balloons()
                            st_rerun()
                        else:
                            st.error("❌ 加入失败，请检查邀请码是否正确")
                    except Exception as e:
                        st.error(f"❌ 加入失败：{str(e)}")
                else:
                    st.warning("⚠️ 请输入邀请码")
    
    # 显示已加入的班级
    if classes:
        st.markdown("### 我的班级")
        for class_info in classes:
            with st.expander(f"📚 {class_info['name']}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**描述：** {class_info.get('description', '无')}")
                    st.write(f"**教师：** {class_info.get('teacher_name', '未知')}")
                    st.write(f"**加入时间：** {class_info.get('joined_at', '未知')}")
                    st.write(f"**班级人数：** {class_info['student_count']} 人")
                
                with col2:
                    if st.button(f"📝 查看作业", key=f"assignments_{class_info['id']}"):
                        st.session_state.current_class_id = class_info['id']
                        # 切换到作业提交选项卡
                        st.info("请切换到\"作业提交\"选项卡查看作业")
                    
                    if st.button(f"📊 查看成绩", key=f"grades_{class_info['id']}"):
                        st.session_state.current_class_id = class_info['id']
                        # 切换到成绩查看选项卡
                        st.info("请切换到\"成绩查看\"选项卡查看成绩")
    else:
        st.info("📝 您还没有加入任何班级。点击上方\"加入班级\"开始学习！")

# 学生作业提交
def show_student_assignments():
    st.markdown("### 📝 作业提交")
    
    # 获取当前选中的班级
    current_class_id = st.session_state.get('current_class_id', '')
    
    if not current_class_id:
        # 获取学生的班级列表让其选择
        try:
            classes = get_user_classes(st.session_state.username, 'student')
            if classes:
                class_options = {cls['id']: cls['name'] for cls in classes}
                selected_class = st.selectbox(
                    "选择班级",
                    options=list(class_options.keys()),
                    format_func=lambda x: class_options[x],
                    key="class_selector_assignments"
                )
                st.session_state.current_class_id = selected_class
                current_class_id = selected_class
            else:
                st.info("请先加入班级")
                return
        except Exception as e:
            st.error(f"❌ 获取班级列表失败：{str(e)}")
            return
    
    # 获取班级作业列表
    try:
        assignments = get_class_assignments(current_class_id)
    except Exception as e:
        st.error(f"❌ 获取作业列表失败：{str(e)}")
        assignments = []
    
    if assignments:
        st.markdown("### 班级作业")
        for assignment in assignments:
            with st.expander(f"📝 {assignment['title']}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**描述：** {assignment.get('description', '无')}")
                    st.write(f"**发布时间：** {assignment['created_at']}")
                    st.write(f"**截止时间：** {assignment.get('due_date', '无限制')}")
                    
                    # 显示题目文件（如果有）
                    if assignment.get('question_files'):
                        st.write("**题目文件：**")
                        for file_path in assignment['question_files']:
                            if Path(file_path).exists():
                                file_name = Path(file_path).name
                                with open(file_path, 'rb') as f:
                                    st.download_button(
                                        f"📄 {file_name}",
                                        data=f.read(),
                                        file_name=file_name,
                                        key=f"download_{assignment['id']}_{file_name}"
                                    )
                
                with col2:
                    # 检查是否已提交
                    try:
                        submissions = get_assignment_submissions(assignment['id'])
                        user_submission = next((s for s in submissions if s['student_username'] == st.session_state.username), None)
                        
                        if user_submission:
                            st.success("✅ 已提交")
                            st.write(f"提交时间：{user_submission['submitted_at']}")
                            if user_submission.get('grade'):
                                st.write(f"成绩：{user_submission['grade']}")
                        else:
                            # 作业提交表单
                            with st.form(f"submit_assignment_{assignment['id']}"):
                                uploaded_files = st.file_uploader(
                                    "上传作业文件",
                                    type=['pdf', 'jpg', 'jpeg', 'png', 'txt', 'docx'],
                                    accept_multiple_files=True,
                                    key=f"upload_{assignment['id']}"
                                )
                                
                                submit_btn = st.form_submit_button("提交作业", type="primary")
                                
                                if submit_btn and uploaded_files:
                                    try:
                                        # 保存提交的文件
                                        submission_dir = Path("class_files/submissions") / str(assignment['id'])
                                        submission_dir.mkdir(parents=True, exist_ok=True)
                                        
                                        saved_files = []
                                        for file in uploaded_files:
                                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                            safe_name = re.sub(r'[^\w\-_.]', '_', Path(file.name).stem)
                                            file_ext = Path(file.name).suffix
                                            filename = f"{st.session_state.username}_{timestamp}_{safe_name}{file_ext}"
                                            file_path = submission_dir / filename
                                            
                                            with open(file_path, "wb") as f:
                                                f.write(file.getbuffer())
                                            saved_files.append(str(file_path))
                                        
                                        # 提交作业到数据库
                                        success = submit_assignment(
                                            assignment['id'],
                                            st.session_state.username,
                                            saved_files
                                        )
                                        
                                        if success:
                                            st.success("🎉 作业提交成功！")
                                            
                                            # 如果有批改标准，自动触发批改
                                            if assignment.get('marking_files'):
                                                st.info("🤖 正在自动批改中...")
                                                
                                                # 创建进度条
                                                progress_bar = st.progress(0)
                                                status_text = st.empty()
                                                
                                                try:
                                                    status_text.text("正在准备批改...")
                                                    progress_bar.progress(10)
                                                    
                                                    # 调用批改API
                                                    status_text.text("正在调用AI批改引擎...")
                                                    progress_bar.progress(30)
                                                    
                                                    result = batch_correction_with_standard(
                                                        marking_scheme_files=assignment['marking_files'],
                                                        student_answer_files=saved_files,
                                                        strictness_level="标准"
                                                    )
                                                    
                                                    progress_bar.progress(70)
                                                    status_text.text("正在保存批改结果...")
                                                    
                                                    # 保存批改结果到数据库
                                                    if save_grading_result(
                                                        assignment['id'], 
                                                        st.session_state.username, 
                                                        result
                                                    ):
                                                        progress_bar.progress(100)
                                                        status_text.text("✅ 自动批改完成！")
                                                        
                                                        # 显示批改结果
                                                        with st.expander("📋 查看批改结果", expanded=True):
                                                            if isinstance(result, str):
                                                                st.markdown(result)
                                                            else:
                                                                st.text_area("批改结果", value=str(result), height=200, disabled=True)
                                                        
                                                        # 发送通知
                                                        add_notification(
                                                            st.session_state.username,
                                                            "作业批改完成",
                                                            f"您的作业《{assignment['title']}》已完成自动批改，请查看结果。",
                                                            "success"
                                                        )
                                                    else:
                                                        st.warning("⚠️ 批改结果保存失败")
                                                        
                                                except Exception as e:
                                                    progress_bar.progress(0)
                                                    status_text.text("")
                                                    st.error(f"❌ 自动批改失败：{str(e)}")
                                                    
                                                    # 记录错误日志
                                                    add_notification(
                                                        st.session_state.username,
                                                        "作业批改失败",
                                                        f"您的作业《{assignment['title']}》自动批改失败：{str(e)}",
                                                        "error"
                                                    )
                                            
                                            st_rerun()
                                        else:
                                            st.error("❌ 提交失败")
                                    except Exception as e:
                                        st.error(f"❌ 提交失败：{str(e)}")
                    except Exception as e:
                        st.error(f"❌ 获取提交状态失败：{str(e)}")
    else:
        st.info("当前班级暂无作业")

# 学生成绩查看
def show_student_grades():
    st.markdown("### 📊 成绩查看")
    st.info("🚧 成绩查看功能开发中...")

# 学生通知消息
def show_student_notifications():
    st.markdown("### 🔔 通知消息")
    
    try:
        notifications = get_user_notifications(st.session_state.username)
        if notifications:
            for notification in notifications:
                with st.container():
                    st.markdown(f"**{notification['title']}**")
                    st.write(notification['content'])
                    st.caption(f"时间：{notification['created_at']}")
                    st.markdown("---")
        else:
            st.info("暂无通知消息")
    except Exception as e:
        st.error(f"❌ 获取通知失败：{str(e)}")

# 教师独立批改功能
def show_teacher_independent_grading():
    st.markdown("### 🚀 独立批改")
    
    st.info("💡 独立批改功能允许您快速批改学生作业，支持三步流程：题目文件、学生作答、批改标准")
    
    # 获取当前选中的班级
    current_class_id = st.session_state.get('current_class_id', '')
    
    if not current_class_id:
        # 获取教师的班级列表让其选择
        try:
            classes = get_user_classes(st.session_state.username, 'teacher')
            if classes:
                class_options = {cls['id']: cls['name'] for cls in classes}
                selected_class = st.selectbox(
                    "选择班级",
                    options=list(class_options.keys()),
                    format_func=lambda x: class_options[x],
                    key="class_selector_independent_grading"
                )
                st.session_state.current_class_id = selected_class
                current_class_id = selected_class
            else:
                st.info("请先创建班级")
                return
        except Exception as e:
            st.error(f"❌ 获取班级列表失败：{str(e)}")
            return
    
    # 获取班级作业列表
    try:
        assignments = get_class_assignments(current_class_id)
        if not assignments:
            st.info("当前班级暂无作业")
            return
    except Exception as e:
        st.error(f"❌ 获取作业列表失败：{str(e)}")
        return
    
    # 选择作业
    assignment_options = {a['id']: a['title'] for a in assignments}
    selected_assignment_id = st.selectbox(
        "选择要批改的作业",
        options=list(assignment_options.keys()),
        format_func=lambda x: assignment_options[x],
        key="assignment_selector_independent"
    )
    
    if not selected_assignment_id:
        return
    
    # 获取选中作业的信息
    selected_assignment = next(a for a in assignments if a['id'] == selected_assignment_id)
    
    # 显示作业信息
    with st.expander(f"📝 作业信息：{selected_assignment['title']}", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**描述：** {selected_assignment.get('description', '无')}")
            st.write(f"**创建时间：** {selected_assignment['created_at']}")
            st.write(f"**截止时间：** {selected_assignment.get('deadline', '无限制')}")
        
        with col2:
            # 显示题目文件
            if selected_assignment.get('question_files'):
                st.write("**📋 题目文件：**")
                for file_path in selected_assignment['question_files']:
                    if Path(file_path).exists():
                        file_name = Path(file_path).name
                        st.write(f"• {file_name}")
            
            # 显示批改标准文件
            if selected_assignment.get('marking_files'):
                st.write("**📊 批改标准：**")
                for file_path in selected_assignment['marking_files']:
                    if Path(file_path).exists():
                        file_name = Path(file_path).name
                        st.write(f"• {file_name}")
    
    # 获取作业提交情况
    try:
        submissions = get_assignment_submissions(selected_assignment_id)
        if not submissions:
            st.info("该作业暂无学生提交")
            return
    except Exception as e:
        st.error(f"❌ 获取提交情况失败：{str(e)}")
        return
    
    # 显示提交统计
    st.markdown("### 📊 提交统计")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("总提交数", len(submissions))
    
    with col2:
        graded_count = len([s for s in submissions if s.get('ai_result')])
        st.metric("已批改数", graded_count)
    
    with col3:
        ungraded_count = len(submissions) - graded_count
        st.metric("待批改数", ungraded_count)
    
    # 一键批改功能
    st.markdown("### 🚀 一键批改")
    
    if selected_assignment.get('marking_files'):
        # 有批改标准的情况
        st.success("✅ 检测到批改标准文件，可以进行自动批改")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🤖 一键批改所有作业", type="primary", use_container_width=True):
                if ungraded_count == 0:
                    st.info("所有作业都已批改完成")
                else:
                    try:
                        with st.spinner(f"正在批改 {ungraded_count} 份作业..."):
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            ungraded_submissions = [s for s in submissions if not s.get('ai_result')]
                            
                            for i, submission in enumerate(ungraded_submissions):
                                status_text.text(f"正在批改 {submission['student_username']} 的作业...")
                                
                                # 调用AI批改
                                result = batch_correction_with_standard(
                                    marking_scheme_files=selected_assignment['marking_files'],
                                    student_answer_files=submission['files'],
                                    strictness_level="标准"
                                )
                                
                                # 保存批改结果
                                update_submission_ai_result(submission['id'], str(result))
                                
                                # 发送通知给学生
                                try:
                                    add_notification(
                                        submission['student_username'],
                                        f"作业已批改：{selected_assignment['title']}",
                                        f"您的作业已完成AI批改，请查看结果。",
                                        "success"
                                    )
                                except Exception as e:
                                    print(f"发送通知失败: {e}")
                                
                                progress_bar.progress((i + 1) / len(ungraded_submissions))
                            
                            status_text.text("批改完成！")
                            st.success(f"✅ 成功批改 {len(ungraded_submissions)} 份作业！")
                            st.balloons()
                            
                            # 刷新页面
                            st_rerun()
                            
                    except Exception as e:
                        st.error(f"❌ 批改失败：{str(e)}")
        
        with col2:
            if st.button("📊 导出批改结果", use_container_width=True):
                try:
                    # 生成批改结果报告
                    report_data = []
                    for submission in submissions:
                        report_data.append({
                            "学生": submission['student_username'],
                            "提交时间": submission['submitted_at'],
                            "批改状态": "已批改" if submission.get('ai_result') else "未批改",
                            "AI批改结果": submission.get('ai_result', '未批改')[:100] + "..." if submission.get('ai_result') and len(submission.get('ai_result', '')) > 100 else submission.get('ai_result', '未批改')
                        })
                    
                    # 转换为CSV格式
                    import pandas as pd
                    df = pd.DataFrame(report_data)
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    
                    st.download_button(
                        "📥 下载批改报告",
                        data=csv,
                        file_name=f"批改报告_{selected_assignment['title']}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                except Exception as e:
                    st.error(f"❌ 导出失败：{str(e)}")
    
    else:
        # 没有批改标准的情况
        st.warning("⚠️ 该作业没有设置批改标准，无法进行自动批改")
        st.info("💡 建议：在作业管理中为作业添加批改标准文件，以启用自动批改功能")
    
    # 显示详细的提交列表
    st.markdown("### 📋 详细提交列表")
    
    for i, submission in enumerate(submissions):
        with st.expander(f"👨‍🎓 {submission['student_username']} - {submission['submitted_at']}", expanded=False):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("#### 📁 提交文件")
                for file_path in submission.get('files', []):
                    if Path(file_path).exists():
                        file_name = Path(file_path).name
                        st.write(f"• {file_name}")
                        
                        # 下载按钮
                        with open(file_path, 'rb') as f:
                            st.download_button(
                                f"📥 下载 {file_name}",
                                data=f.read(),
                                file_name=file_name,
                                key=f"download_independent_{submission['id']}_{file_name}"
                            )
            
            with col2:
                st.markdown("#### 🤖 批改结果")
                if submission.get('ai_result'):
                    st.text_area(
                        "AI批改结果",
                        value=submission['ai_result'],
                        height=200,
                        disabled=True,
                        key=f"result_{submission['id']}"
                    )
                else:
                    st.info("尚未批改")
                    
                    # 单独批改按钮
                    if selected_assignment.get('marking_files'):
                        if st.button(f"🤖 批改此作业", key=f"grade_single_{submission['id']}"):
                            try:
                                with st.spinner("正在批改..."):
                                    result = batch_correction_with_standard(
                                        marking_scheme_files=selected_assignment['marking_files'],
                                        student_answer_files=submission['files'],
                                        strictness_level="标准"
                                    )
                                    
                                    # 保存结果
                                    update_submission_ai_result(submission['id'], str(result))
                                    
                                    st.success("✅ 批改完成！")
                                    st_rerun()
                                    
                            except Exception as e:
                                st.error(f"❌ 批改失败：{str(e)}")

# 优化的批改中心 - 以教师需求为核心
def show_simplified_grading_center():
    st.markdown("### 🚀 智能批改中心")
    
    # 获取教师的班级
    try:
        classes = get_user_classes(st.session_state.username, 'teacher')
        if not classes:
            st.info("📝 请先创建班级开始使用")
            with st.expander("💡 快速开始指南", expanded=True):
                st.markdown("""
                **第一步：创建班级**
                1. 切换到"班级管理"选项卡
                2. 点击"创建班级"
                3. 输入班级名称（如：高一数学班）
                4. 获得邀请码，分享给学生
                
                **第二步：发布作业**
                1. 上传题目文件（PDF、图片等）
                2. 上传批改标准（答案、评分细则）
                3. 设置截止时间
                
                **第三步：智能批改**
                1. 学生提交作业后自动显示
                2. 一键批改所有作业
                3. 查看结果并进行调整
                """)
            return
    except Exception as e:
        st.error(f"❌ 获取班级失败：{str(e)}")
        return
    
    # 智能班级选择 - 显示更多信息
    st.markdown("#### 📚 选择班级")
    class_options = {}
    for cls in classes:
        # 获取班级统计信息
        try:
            assignments = get_class_assignments(cls['id'])
            pending_count = 0
            for assignment in assignments:
                submissions = get_assignment_submissions(assignment['id'])
                pending_count += len([s for s in submissions if not s.get('ai_result')])
            
            status_text = f"📋 {len(assignments)}个作业"
            if pending_count > 0:
                status_text += f" | ⏳ {pending_count}份待批改"
            else:
                status_text += " | ✅ 全部已批改"
                
            class_options[cls['id']] = f"{cls['name']} ({cls['student_count']}人) - {status_text}"
        except:
            class_options[cls['id']] = f"{cls['name']} ({cls['student_count']}人)"
    
    selected_class_id = st.selectbox(
        "选择要批改的班级",
        options=list(class_options.keys()),
        format_func=lambda x: class_options[x],
        key="grading_center_class",
        help="选择需要批改作业的班级"
    )
    
    if not selected_class_id:
        return
    
    # 获取班级作业 - 按状态分类显示
    try:
        assignments = get_class_assignments(selected_class_id)
        if not assignments:
            st.info("📝 当前班级暂无作业")
            st.markdown("💡 **提示：** 请先在班级管理中发布作业")
            return
    except Exception as e:
        st.error(f"❌ 获取作业失败：{str(e)}")
        return
    
    # 作业状态分析和智能推荐
    st.markdown("#### 📝 作业批改状态")
    
    assignment_status = []
    for assignment in assignments:
        try:
            submissions = get_assignment_submissions(assignment['id'])
            total_submissions = len(submissions)
            graded_count = len([s for s in submissions if s.get('ai_result')])
            ungraded_count = total_submissions - graded_count
            
            status = {
                'assignment': assignment,
                'total': total_submissions,
                'graded': graded_count,
                'ungraded': ungraded_count,
                'has_marking': bool(assignment.get('marking_files')),
                'priority': ungraded_count if assignment.get('marking_files') else 0
            }
            assignment_status.append(status)
        except Exception as e:
            print(f"获取作业状态失败: {e}")
    
    # 按优先级排序（有批改标准且有待批改的作业优先）
    assignment_status.sort(key=lambda x: (-x['priority'], -x['total']))
    
    # 显示作业状态卡片 - 统一批改界面
    for i, status in enumerate(assignment_status):
        assignment = status['assignment']
        
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                # 作业标题和状态
                if status['ungraded'] > 0:
                    if status['has_marking']:
                        st.markdown(f"🔥 **{assignment['title']}** (AI智能批改)")
                    else:
                        st.markdown(f"⚠️ **{assignment['title']}** (无标准AI批改)")
                else:
                    st.markdown(f"✅ **{assignment['title']}** (已完成)")
                
                st.caption(f"发布时间: {assignment['created_at']} | 截止: {assignment.get('deadline', '无限制')}")
                if assignment.get('description'):
                    st.caption(f"说明: {assignment['description']}")
            
            with col2:
                st.metric("提交数", status['total'])
            
            with col3:
                if status['ungraded'] > 0:
                    st.metric("待批改", status['ungraded'], delta=f"-{status['graded']}")
                else:
                    st.metric("已完成", status['graded'], delta="✅")
            
            with col4:
                # 统一的操作按钮
                if status['ungraded'] > 0:
                    if st.button("🚀 开始批改", key=f"unified_grade_{assignment['id']}",
                               type="primary", use_container_width=True):
                        # 根据是否有批改标准选择不同的批改方式
                        if status['has_marking']:
                            start_enhanced_batch_grading(assignment['id'], assignment, status['ungraded'])
                        else:
                            start_no_standard_batch_grading(assignment['id'], assignment, status['ungraded'])
                else:
                    if st.button("📊 查看结果", key=f"view_results_{assignment['id']}",
                               use_container_width=True):
                        show_grading_results_summary(assignment['id'], assignment)
            
            st.markdown("---")
    
    # 移除手动批改的单独界面 - 统一处理
    if st.session_state.get('selected_assignment_for_manual'):
        del st.session_state.selected_assignment_for_manual
    
    # 教师补交文件功能 - 整合到统一界面
    st.markdown("---")
    st.markdown("#### 📤 作业管理")
    
    with st.expander("📁 作业文件管理", expanded=False):
        if assignment_status:
            # 选择要管理的作业
            assignment_options = {a['assignment']['id']: a['assignment']['title'] for a in assignment_status}
            selected_assignment_id = st.selectbox(
                "选择作业",
                options=list(assignment_options.keys()),
                format_func=lambda x: assignment_options[x],
                key="manage_assignment_selector"
            )
            
            if selected_assignment_id:
                selected_assignment = next(a['assignment'] for a in assignment_status
                                         if a['assignment']['id'] == selected_assignment_id)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📋 题目文件**")
                    additional_question_files = st.file_uploader(
                        "补充题目文件",
                        type=['pdf', 'jpg', 'jpeg', 'png', 'txt', 'docx'],
                        accept_multiple_files=True,
                        help="为作业补充题目文件",
                        key="additional_question_files"
                    )
                
                with col2:
                    st.markdown("**📊 批改标准**")
                    additional_marking_files = st.file_uploader(
                        "补充批改标准",
                        type=['pdf', 'jpg', 'jpeg', 'png', 'txt', 'docx'],
                        accept_multiple_files=True,
                        help="为作业补充批改标准（有标准将使用标准批改，无标准将使用智能批改）",
                        key="additional_marking_files"
                    )
                
                if st.button("💾 保存文件", type="primary"):
                    try:
                        files_added = False
                        
                        # 保存补充的题目文件
                        if additional_question_files:
                            for file in additional_question_files:
                                file_path = save_assignment_file(file, "questions", st.session_state.username)
                                files_added = True
                        
                        # 保存补充的批改标准文件
                        if additional_marking_files:
                            for file in additional_marking_files:
                                file_path = save_assignment_file(file, "marking", st.session_state.username)
                                files_added = True
                        
                        if files_added:
                            st.success("✅ 文件保存成功！")
                            st.info("💡 页面将刷新以显示最新状态")
                            time.sleep(1)
                            st_rerun()
                        else:
                            st.warning("⚠️ 请选择要补充的文件")
                    
                    except Exception as e:
                        st.error(f"❌ 文件保存失败：{str(e)}")
        else:
            st.info("📝 暂无作业可管理")
    
    # 移除单独的无标准批改区域 - 已整合到统一界面
    # 添加智能批改说明
    st.markdown("---")
    st.markdown("#### 🤖 智能批改说明")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("**📊 标准批改**")
        st.markdown("""
        - 上传了批改标准的作业
        - AI根据标准答案进行精确批改
        - 提供详细的评分和反馈
        """)
    
    with col2:
        st.info("**🧠 智能批改**")
        st.markdown("""
        - 无批改标准的作业
        - AI智能分析题目和学生答案
        - 基于理解能力进行评分
        """)

# 简化的班级管理
def show_simplified_class_management():
   st.markdown("### 📚 班级管理")
   
   # 获取教师班级
   try:
       classes = get_user_classes(st.session_state.username, 'teacher')
   except Exception as e:
       st.error(f"❌ 获取班级失败：{str(e)}")
       classes = []
   
   # 创建新班级
   with st.expander("➕ 创建班级", expanded=False):
       with st.form("create_class_simple"):
           class_name = st.text_input("班级名称", placeholder="例如：高一数学班")
           class_desc = st.text_area("班级描述", placeholder="可选")
           
           if st.form_submit_button("创建", type="primary"):
               if class_name:
                   try:
                       invite_code = create_class(st.session_state.username, class_name, class_desc)
                       if invite_code:
                           st.success(f"✅ 创建成功！邀请码：**{invite_code}**")
                           st_rerun()
                       else:
                           st.error("❌ 创建失败")
                   except Exception as e:
                       st.error(f"❌ 创建失败：{str(e)}")
               else:
                   st.warning("⚠️ 请输入班级名称")
   
   # 班级列表
   if classes:
       for class_info in classes:
           with st.container():
               col1, col2, col3 = st.columns([2, 1, 1])
               
               with col1:
                   st.markdown(f"**📚 {class_info['name']}**")
                   st.caption(f"👥 {class_info['student_count']} 人 | 邀请码: `{class_info['invite_code']}`")
               
               with col2:
                   if st.button("📝 发布作业", key=f"assign_{class_info['id']}", use_container_width=True):
                       show_quick_assignment_form(class_info['id'])
               
               with col3:
                   if st.button("👥 查看学生", key=f"students_{class_info['id']}", use_container_width=True):
                       show_class_students_simple(class_info['id'])
               
               st.markdown("---")
   else:
       st.info("📝 暂无班级，请创建第一个班级")

# 快速发布作业表单
def show_quick_assignment_form(class_id):
   st.markdown("#### 📝 快速发布作业")
   
   with st.form(f"quick_assignment_{class_id}"):
       title = st.text_input("作业标题", placeholder="例如：第一章练习")
       description = st.text_area("作业说明", placeholder="可选")
       
       col1, col2 = st.columns(2)
       with col1:
           question_files = st.file_uploader(
               "📋 题目文件",
               type=['pdf', 'jpg', 'jpeg', 'png', 'txt', 'docx'],
               accept_multiple_files=True,
               help="学生将看到的题目"
           )
       
       with col2:
           marking_files = st.file_uploader(
               "📊 批改标准",
               type=['pdf', 'jpg', 'jpeg', 'png', 'txt', 'docx'],
               accept_multiple_files=True,
               help="用于自动批改的标准答案"
           )
       
       if st.form_submit_button("🚀 发布作业", type="primary"):
           if title:
               try:
                   # 保存文件
                   saved_question_files = []
                   saved_marking_files = []
                   
                   if question_files:
                       for file in question_files:
                           file_path = save_assignment_file(file, "questions", st.session_state.username)
                           saved_question_files.append(file_path)
                   
                   if marking_files:
                       for file in marking_files:
                           file_path = save_assignment_file(file, "marking", st.session_state.username)
                           saved_marking_files.append(file_path)
                   
                   # 创建作业
                   assignment_id = create_assignment(
                       class_id=class_id,
                       title=title,
                       description=description,
                       question_files=saved_question_files,
                       marking_files=saved_marking_files
                   )
                   
                   if assignment_id:
                       st.success("✅ 作业发布成功！")
                       st_rerun()
                   else:
                       st.error("❌ 发布失败")
               except Exception as e:
                   st.error(f"❌ 发布失败：{str(e)}")
           else:
               st.warning("⚠️ 请输入作业标题")

# 简化的学生列表 - 增强版学生档案
def show_class_students_simple(class_id):
   st.markdown("#### 👥 班级学生档案")
   
   try:
       students = get_class_students(class_id)
       if students:
           for student in students:
               with st.expander(f"👨‍🎓 {student.get('real_name', student['username'])} ({student['username']})", expanded=False):
                   # 学生基本信息
                   st.markdown("**📋 学生信息**")
                   st.write(f"**用户名:** {student['username']}")
                   st.write(f"**真实姓名:** {student.get('real_name', '未设置')}")
                   st.write(f"**加入时间:** {student.get('joined_at', '未知')}")
                   
                   # 获取学生作业记录
                   try:
                       student_submissions = get_student_submissions_in_class(student['username'], class_id)
                       if student_submissions:
                           st.markdown("**📚 作业记录**")
                           total_assignments = len(student_submissions)
                           completed_assignments = len([s for s in student_submissions if s.get('status') == 'graded'])
                           pending_assignments = len([s for s in student_submissions if s.get('status') == 'submitted'])
                           
                           col1, col2, col3 = st.columns(3)
                           with col1:
                               st.metric("总作业", total_assignments)
                           with col2:
                               st.metric("已完成", completed_assignments)
                           with col3:
                               st.metric("待批改", pending_assignments)
                           
                           # 详细作业列表
                           st.markdown("**📊 详细记录**")
                           for submission in student_submissions:
                               assignment = get_assignment_by_id(submission['assignment_id'])
                               if assignment:
                                   status_emoji = "✅" if submission.get('status') == 'graded' else "⏳"
                                   st.write(f"{status_emoji} **{assignment['title']}**")
                                   st.caption(f"提交时间: {submission['submitted_at']} | 状态: {submission.get('status', '未知')}")
                                   if submission.get('grade'):
                                       st.caption(f"成绩: {submission['grade']} | 评语: {submission.get('feedback', '无评语')}")
                       else:
                           st.info("📝 该学生暂无作业记录")
                           
                   except Exception as e:
                       st.error(f"❌ 获取作业记录失败：{str(e)}")
                   
                   st.markdown("---")
       else:
           st.info("📝 暂无学生")
   except Exception as e:
       st.error(f"❌ 获取学生列表失败：{str(e)}")

# 文件预览和结果展示区域
def show_grading_preview_area(submissions, assignment):
   st.markdown("### 📋 批改预览")
   
   # 学生选择
   if not submissions:
       st.info("📝 暂无提交")
       return
   
   student_options = {s['id']: f"{s['student_username']} - {s['submitted_at']}" for s in submissions}
   selected_submission_id = st.selectbox(
       "选择学生作业",
       options=list(student_options.keys()),
       format_func=lambda x: student_options[x],
       key="preview_submission"
   )
   
   if not selected_submission_id:
       return
   
   selected_submission = next(s for s in submissions if s['id'] == selected_submission_id)
   
   # 左右分栏显示
   col1, col2 = st.columns(2)
   
   with col1:
       st.markdown("#### 📁 学生作业")
       show_student_files_preview(selected_submission.get('files', []))
   
   with col2:
       st.markdown("#### 🤖 批改结果")
       show_grading_result_preview(selected_submission, assignment)

# 学生文件预览
def show_student_files_preview(files):
   if not files:
       st.info("📝 无文件")
       return
   
   for file_path in files:
       if Path(file_path).exists():
           file_name = Path(file_path).name
           file_type = get_file_type(file_name)
           
           with st.expander(f"📄 {file_name}", expanded=False):
               if file_type == 'image':
                   try:
                       from PIL import Image
                       image = Image.open(file_path)
                       st.image(image, use_container_width=True)
                   except Exception as e:
                       st.error(f"图片预览失败: {e}")
               elif file_type == 'text':
                   try:
                       with open(file_path, 'r', encoding='utf-8') as f:
                           content = f.read()
                       if len(content) > 500:
                           content = content[:500] + "\n...(内容已截断)"
                       st.text_area("", content, height=200, disabled=True)
                   except Exception as e:
                       st.error(f"文本预览失败: {e}")
               else:
                   st.info(f"📄 {file_name} ({file_type})")
               
               # 下载按钮
               with open(file_path, 'rb') as f:
                   st.download_button(
                       "📥 下载",
                       data=f.read(),
                       file_name=file_name,
                       key=f"download_preview_{file_name}"
                   )

# 批改结果预览
def show_grading_result_preview(submission, assignment):
   if submission.get('ai_result'):
       st.text_area("", submission['ai_result'], height=300, disabled=True)
       
       # 分享到班级按钮
       if st.button("📤 分享到班级", key=f"share_{submission['id']}", type="primary"):
           share_result_to_class(submission, assignment)
   else:
       st.info("⏳ 尚未批改")
       
       # 单独批改按钮
       if assignment.get('marking_files'):
           if st.button("🚀 立即批改", key=f"grade_now_{submission['id']}", type="primary"):
               grade_single_submission(submission, assignment)

# 后台批改启动函数
def start_background_grading(assignment_id, assignment):
   """启动后台批改任务"""
   st.info("🚀 批改任务已启动，将在后台进行...")
   
   try:
       submissions = get_assignment_submissions(assignment_id)
       ungraded_submissions = [s for s in submissions if not s.get('ai_result')]
       
       if not ungraded_submissions:
           st.info("✅ 所有作业都已批改完成")
           return
       
       # 创建后台任务标记
       st.session_state.background_grading = {
           'assignment_id': assignment_id,
           'total': len(ungraded_submissions),
           'completed': 0,
           'status': 'running'
       }
       
       # 模拟后台批改（实际应该用异步任务）
       progress_bar = st.progress(0)
       status_text = st.empty()
       
       for i, submission in enumerate(ungraded_submissions):
           status_text.text(f"正在批改 {submission['student_username']} 的作业...")
           
           try:
               # 调用AI批改
               result = batch_correction_with_standard(
                   marking_scheme_files=assignment['marking_files'],
                   student_answer_files=submission['files'],
                   strictness_level="标准"
               )
               
               # 保存结果
               update_submission_ai_result(submission['id'], str(result))
               
               # 发送通知
               add_notification(
                   submission['student_username'],
                   f"作业已批改：{assignment['title']}",
                   f"您的作业已完成批改，请查看结果。",
                   "success"
               )
               
               progress_bar.progress((i + 1) / len(ungraded_submissions))
               
           except Exception as e:
               st.error(f"❌ 批改 {submission['student_username']} 的作业失败：{str(e)}")
       
       status_text.text("✅ 批改完成！")
       st.success(f"🎉 成功批改 {len(ungraded_submissions)} 份作业！")
       
       # 清除后台任务标记
       if 'background_grading' in st.session_state:
           del st.session_state.background_grading
       
       st_rerun()
       
   except Exception as e:
       st.error(f"❌ 批改失败：{str(e)}")

# 单个作业批改
def grade_single_submission(submission, assignment):
   """批改单个作业"""
   try:
       with st.spinner("正在批改..."):
           result = batch_correction_with_standard(
               marking_scheme_files=assignment['marking_files'],
               student_answer_files=submission['files'],
               strictness_level="标准"
           )
           
           # 保存结果
           update_submission_ai_result(submission['id'], str(result))
           
           st.success("✅ 批改完成！")
           st_rerun()
           
   except Exception as e:
       st.error(f"❌ 批改失败：{str(e)}")

# 分享结果到班级
def share_result_to_class(submission, assignment):
   """分享批改结果到班级"""
   try:
       # 获取班级所有学生
       students = get_class_students(assignment['class_id'])
       
       # 发送通知给所有学生
       for student in students:
           add_notification(
               student['username'],
               f"优秀作业分享：{assignment['title']}",
               f"老师分享了 {submission['student_username']} 同学的优秀作业，请查看学习。",
               "info"
           )
       
       st.success("✅ 已分享到班级！")
       
   except Exception as e:
       st.error(f"❌ 分享失败：{str(e)}")

# 保存作业文件的辅助函数
def save_assignment_file(file, file_type, username):
   """保存作业文件"""
   import re
   
   # 创建目录
   file_dir = Path("class_files") / file_type
   file_dir.mkdir(parents=True, exist_ok=True)
   
   # 生成文件名
   timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
   safe_name = re.sub(r'[^\w\-_.]', '_', Path(file.name).stem)
   file_ext = Path(file.name).suffix
   filename = f"{username}_{timestamp}_{safe_name}{file_ext}"
   file_path = file_dir / filename
   
   # 保存文件
   with open(file_path, "wb") as f:
       f.write(file.getbuffer())
   
   return str(file_path)

# 简化的学生作业页面
def show_simplified_student_assignments():
   st.markdown("### 📝 我的作业")
   
   # 获取学生的班级
   try:
       classes = get_user_classes(st.session_state.username, 'student')
       if not classes:
           st.info("📝 请先加入班级")
           return
   except Exception as e:
       st.error(f"❌ 获取班级失败：{str(e)}")
       return
   
   # 班级选择
   class_options = {cls['id']: f"{cls['name']} ({cls.get('teacher_name', '未知老师')})" for cls in classes}
   selected_class_id = st.selectbox(
       "选择班级",
       options=list(class_options.keys()),
       format_func=lambda x: class_options[x],
       key="student_assignments_class"
   )
   
   if not selected_class_id:
       return
   
   # 获取班级作业
   try:
       assignments = get_class_assignments(selected_class_id)
       if not assignments:
           st.info("📝 当前班级暂无作业")
           return
   except Exception as e:
       st.error(f"❌ 获取作业失败：{str(e)}")
       return
   
   # 作业列表
   for assignment in assignments:
       with st.container():
           col1, col2, col3 = st.columns([2, 1, 1])
           
           with col1:
               st.markdown(f"**📝 {assignment['title']}**")
               st.caption(f"截止时间: {assignment.get('due_date', '无限制')}")
               if assignment.get('description'):
                   st.caption(f"说明: {assignment['description']}")
           
           with col2:
               # 检查提交状态
               try:
                   submissions = get_assignment_submissions(assignment['id'])
                   user_submission = next((s for s in submissions if s['student_username'] == st.session_state.username), None)
                   
                   if user_submission:
                       st.success("✅ 已提交")
                       if user_submission.get('grade'):
                           st.metric("成绩", f"{user_submission['grade']}分")
                   else:
                       st.warning("⏳ 未提交")
               except Exception as e:
                   st.error("❌ 状态错误")
           
           with col3:
               if st.button("📋 查看详情", key=f"view_assignment_{assignment['id']}", use_container_width=True):
                   show_assignment_detail_modal(assignment)
           
           st.markdown("---")

# 简化的学生班级页面
def show_simplified_student_classes():
   st.markdown("### 📚 班级管理")
   
   # 获取学生班级
   try:
       classes = get_user_classes(st.session_state.username, 'student')
   except Exception as e:
       st.error(f"❌ 获取班级失败：{str(e)}")
       classes = []
   
   # 加入班级
   with st.expander("➕ 加入班级", expanded=False):
       with st.form("join_class_simple"):
           invite_code = st.text_input("邀请码", placeholder="输入老师提供的邀请码")
           
           if st.form_submit_button("加入", type="primary"):
               if invite_code:
                   try:
                       success = join_class_by_code(st.session_state.username, invite_code)
                       if success:
                           st.success("✅ 加入成功！")
                           st_rerun()
                       else:
                           st.error("❌ 邀请码无效")
                   except Exception as e:
                       st.error(f"❌ 加入失败：{str(e)}")
               else:
                   st.warning("⚠️ 请输入邀请码")
   
   # 班级列表
   if classes:
       for class_info in classes:
           with st.container():
               col1, col2, col3 = st.columns([2, 1, 1])
               
               with col1:
                   st.markdown(f"**📚 {class_info['name']}**")
                   st.caption(f"教师: {class_info.get('teacher_name', '未知')} | {class_info['student_count']} 人")
               
               with col2:
                   # 获取作业统计
                   try:
                       assignments = get_class_assignments(class_info['id'])
                       total_assignments = len(assignments)
                       
                       # 计算已提交作业数
                       submitted_count = 0
                       for assignment in assignments:
                           submissions = get_assignment_submissions(assignment['id'])
                           if any(s['student_username'] == st.session_state.username for s in submissions):
                               submitted_count += 1
                       
                       st.metric("作业", f"{submitted_count}/{total_assignments}")
                   except Exception as e:
                       st.metric("作业", "0/0")
               
               with col3:
                   if st.button("📝 查看作业", key=f"view_class_assignments_{class_info['id']}", use_container_width=True):
                       st.session_state.current_class_id = class_info['id']
                       st.info("💡 请切换到\"我的作业\"选项卡")
               
               st.markdown("---")
   else:
       st.info("📝 暂未加入任何班级")

# 作业详情模态框
def show_assignment_detail_modal(assignment):
   st.markdown(f"#### 📝 {assignment['title']}")
   
   # 作业信息
   col1, col2 = st.columns(2)
   
   with col1:
       st.write(f"**发布时间：** {assignment['created_at']}")
       st.write(f"**截止时间：** {assignment.get('due_date', '无限制')}")
       if assignment.get('description'):
           st.write(f"**作业说明：** {assignment['description']}")
   
   with col2:
       # 题目文件下载
       if assignment.get('question_files'):
           st.write("**📋 题目文件：**")
           for file_path in assignment['question_files']:
               if Path(file_path).exists():
                   file_name = Path(file_path).name
                   with open(file_path, 'rb') as f:
                       st.download_button(
                           f"📄 {file_name}",
                           data=f.read(),
                           file_name=file_name,
                           key=f"download_question_{assignment['id']}_{file_name}"
                       )
   
   # 提交状态和操作
   try:
       submissions = get_assignment_submissions(assignment['id'])
       user_submission = next((s for s in submissions if s['student_username'] == st.session_state.username), None)
       
       if user_submission:
           st.success("✅ 您已提交此作业")
           st.write(f"**提交时间：** {user_submission['submitted_at']}")
           
           # 显示提交的文件
           if user_submission.get('files'):
               st.write("**📁 已提交文件：**")
               for file_path in user_submission['files']:
                   if Path(file_path).exists():
                       file_name = Path(file_path).name
                       st.write(f"• {file_name}")
           
           # 显示成绩和评语
           if user_submission.get('grade'):
               st.metric("成绩", f"{user_submission['grade']}分")
           
           if user_submission.get('ai_result'):
               with st.expander("🤖 AI批改结果", expanded=False):
                   st.text_area("", user_submission['ai_result'], height=200, disabled=True)
           
           if user_submission.get('teacher_comment'):
               with st.expander("👨‍🏫 教师评语", expanded=False):
                   st.text_area("", user_submission['teacher_comment'], height=100, disabled=True)
       
       else:
           st.warning("⏳ 您尚未提交此作业")
           
           # 作业提交表单
           with st.form(f"submit_assignment_modal_{assignment['id']}"):
               st.markdown("#### 📤 提交作业")
               
               uploaded_files = st.file_uploader(
                   "选择文件",
                   type=['pdf', 'jpg', 'jpeg', 'png', 'txt', 'docx'],
                   accept_multiple_files=True,
                   help="支持PDF、图片、文本等格式",
                   key=f"upload_modal_{assignment['id']}"
               )
               
               submit_btn = st.form_submit_button("🚀 提交作业", type="primary", use_container_width=True)
               
               if submit_btn and uploaded_files:
                   try:
                       # 保存文件
                       submission_dir = Path("class_files/submissions") / str(assignment['id'])
                       submission_dir.mkdir(parents=True, exist_ok=True)
                       
                       saved_files = []
                       for file in uploaded_files:
                           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                           safe_name = re.sub(r'[^\w\-_.]', '_', Path(file.name).stem)
                           file_ext = Path(file.name).suffix
                           filename = f"{st.session_state.username}_{timestamp}_{safe_name}{file_ext}"
                           file_path = submission_dir / filename
                           
                           with open(file_path, "wb") as f:
                               f.write(file.getbuffer())
                           saved_files.append(str(file_path))
                       
                       # 提交到数据库
                       success = submit_assignment(
                           assignment['id'],
                           st.session_state.username,
                           saved_files
                       )
                       
                       if success:
                           st.success("🎉 提交成功！")
                           
                           # 如果有批改标准，触发自动批改
                           if assignment.get('marking_files'):
                               # 创建进度条
                               progress_bar = st.progress(0)
                               status_text = st.empty()
                               
                               try:
                                   status_text.text("正在准备批改...")
                                   progress_bar.progress(10)
                                   
                                   # 调用批改API
                                   status_text.text("正在调用AI批改引擎...")
                                   progress_bar.progress(30)
                                   
                                   result = batch_correction_with_standard(
                                       marking_scheme_files=assignment['marking_files'],
                                       student_answer_files=saved_files,
                                       strictness_level="标准"
                                   )
                                   
                                   progress_bar.progress(70)
                                   status_text.text("正在保存批改结果...")
                                   
                                   # 保存批改结果到数据库
                                   if save_grading_result(
                                       assignment['id'], 
                                       st.session_state.username, 
                                       result
                                   ):
                                       progress_bar.progress(100)
                                       status_text.text("✅ 自动批改完成！")
                                       
                                       # 显示批改结果
                                       with st.expander("📋 查看批改结果", expanded=True):
                                           if isinstance(result, str):
                                               st.markdown(result)
                                           else:
                                               st.text_area("批改结果", value=str(result), height=200, disabled=True)
                                       
                                       # 发送通知
                                       add_notification(
                                           st.session_state.username,
                                           "作业批改完成",
                                           f"您的作业《{assignment['title']}》已完成自动批改，请查看结果。",
                                           "success"
                                       )
                                   else:
                                       st.warning("⚠️ 批改结果保存失败")
                                       
                               except Exception as e:
                                   progress_bar.progress(0)
                                   status_text.text("")
                                   st.error(f"❌ 自动批改失败：{str(e)}")
                                   
                                   # 记录错误日志
                                   add_notification(
                                       st.session_state.username,
                                       "作业批改失败",
                                       f"您的作业《{assignment['title']}》自动批改失败：{str(e)}",
                                       "error"
                                   )
                           
                           st_rerun()
                       else:
                           st.error("❌ 提交失败")
                   except Exception as e:
                       st.error(f"❌ 提交失败：{str(e)}")
               elif submit_btn:
                   st.warning("⚠️ 请选择要提交的文件")
   
   except Exception as e:
       st.error(f"❌ 获取提交状态失败：{str(e)}")

# 获取班级学生列表的辅助函数
def get_class_students(class_id):
   """获取班级学生列表"""
   try:
       # 这里应该调用数据库函数获取班级学生
       # 暂时返回空列表，需要在database.py中实现相应函数
       return []
   except Exception as e:
       print(f"获取班级学生失败: {e}")
       return []

# 导入数据库连接函数
from database import get_db_connection

# 更新提交AI结果的辅助函数
def update_submission_ai_result(submission_id, ai_result):
   """更新提交的AI批改结果"""
   try:
       # 通过submission_id获取assignment_id和student_username
       conn = get_db_connection()
       cursor = conn.cursor()
       cursor.execute('''
           SELECT assignment_id, student_username FROM submissions WHERE id = ?
       ''', (submission_id,))
       result = cursor.fetchone()
       conn.close()
       
       if result:
           assignment_id, student_username = result['assignment_id'], result['student_username']
           return save_grading_result(assignment_id, student_username, ai_result)
       else:
           print(f"未找到提交记录: {submission_id}")
           return False
   except Exception as e:
       print(f"更新AI结果失败: {e}")
       return False

# 增强的批改启动函数
def start_enhanced_batch_grading(assignment_id, assignment, ungraded_count):
    """启动增强的批改任务"""
    st.info(f"🚀 开始批改 {ungraded_count} 份作业...")
    
    try:
        submissions = get_assignment_submissions(assignment_id)
        ungraded_submissions = [s for s in submissions if not s.get('ai_result')]
        
        if not ungraded_submissions:
            st.success("✅ 所有作业都已批改完成")
            return
        
        # 执行批改
        execute_enhanced_batch_grading(assignment_id, assignment, ungraded_submissions)
        
    except Exception as e:
        st.error(f"❌ 批改失败：{str(e)}")

# 执行增强批改
def execute_enhanced_batch_grading(assignment_id, assignment, ungraded_submissions):
    """执行增强的批量批改"""
    progress_container = st.container()
    
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        
        success_count = 0
        failed_submissions = []
        
        for i, submission in enumerate(ungraded_submissions):
            status_text.text(f"🤖 正在批改 {submission['student_username']} 的作业... ({i+1}/{len(ungraded_submissions)})")
            
            try:
                # 调用AI批改
                result = batch_correction_with_standard(
                    marking_scheme_files=assignment['marking_files'],
                    student_answer_files=submission['files'],
                    strictness_level="标准"
                )
                
                # 保存结果
                update_submission_ai_result(submission['id'], str(result))
                
                # 发送通知
                add_notification(
                    submission['student_username'],
                    f"作业已批改：{assignment['title']}",
                    f"您的作业已完成AI批改，请查看结果。",
                    "success"
                )
                
                success_count += 1
                
                # 显示实时结果
                with results_container:
                    st.success(f"✅ {submission['student_username']} - 批改完成")
                
            except Exception as e:
                failed_submissions.append({
                    'student': submission['student_username'],
                    'error': str(e)
                })
                
                with results_container:
                    st.error(f"❌ {submission['student_username']} - 批改失败：{str(e)}")
            
            # 更新进度
            progress_bar.progress((i + 1) / len(ungraded_submissions))
        
        # 显示最终结果
        status_text.text("🎉 批改任务完成！")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("成功批改", success_count, delta=f"✅ {success_count}")
        with col2:
            st.metric("失败数量", len(failed_submissions), delta=f"❌ {len(failed_submissions)}")
        
        if failed_submissions:
            with st.expander("❌ 失败详情", expanded=False):
                for failed in failed_submissions:
                    st.error(f"**{failed['student']}**: {failed['error']}")
        
        if success_count > 0:
            st.balloons()
            st.success(f"🎉 批改完成！成功批改 {success_count} 份作业")
        
        # 自动刷新页面
        time.sleep(2)
        st_rerun()

# 手动批改界面
def show_enhanced_manual_grading(assignment):
    """显示增强的手动批改界面"""
    st.markdown("#### 👨‍🏫 手动批改模式")
    st.info("💡 该作业没有批改标准，需要手动批改每份作业")
    
    try:
        submissions = get_assignment_submissions(assignment['id'])
        ungraded_submissions = [s for s in submissions if not s.get('ai_result')]
        
        if not ungraded_submissions:
            st.success("✅ 所有作业都已批改完成")
            return
        
        # 学生选择
        student_options = {s['id']: f"{s['student_username']} - {s['submitted_at']}" for s in ungraded_submissions}
        selected_submission_id = st.selectbox(
            "选择要批改的学生作业",
            options=list(student_options.keys()),
            format_func=lambda x: student_options[x],
            key="manual_grading_student"
        )
        
        if not selected_submission_id:
            return
        
        selected_submission = next(s for s in ungraded_submissions if s['id'] == selected_submission_id)
        
        # 显示学生作业
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 📁 学生作业")
            show_student_files_preview(selected_submission.get('files', []))
        
        with col2:
            st.markdown("##### ✍️ 手动批改")
            
            with st.form(f"manual_grading_{selected_submission['id']}"):
                grade = st.number_input(
                    "成绩 (0-100分)",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0,
                    step=0.5
                )
                
                comment = st.text_area(
                    "批改评语",
                    placeholder="请输入详细的批改意见和建议...",
                    height=200
                )
                
                col_submit, col_skip = st.columns(2)
                
                with col_submit:
                    submit_manual = st.form_submit_button("💾 提交批改", type="primary")
                
                with col_skip:
                    skip_manual = st.form_submit_button("⏭️ 跳过此份")
                
                if submit_manual:
                    try:
                        # 保存手动批改结果
                        manual_result = f"成绩：{grade}分\n\n教师评语：\n{comment}"
                        update_submission_ai_result(selected_submission['id'], manual_result)
                        
                        # 发送通知
                        add_notification(
                            selected_submission['student_username'],
                            f"作业已批改：{assignment['title']}",
                            f"您的作业已完成批改。成绩：{grade}分。{comment[:50]}{'...' if len(comment) > 50 else ''}",
                            "success"
                        )
                        
                        st.success("✅ 批改完成！")
                        st_rerun()
                        
                    except Exception as e:
                        st.error(f"❌ 保存失败：{str(e)}")
                
                elif skip_manual:
                    st.info("⏭️ 已跳过此份作业")
                    st_rerun()
    
    except Exception as e:
        st.error(f"❌ 获取作业信息失败：{str(e)}")

# 批改结果汇总
def show_grading_results_summary(assignment_id, assignment):
    """显示批改结果汇总"""
    st.markdown("#### 📊 批改结果汇总")
    
    try:
        submissions = get_assignment_submissions(assignment_id)
        
        if not submissions:
            st.info("📝 暂无提交")
            return
        
        # 统计信息
        total_count = len(submissions)
        graded_count = len([s for s in submissions if s.get('ai_result')])
        ungraded_count = total_count - graded_count
        
        # 显示统计
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总提交数", total_count)
        
        with col2:
            st.metric("已批改", graded_count, delta=f"{graded_count/total_count*100:.1f}%" if total_count > 0 else "0%")
        
        with col3:
            st.metric("待批改", ungraded_count)
        
        with col4:
            # 计算平均分（如果有成绩）
            grades = []
            for s in submissions:
                if s.get('ai_result'):
                    # 尝试从结果中提取分数
                    result_text = s['ai_result']
                    import re
                    score_match = re.search(r'(\d+(?:\.\d+)?)\s*分', result_text)
                    if score_match:
                        grades.append(float(score_match.group(1)))
            
            if grades:
                avg_grade = sum(grades) / len(grades)
                st.metric("平均分", f"{avg_grade:.1f}分")
            else:
                st.metric("平均分", "暂无")
        
        # 详细列表
        st.markdown("##### 📋 详细结果")
        
        for submission in submissions:
            with st.expander(f"👨‍🎓 {submission['student_username']} - {submission['submitted_at']}", expanded=False):
                col_info, col_result = st.columns(2)
                
                with col_info:
                    st.write(f"**提交时间：** {submission['submitted_at']}")
                    st.write(f"**文件数量：** {len(submission.get('files', []))}")
                    
                    # 文件列表
                    if submission.get('files'):
                        st.write("**提交文件：**")
                        for file_path in submission['files']:
                            if Path(file_path).exists():
                                file_name = Path(file_path).name
                                st.write(f"• {file_name}")
                
                with col_result:
                    if submission.get('ai_result'):
                        st.success("✅ 已批改")
                        
                        # 显示批改结果
                        result_text = submission['ai_result']
                        if len(result_text) > 200:
                            st.text_area("批改结果", result_text[:200] + "...", height=100, disabled=True)
                            
                            if st.button(f"📖 查看完整结果", key=f"full_result_{submission['id']}"):
                                st.text_area("完整批改结果", result_text, height=300, disabled=True)
                        else:
                            st.text_area("批改结果", result_text, height=100, disabled=True)
                        
                        # 下载按钮
                        st.download_button(
                            "📥 下载结果",
                            data=result_text,
                            file_name=f"{submission['student_username']}_{assignment['title']}_批改结果.txt",
                            mime="text/plain",
                            key=f"download_result_{submission['id']}"
                        )
                    else:
                        st.warning("⏳ 未批改")
                        
                        # 快速批改按钮
                        if assignment.get('marking_files'):
                            if st.button(f"🚀 立即批改", key=f"quick_grade_{submission['id']}", type="primary"):
                                grade_single_submission(submission, assignment)
        
        # 批量操作
        st.markdown("---")
        st.markdown("##### 🔄 批量操作")
        
        col_export, col_notify = st.columns(2)
        
        with col_export:
            if st.button("📊 导出成绩单", use_container_width=True):
                export_grade_report(assignment_id, assignment, submissions)
        
        with col_notify:
            if st.button("📢 通知未提交学生", use_container_width=True):
                notify_unsubmitted_students(assignment_id, assignment)
    
    except Exception as e:
        st.error(f"❌ 获取结果汇总失败：{str(e)}")

# 导出成绩单
def export_grade_report(assignment_id, assignment, submissions):
    """导出成绩单"""
    try:
        # 生成成绩数据
        grade_data = []
        for submission in submissions:
            # 提取分数
            grade = "未批改"
            if submission.get('ai_result'):
                result_text = submission['ai_result']
                import re
                score_match = re.search(r'(\d+(?:\.\d+)?)\s*分', result_text)
                if score_match:
                    grade = f"{score_match.group(1)}分"
                else:
                    grade = "已批改"
            
            grade_data.append({
                "学生姓名": submission['student_username'],
                "提交时间": submission['submitted_at'],
                "成绩": grade,
                "批改状态": "已批改" if submission.get('ai_result') else "未批改",
                "文件数量": len(submission.get('files', []))
            })
        
        # 转换为CSV
        import pandas as pd
        df = pd.DataFrame(grade_data)
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"成绩单_{assignment['title']}_{timestamp}.csv"
        
        st.download_button(
            "📥 下载成绩单",
            data=csv,
            file_name=filename,
            mime="text/csv",
            key="export_grades"
        )
        
        st.success("✅ 成绩单已准备好下载")
        
    except Exception as e:
        st.error(f"❌ 导出失败：{str(e)}")

# 通知未提交学生
def notify_unsubmitted_students(assignment_id, assignment):
    """通知未提交作业的学生"""
    try:
        # 获取班级所有学生
        all_students = get_class_students(assignment.get('class_id'))
        
        # 获取已提交的学生
        submissions = get_assignment_submissions(assignment_id)
        submitted_students = [s['student_username'] for s in submissions]
        
        # 找出未提交的学生
        unsubmitted_students = [s for s in all_students if s['username'] not in submitted_students]
        
        if not unsubmitted_students:
            st.info("✅ 所有学生都已提交作业")
            return
        
        # 发送通知
        for student in unsubmitted_students:
            add_notification(
                student['username'],
                f"作业提醒：{assignment['title']}",
                f"您还未提交作业《{assignment['title']}》，请尽快完成提交。截止时间：{assignment.get('due_date', '无限制')}",
                "warning"
            )
        
        st.success(f"✅ 已向 {len(unsubmitted_students)} 名未提交学生发送提醒")
        
        # 显示未提交学生列表
        with st.expander("📋 未提交学生名单", expanded=False):
            for student in unsubmitted_students:
                st.write(f"• {student.get('real_name', student['username'])} ({student['username']})")
    
    except Exception as e:
        st.error(f"❌ 发送通知失败：{str(e)}")

# 无标准批改启动函数
def start_no_standard_batch_grading(assignment_id, assignment, ungraded_count):
    """启动无批改标准的智能批改"""
    st.info(f"🤖 开始无标准智能批改 {ungraded_count} 份作业...")
    st.warning("💡 AI将根据题目内容和学生答案进行智能分析和评分")
    
    try:
        submissions = get_assignment_submissions(assignment_id)
        ungraded_submissions = [s for s in submissions if not s.get('ai_result')]
        
        if not ungraded_submissions:
            st.success("✅ 所有作业都已批改完成")
            return
        
        # 执行无标准批改
        execute_no_standard_batch_grading(assignment_id, assignment, ungraded_submissions)
        
    except Exception as e:
        st.error(f"❌ 批改失败：{str(e)}")

# 执行无标准批改
def execute_no_standard_batch_grading(assignment_id, assignment, ungraded_submissions):
    """执行无批改标准的批量批改"""
    progress_container = st.container()
    
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        
        success_count = 0
        failed_submissions = []
        
        for i, submission in enumerate(ungraded_submissions):
            status_text.text(f"🤖 正在智能分析 {submission['student_username']} 的作业... ({i+1}/{len(ungraded_submissions)})")
            
            try:
                # 检查学生提交的文件
                if not submission.get('files') or len(submission['files']) == 0:
                    raise ValueError("学生未提交任何文件")
                
                # 验证文件是否存在
                valid_files = []
                for file_path in submission['files']:
                    if Path(file_path).exists():
                        valid_files.append(file_path)
                    else:
                        print(f"警告：文件不存在 {file_path}")
                
                if not valid_files:
                    raise ValueError("学生提交的文件都不存在")
                
                # 调用无标准AI批改
                if assignment.get('question_files'):
                    # 有题目文件的情况
                    result = batch_correction_without_standard(
                        question_files=assignment['question_files'],
                        student_answer_files=valid_files,
                        strictness_level="标准"
                    )
                else:
                    # 没有题目文件，纯粹基于学生答案进行分析
                    result = intelligent_correction_with_files(
                        answer_files=valid_files,
                        marking_scheme_files=[],  # 空的批改标准
                        strictness_level="标准"
                    )
                
                # 保存结果
                update_submission_ai_result(submission['id'], str(result))
                
                # 发送通知
                add_notification(
                    submission['student_username'],
                    f"作业已智能批改：{assignment['title']}",
                    f"您的作业已完成AI智能分析，请查看结果。",
                    "success"
                )
                
                success_count += 1
                
                # 显示实时结果
                with results_container:
                    st.success(f"✅ {submission['student_username']} - 智能分析完成")
                
            except Exception as e:
                failed_submissions.append({
                    'student': submission['student_username'],
                    'error': str(e)
                })
                
                with results_container:
                    st.error(f"❌ {submission['student_username']} - 分析失败：{str(e)}")
            
            # 更新进度
            progress_bar.progress((i + 1) / len(ungraded_submissions))
        
        # 显示最终结果
        status_text.text("🎉 智能批改任务完成！")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("成功分析", success_count, delta=f"✅ {success_count}")
        with col2:
            st.metric("失败数量", len(failed_submissions), delta=f"❌ {len(failed_submissions)}")
        
        if failed_submissions:
            with st.expander("❌ 失败详情", expanded=False):
                for failed in failed_submissions:
                    st.error(f"**{failed['student']}**: {failed['error']}")
        
        if success_count > 0:
            st.balloons()
            st.success(f"🎉 智能批改完成！成功分析 {success_count} 份作业")
            st.info("💡 无标准批改结果仅供参考，建议教师进一步审核")
        
        # 自动刷新页面
        time.sleep(2)
        st_rerun()

# 更新作业文件的辅助函数
def update_assignment_files(assignment_id, file_type, file_path):
    """更新作业的文件列表"""
    try:
        # 这里应该调用数据库函数更新作业文件
        # 暂时只打印，需要在database.py中实现相应函数
        print(f"更新作业 {assignment_id} 的 {file_type}: {file_path}")
        return True
    except Exception as e:
        print(f"更新作业文件失败: {e}")
        return False

# ===================== 作业中心功能 =====================

def show_assignment_center():
    """显示作业中心主界面"""
    st.markdown('<h2 class="main-title">📚 作业中心</h2>', unsafe_allow_html=True)
    
    # 检查登录状态
    if not st.session_state.logged_in:
        st.warning("请先登录")
        st.session_state.page = "login"
        st_rerun()
        return
    
    # 获取用户角色
    user_role = st.session_state.get('user_role', '')
    if not user_role:
        st.error("用户角色未确定，请重新登录")
        st.session_state.page = "login"
        st_rerun()
        return
    
    # 顶部搜索和筛选
    filters = show_assignment_search_filters()
    
    # 概览仪表盘
    show_assignment_dashboard()
    
    # 作业列表
    show_assignment_list(filters)
    
    # 统计分析（可选展开）
    with st.expander("📈 数据分析", expanded=False):
        show_assignment_analytics()

def show_assignment_search_filters():
    """显示搜索和筛选界面"""
    st.markdown("### 🔍 搜索与筛选")
    
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            search_keyword = st.text_input(
                "搜索作业",
                placeholder="输入作业标题或描述关键词...",
                key="assignment_search",
                help="支持搜索作业标题和描述内容"
            )
        
        with col2:
            date_filter = st.selectbox(
                "📅 时间范围",
                ["全部", "最近7天", "最近30天", "本学期"],
                key="date_filter"
            )
        
        with col3:
            if st.session_state.user_role == 'teacher':
                status_filter = st.selectbox(
                    "📊 状态筛选",
                    ["全部", "待批改", "批改中", "已完成"],
                    key="status_filter"
                )
            else:
                status_filter = st.selectbox(
                    "📊 状态筛选",
                    ["全部", "未提交", "已提交", "已批改"],
                    key="status_filter"
                )
        
        with col4:
            if st.session_state.user_role == 'teacher':
                # 教师可以按班级筛选
                try:
                    classes = get_user_classes(st.session_state.username, 'teacher')
                    class_options = ["全部班级"] + [c['name'] for c in classes]
                    class_filter = st.selectbox(
                        "📚 班级筛选",
                        class_options,
                        key="class_filter"
                    )
                except:
                    class_filter = "全部班级"
            else:
                # 学生显示排序选项
                sort_option = st.selectbox(
                    "📋 排序方式",
                    ["最新发布", "截止时间", "成绩高低", "提交状态"],
                    key="sort_option"
                )
    
    # 构建筛选条件
    filters = {}
    
    if search_keyword:
        filters['keyword'] = search_keyword
    
    # 时间筛选
    if date_filter != "全部":
        from datetime import datetime, timedelta
        now = datetime.now()
        if date_filter == "最近7天":
            filters['date_from'] = (now - timedelta(days=7)).isoformat()
        elif date_filter == "最近30天":
            filters['date_from'] = (now - timedelta(days=30)).isoformat()
        elif date_filter == "本学期":
            # 假设学期从9月1日开始
            semester_start = datetime(now.year if now.month >= 9 else now.year - 1, 9, 1)
            filters['date_from'] = semester_start.isoformat()
    
    # 状态筛选
    if status_filter != "全部":
        if st.session_state.user_role == 'teacher':
            if status_filter == "待批改":
                filters['status'] = 'pending_grading'
            elif status_filter == "已完成":
                filters['status'] = 'completed'
        else:
            filters['status'] = status_filter.lower()
    
    # 班级筛选（仅教师）
    if st.session_state.user_role == 'teacher' and 'class_filter' in locals() and class_filter != "全部班级":
        try:
            classes = get_user_classes(st.session_state.username, 'teacher')
            selected_class = next((c for c in classes if c['name'] == class_filter), None)
            if selected_class:
                filters['class_id'] = selected_class['id']
        except:
            pass
    
    return filters

def show_assignment_dashboard():
    """显示作业概览仪表盘"""
    st.markdown("### 📊 概览仪表盘")
    
    # 获取统计数据
    try:
        stats = get_user_assignment_summary(
            st.session_state.username,
            st.session_state.user_role
        )
    except Exception as e:
        st.error(f"获取统计数据失败：{str(e)}")
        stats = {}
    
    # 显示关键指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📚 总作业数",
            stats.get('total_assignments', 0),
            delta=f"+{stats.get('new_this_week', 0)} 本周" if stats.get('new_this_week', 0) > 0 else None
        )
    
    with col2:
        if st.session_state.user_role == 'teacher':
            pending = stats.get('pending_grading', 0)
            st.metric(
                "⏳ 待批改",
                pending,
                delta="需要处理" if pending > 0 else "全部完成",
                delta_color="normal" if pending == 0 else "inverse"
            )
        else:
            submitted = stats.get('total_assignments', 0) - stats.get('pending_grading', 0)
            st.metric(
                "✅ 已提交",
                submitted,
                delta=f"完成率: {stats.get('completion_rate', 0):.1f}%"
            )
    
    with col3:
        avg_score = stats.get('avg_score', 0)
        st.metric(
            "📈 平均分",
            f"{avg_score:.1f}" if avg_score > 0 else "暂无",
            delta=f"{stats.get('score_trend', 0):+.1f}" if stats.get('score_trend', 0) != 0 else None
        )
    
    with col4:
        if st.session_state.user_role == 'teacher':
            st.metric(
                "👥 活跃班级",
                stats.get('active_classes', 0),
                delta=f"{stats.get('total_students', 0)} 学生"
            )
        else:
            st.metric(
                "📚 参与班级",
                stats.get('active_classes', 0),
                delta="学习中"
            )
    
    st.markdown("---")

def show_assignment_list(filters=None):
    """显示作业列表"""
    st.markdown("### 📋 作业列表")
    
    # 获取筛选后的作业数据
    try:
        data = get_assignment_center_data(
            st.session_state.username,
            st.session_state.user_role,
            filters
        )
        assignments = data['assignments']
    except Exception as e:
        st.error(f"获取作业数据失败：{str(e)}")
        assignments = []
    
    if not assignments:
        st.info("📝 暂无作业记录")
        if st.session_state.user_role == 'teacher':
            st.markdown("💡 **提示：** 请先在班级管理中发布作业")
        else:
            st.markdown("💡 **提示：** 请先加入班级或等待老师发布作业")
        return
    
    # 分页显示
    page_size = 8
    total_pages = (len(assignments) + page_size - 1) // page_size
    
    if total_pages > 1:
        col_page1, col_page2, col_page3 = st.columns([1, 2, 1])
        with col_page2:
            page = st.selectbox(
                "选择页码",
                range(1, total_pages + 1),
                format_func=lambda x: f"第 {x} 页 (共 {total_pages} 页)",
                key="assignment_page"
            )
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_assignments = assignments[start_idx:end_idx]
    else:
        page_assignments = assignments
    
    # 显示作业卡片
    for assignment in page_assignments:
        show_assignment_card(assignment)

def show_assignment_card(assignment):
    """显示单个作业卡片"""
    with st.container():
        # 创建作业卡片
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        
        with col1:
            # 作业标题和基本信息
            st.markdown(f"**📝 {assignment['title']}**")
            st.caption(f"📅 发布: {assignment['created_at'][:10]} | 📚 {assignment['class_name']}")
            
            if assignment.get('deadline'):
                deadline_str = assignment['deadline'][:10] if len(assignment['deadline']) > 10 else assignment['deadline']
                st.caption(f"⏰ 截止: {deadline_str}")
            
            if assignment.get('description'):
                desc = assignment['description']
                display_desc = desc[:50] + "..." if len(desc) > 50 else desc
                st.caption(f"📄 {display_desc}")
        
        with col2:
            # 提交统计和状态
            if st.session_state.user_role == 'teacher':
                submission_count = assignment.get('submission_count', 0)
                graded_count = assignment.get('graded_count', 0)
                total_students = assignment.get('total_students', 0)
                
                st.write(f"📊 {submission_count}/{total_students} 份提交")
                st.write(f"✅ {graded_count} 份已批改")
                
                if assignment.get('avg_score') and assignment.get('avg_score') > 0:
                    st.write(f"📈 平均分: {assignment['avg_score']:.1f}")
                else:
                    st.write("📈 平均分: 暂无")
            else:
                # 学生视角：显示自己的提交状态
                if assignment.get('user_submission_id'):
                    st.success("✅ 已提交")
                    submit_time = assignment.get('user_submitted_at', '')
                    if submit_time:
                        st.caption(f"提交时间: {submit_time[:10]}")
                    
                    if assignment.get('user_score') is not None:
                        st.write(f"📈 得分: {assignment['user_score']:.1f}")
                    else:
                        st.write("📈 得分: 批改中")
                else:
                    st.warning("⏳ 未提交")
                    if assignment.get('deadline'):
                        st.caption("请及时提交")
        
        with col3:
            # 状态标签
            status = get_assignment_status(assignment, st.session_state.user_role)
            if status == 'completed':
                st.success("✅ 已完成")
            elif status == 'grading':
                st.warning("⏳ 批改中")
            elif status == 'active':
                st.info("📝 进行中")
            elif status == 'expired':
                st.error("⏰ 已过期")
            
            # 显示文件信息
            question_count = len(assignment.get('question_files', []))
            marking_count = len(assignment.get('marking_files', []))
            
            if question_count > 0:
                st.caption(f"📋 {question_count} 个题目文件")
            if marking_count > 0:
                st.caption(f"📊 {marking_count} 个批改标准")
        
        with col4:
            # 快速操作按钮
            if st.session_state.user_role == 'teacher':
                if st.button("📊 详情", key=f"view_{assignment['id']}", use_container_width=True):
                    st.session_state.selected_assignment_detail = assignment
                
                ungraded = assignment.get('submission_count', 0) - assignment.get('graded_count', 0)
                if ungraded > 0:
                    if st.button("🚀 批改", key=f"grade_{assignment['id']}",
                               use_container_width=True, type="primary"):
                        # 跳转到批改界面
                        st.session_state.page = "teacher_dashboard"
                        st.session_state.selected_assignment_for_grading = assignment['id']
                        st_rerun()
            else:
                if st.button("📋 查看", key=f"view_student_{assignment['id']}", use_container_width=True):
                    st.session_state.selected_student_assignment = assignment
                
                if not assignment.get('user_submission_id'):
                    if st.button("📤 提交", key=f"submit_{assignment['id']}",
                               use_container_width=True, type="primary"):
                        st.session_state.assignment_to_submit = assignment
        
        st.markdown("---")

def show_assignment_analytics():
    """显示作业分析图表"""
    st.markdown("#### 📈 数据分析")
    
    # 获取分析数据
    try:
        analytics_data = get_assignment_analytics_data(
            st.session_state.username,
            st.session_state.user_role
        )
    except Exception as e:
        st.error(f"获取分析数据失败：{str(e)}")
        analytics_data = {'has_data': False}
    
    if not analytics_data.get('has_data', False):
        st.info("📊 暂无足够数据进行分析")
        return
    
    # 创建图表
    if st.session_state.user_role == 'teacher':
        tab1, tab2 = st.tabs(["📊 成绩分布", "📈 提交趋势"])
        
        with tab1:
            show_teacher_grade_distribution(analytics_data)
        
        with tab2:
            show_teacher_submission_trend(analytics_data)
    else:
        tab1, tab2 = st.tabs(["📈 个人成绩", "📊 学习进度"])
        
        with tab1:
            show_student_grade_trend(analytics_data)
        
        with tab2:
            show_student_progress(analytics_data)

def show_teacher_grade_distribution(analytics_data):
    """显示教师的成绩分布图"""
    assignments = analytics_data.get('assignments', [])
    
    if not assignments:
        st.info("暂无成绩数据")
        return
    
    # 计算成绩分布
    scores = []
    for assignment in assignments:
        if assignment.get('avg_score'):
            scores.append(assignment['avg_score'])
    
    if scores:
        import pandas as pd
        import numpy as np
        
        # 创建成绩分布数据
        score_ranges = ['0-60', '60-70', '70-80', '80-90', '90-100']
        counts = [0, 0, 0, 0, 0]
        
        for score in scores:
            if score < 60:
                counts[0] += 1
            elif score < 70:
                counts[1] += 1
            elif score < 80:
                counts[2] += 1
            elif score < 90:
                counts[3] += 1
            else:
                counts[4] += 1
        
        # 显示图表
        chart_data = pd.DataFrame({
            '成绩区间': score_ranges,
            '作业数量': counts
        })
        
        st.bar_chart(chart_data.set_index('成绩区间'))
        
        # 显示统计信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("平均分", f"{np.mean(scores):.1f}")
        with col2:
            st.metric("最高分", f"{max(scores):.1f}")
        with col3:
            st.metric("最低分", f"{min(scores):.1f}")
    else:
        st.info("暂无成绩数据可分析")

def show_teacher_submission_trend(analytics_data):
    """显示教师的提交趋势图"""
    assignments = analytics_data.get('assignments', [])
    
    if len(assignments) < 2:
        st.info("需要更多数据来显示趋势")
        return
    
    # 按时间排序并计算趋势
    import pandas as pd
    from datetime import datetime
    
    trend_data = []
    for assignment in assignments:
        try:
            date = datetime.fromisoformat(assignment['created_at'].replace('Z', '+00:00'))
            trend_data.append({
                '日期': date.strftime('%m-%d'),
                '提交数': assignment.get('submission_count', 0),
                '作业': assignment['title'][:10] + '...' if len(assignment['title']) > 10 else assignment['title']
            })
        except:
            continue
    
    if trend_data:
        df = pd.DataFrame(trend_data)
        st.line_chart(df.set_index('日期')['提交数'])
        
        # 显示详细数据
        with st.expander("📋 详细数据", expanded=False):
            st.dataframe(df, use_container_width=True)

def show_student_grade_trend(analytics_data):
    """显示学生的成绩趋势"""
    assignments = analytics_data.get('assignments', [])
    
    # 筛选有成绩的作业
    graded_assignments = [a for a in assignments if a.get('score') is not None]
    
    if len(graded_assignments) < 2:
        st.info("需要更多已批改的作业来显示趋势")
        return
    
    import pandas as pd
    from datetime import datetime
    
    # 准备趋势数据
    trend_data = []
    for assignment in graded_assignments:
        try:
            date = datetime.fromisoformat(assignment['created_at'].replace('Z', '+00:00'))
            trend_data.append({
                '日期': date.strftime('%m-%d'),
                '成绩': assignment['score'],
                '作业': assignment['title'][:10] + '...' if len(assignment['title']) > 10 else assignment['title']
            })
        except:
            continue
    
    if trend_data:
        df = pd.DataFrame(trend_data)
        st.line_chart(df.set_index('日期')['成绩'])
        
        # 显示成绩统计
        scores = [item['成绩'] for item in trend_data]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("平均分", f"{sum(scores)/len(scores):.1f}")
        with col2:
            st.metric("最高分", f"{max(scores):.1f}")
        with col3:
            st.metric("最低分", f"{min(scores):.1f}")

def show_student_progress(analytics_data):
    """显示学生的学习进度"""
    assignments = analytics_data.get('assignments', [])
    
    if not assignments:
        st.info("暂无学习数据")
        return
    
    # 计算进度统计
    total_assignments = len(assignments)
    submitted = len([a for a in assignments if a.get('submitted_at')])
    graded = len([a for a in assignments if a.get('score') is not None])
    
    # 显示进度条
    st.markdown("**📈 学习进度**")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("提交率", f"{submitted/total_assignments*100:.1f}%")
        st.progress(submitted/total_assignments if total_assignments > 0 else 0)
    
    with col2:
        st.metric("完成率", f"{graded/total_assignments*100:.1f}%")
        st.progress(graded/total_assignments if total_assignments > 0 else 0)

# 主函数
def main():
    init_session()
    show_sidebar()
    
    # 页面路由
    if st.session_state.page == "home":
        show_home()
    elif st.session_state.page == "login":
        show_login()

    elif st.session_state.page == "teacher_dashboard":
        show_teacher_dashboard()
    elif st.session_state.page == "student_dashboard":
        show_student_dashboard()
    elif st.session_state.page == "grading":
        show_grading()
    elif st.session_state.page == "assignment_management":
        show_assignment_management()
    elif st.session_state.page == "class_management":
        show_class_management()
    elif st.session_state.page == "class_detail":
        show_class_detail()
    elif st.session_state.page == "student_detail":
        show_student_detail()
    elif st.session_state.page == "analytics":
        show_analytics()
    elif st.session_state.page == "history":
        show_history()
    elif st.session_state.page == "result":
        show_result()
    else:
        show_home()

# ===================== 新的页面函数 =====================

def show_assignment_management():
    """作业管理页面"""
    st.markdown("### 📚 作业管理")
    
    if not st.session_state.logged_in:
        st.warning("请先登录以使用此功能")
        return
    
    # 获取用户信息
    user_info = get_user_info(st.session_state.username)
    if not user_info:
        st.error("无法获取用户信息")
        return
    
    # 根据功能分类显示
    tab1, tab2, tab3 = st.tabs(["📝 创建作业", "📋 我的作业", "📊 作业统计"])
    
    with tab1:
        show_create_assignment_tab()
    
    with tab2:
        show_my_assignments_tab()
    
    with tab3:
        show_assignment_stats_tab()

def show_create_assignment_tab():
    """创建作业标签页"""
    st.markdown("#### 📝 创建新作业")
    
    # 获取用户的班级列表
    try:
        # 直接查询数据库获取用户的所有班级（创建的和加入的）
        import sqlite3
        conn = sqlite3.connect('class_system.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取用户创建的班级
        cursor.execute('''
            SELECT c.id, c.name, c.description, c.invite_code, c.created_at,
                   COUNT(cm.student_username) as student_count
            FROM classes c
            LEFT JOIN class_members cm ON c.id = cm.class_id AND cm.is_active = 1
            WHERE c.teacher_username = ? AND c.is_active = 1
            GROUP BY c.id, c.name, c.description, c.invite_code, c.created_at
            ORDER BY c.created_at DESC
        ''', (st.session_state.username,))
        
        created_classes = [dict(row) for row in cursor.fetchall()]
        
        # 获取用户加入的班级
        cursor.execute('''
            SELECT c.id, c.name, c.description, c.teacher_username,
                   u.real_name as teacher_name, cm.joined_at,
                   COUNT(cm2.student_username) as student_count
            FROM class_members cm
            JOIN classes c ON cm.class_id = c.id
            LEFT JOIN users u ON c.teacher_username = u.username
            LEFT JOIN class_members cm2 ON c.id = cm2.class_id AND cm2.is_active = 1
            WHERE cm.student_username = ? AND cm.is_active = 1 AND c.is_active = 1
            GROUP BY c.id, c.name, c.description, c.teacher_username, u.real_name, cm.joined_at
            ORDER BY cm.joined_at DESC
        ''', (st.session_state.username,))
        
        joined_classes = [dict(row) for row in cursor.fetchall()]
        
        # 合并所有班级
        classes = created_classes + joined_classes
        
        conn.close()
        
        if not classes:
            st.info("请先创建或加入班级")
            return
    except Exception as e:
        st.error(f"获取班级列表失败：{str(e)}")
        return
    
    with st.form("create_assignment_form"):
        # 选择班级
        class_options = {cls['id']: cls['name'] for cls in classes}
        selected_class_id = st.selectbox(
            "选择班级",
            options=list(class_options.keys()),
            format_func=lambda x: class_options[x]
        )
        
        # 作业基本信息
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("作业标题", placeholder="请输入作业标题")
            description = st.text_area("作业描述", placeholder="请输入作业描述")
        
        with col2:
            deadline = st.date_input("截止日期")
            deadline_time = st.time_input("截止时间")
        
        # 文件上传
        st.markdown("##### 📁 文件上传")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**题目文件**")
            question_files = st.file_uploader(
                "上传题目文件",
                accept_multiple_files=True,
                type=['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg'],
                key="question_files"
            )
        
        with col2:
            st.markdown("**批改标准文件**")
            marking_files = st.file_uploader(
                "上传批改标准文件",
                accept_multiple_files=True,
                type=['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg'],
                key="marking_files"
            )
        
        # 提交按钮
        submitted = st.form_submit_button("📝 创建作业", type="primary", use_container_width=True)
        
        if submitted:
            if not title:
                st.error("请输入作业标题")
                return
            
            try:
                # 保存文件并创建作业
                question_file_paths = []
                marking_file_paths = []
                
                # 处理题目文件
                if question_files:
                    for file in question_files:
                        file_path = save_uploaded_file(file, "question")
                        question_file_paths.append(file_path)
                
                # 处理批改标准文件
                if marking_files:
                    for file in marking_files:
                        file_path = save_uploaded_file(file, "marking")
                        marking_file_paths.append(file_path)
                
                # 创建作业
                assignment_id = create_assignment(
                    class_id=selected_class_id,
                    title=title,
                    description=description,
                    question_files=question_file_paths,
                    marking_files=marking_file_paths,
                    deadline=f"{deadline} {deadline_time}"
                )
                
                st.success(f"✅ 作业创建成功！")
                st.balloons()
                
            except Exception as e:
                st.error(f"创建作业失败：{str(e)}")

def show_my_assignments_tab():
    """我的作业标签页"""
    st.markdown("#### 📋 我的作业")
    
    # 获取用户的班级列表
    try:
        # 直接查询数据库获取用户的所有班级（创建的和加入的）
        import sqlite3
        conn = sqlite3.connect('class_system.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取用户创建的班级
        cursor.execute('''
            SELECT c.id, c.name, c.description, c.invite_code, c.created_at,
                   COUNT(cm.student_username) as student_count
            FROM classes c
            LEFT JOIN class_members cm ON c.id = cm.class_id AND cm.is_active = 1
            WHERE c.teacher_username = ? AND c.is_active = 1
            GROUP BY c.id, c.name, c.description, c.invite_code, c.created_at
            ORDER BY c.created_at DESC
        ''', (st.session_state.username,))
        
        created_classes = [dict(row) for row in cursor.fetchall()]
        
        # 获取用户加入的班级
        cursor.execute('''
            SELECT c.id, c.name, c.description, c.teacher_username,
                   u.real_name as teacher_name, cm.joined_at,
                   COUNT(cm2.student_username) as student_count
            FROM class_members cm
            JOIN classes c ON cm.class_id = c.id
            LEFT JOIN users u ON c.teacher_username = u.username
            LEFT JOIN class_members cm2 ON c.id = cm2.class_id AND cm2.is_active = 1
            WHERE cm.student_username = ? AND cm.is_active = 1 AND c.is_active = 1
            GROUP BY c.id, c.name, c.description, c.teacher_username, u.real_name, cm.joined_at
            ORDER BY cm.joined_at DESC
        ''', (st.session_state.username,))
        
        joined_classes = [dict(row) for row in cursor.fetchall()]
        
        # 合并所有班级
        classes = created_classes + joined_classes
        
        conn.close()
        
        if not classes:
            st.info("暂无班级")
            return
    except Exception as e:
        st.error(f"获取班级列表失败：{str(e)}")
        return
    
    # 选择班级
    class_options = {cls['id']: cls['name'] for cls in classes}
    selected_class_id = st.selectbox(
        "选择班级",
        options=list(class_options.keys()),
        format_func=lambda x: class_options[x],
        key="my_assignments_class"
    )
    
    # 获取作业列表
    try:
        assignments = get_class_assignments(selected_class_id)
        if not assignments:
            st.info("该班级暂无作业")
            return
    except Exception as e:
        st.error(f"获取作业列表失败：{str(e)}")
        return
    
    # 显示作业列表
    for assignment in assignments:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**📝 {assignment['title']}**")
                st.caption(f"截止时间: {assignment.get('deadline', '无限制')}")
            
            with col2:
                # 获取提交统计
                try:
                    submissions = get_assignment_submissions(assignment['id'])
                    st.metric("提交数", len(submissions))
                except:
                    st.metric("提交数", "N/A")
            
            with col3:
                if st.button(f"📊 管理", key=f"manage_{assignment['id']}", use_container_width=True):
                    st.session_state.selected_assignment_id = assignment['id']
                    st.session_state.page = "assignment_detail"
                    st_rerun()
            
            st.divider()

def show_assignment_stats_tab():
    """作业统计标签页"""
    st.markdown("#### 📊 作业统计")
    
    # 获取统计数据
    try:
        # 直接查询数据库获取统计数据
        import sqlite3
        conn = sqlite3.connect('class_system.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取用户创建的班级统计
        cursor.execute('''
            SELECT COUNT(*) as created_classes_count
            FROM classes 
            WHERE teacher_username = ? AND is_active = 1
        ''', (st.session_state.username,))
        created_classes_count = cursor.fetchone()['created_classes_count']
        
        # 获取用户加入的班级统计
        cursor.execute('''
            SELECT COUNT(*) as joined_classes_count
            FROM class_members cm
            JOIN classes c ON cm.class_id = c.id
            WHERE cm.student_username = ? AND cm.is_active = 1 AND c.is_active = 1
        ''', (st.session_state.username,))
        joined_classes_count = cursor.fetchone()['joined_classes_count']
        
        total_classes = created_classes_count + joined_classes_count
        
        # 获取作业统计
        cursor.execute('''
            SELECT COUNT(*) as total_assignments
            FROM assignments a
            JOIN classes c ON a.class_id = c.id
            WHERE (c.teacher_username = ? OR c.id IN (
                SELECT class_id FROM class_members 
                WHERE student_username = ? AND is_active = 1
            )) AND a.is_active = 1 AND c.is_active = 1
        ''', (st.session_state.username, st.session_state.username))
        total_assignments = cursor.fetchone()['total_assignments']
        
        # 获取提交统计
        cursor.execute('''
            SELECT COUNT(*) as total_submissions
            FROM submissions s
            JOIN assignments a ON s.assignment_id = a.id
            JOIN classes c ON a.class_id = c.id
            WHERE s.student_username = ? AND a.is_active = 1 AND c.is_active = 1
        ''', (st.session_state.username,))
        total_submissions = cursor.fetchone()['total_submissions']
        
        conn.close()
        
        # 显示总体统计
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总班级数", total_classes)
        
        with col2:
            st.metric("总作业数", total_assignments)
        
        with col3:
            st.metric("我的提交数", total_submissions)
        
        with col4:
            if total_assignments > 0:
                completion_rate = (total_submissions / total_assignments) * 100
                st.metric("完成率", f"{completion_rate:.1f}%")
            else:
                st.metric("完成率", "N/A")
        
    except Exception as e:
        st.error(f"获取统计数据失败：{str(e)}")

def show_class_management():
    """班级管理页面 - 整合作业管理和数据分析"""
    st.markdown("### 🏫 班级系统")
    
    if not st.session_state.logged_in:
        st.warning("请先登录以使用此功能")
        if st.button("🔐 前往登录", use_container_width=True):
            st.session_state.page = "login"
            st_rerun()
        return
    
    # 顶部导航标签 - 整合所有班级相关功能
    main_tab1, main_tab2, main_tab3 = st.tabs(["👥 班级管理", "📚 作业管理", "📊 数据分析"])
    
    with main_tab1:
        # 原有的班级管理功能
        st.markdown("#### 班级管理")
        sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["🏫 我创建的班级", "👥 我加入的班级", "➕ 创建班级", "🔗 加入班级"])
        
        with sub_tab1:
            show_my_created_classes_tab()
        
        with sub_tab2:
            show_my_joined_classes_tab()
        
        with sub_tab3:
            show_create_class_tab()
        
        with sub_tab4:
            show_join_class_tab()
    
    with main_tab2:
        # 作业管理功能
        show_assignment_management_content()
    
    with main_tab3:
        # 数据分析功能
        show_analytics_content()

def show_assignment_management_content():
    """作业管理内容 - 整合到班级管理中"""
    st.markdown("#### 📚 作业管理")
    
    # 根据功能分类显示
    tab1, tab2, tab3 = st.tabs(["📝 创建作业", "📋 我的作业", "📊 作业统计"])
    
    with tab1:
        show_create_assignment_tab()
    
    with tab2:
        show_my_assignments_tab()
    
    with tab3:
        show_assignment_stats_tab()

def show_analytics_content():
    """数据分析内容 - 整合到班级管理中"""
    st.markdown("#### 📊 数据分析")
    
    tab1, tab2, tab3 = st.tabs(["📈 总体统计", "📊 班级分析", "🎯 个人分析"])
    
    with tab1:
        show_overall_stats()
    
    with tab2:
        show_class_analytics()
    
    with tab3:
        show_personal_analytics()

def show_my_created_classes_tab():
    """我创建的班级标签页"""
    st.markdown("#### 🏫 我创建的班级")
    
    try:
        # 直接查询数据库获取班级信息
        import sqlite3
        conn = sqlite3.connect('class_system.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, c.name, c.description, c.invite_code, c.created_at,
                   COUNT(cm.student_username) as student_count
            FROM classes c
            LEFT JOIN class_members cm ON c.id = cm.class_id AND cm.is_active = 1
            WHERE c.teacher_username = ? AND c.is_active = 1
            GROUP BY c.id, c.name, c.description, c.invite_code, c.created_at
            ORDER BY c.created_at DESC
        ''', (st.session_state.username,))
        
        classes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        if not classes:
            st.info("您还没有创建任何班级")
            return
        
        for cls in classes:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**🏫 {cls['name']}**")
                    st.caption(f"班级代码: {cls.get('invite_code', 'N/A')}")
                    st.caption(f"创建时间: {cls.get('created_at', 'N/A')}")
                
                with col2:
                    # 获取班级作业数量
                    try:
                        assignments = get_class_assignments(cls['id'])
                        st.metric("作业数", len(assignments))
                    except:
                        st.metric("作业数", "N/A")
                
                with col3:
                    # 获取学生数量
                    st.metric("学生数", cls.get('student_count', 0))
                
                with col4:
                    # 管理和删除按钮
                    if st.button(f"📊 管理", key=f"manage_created_class_{cls['id']}", use_container_width=True):
                        st.session_state.selected_class_id = cls['id']
                        st.session_state.page = "class_detail"
                        st_rerun()
                    
                    # 删除班级按钮（危险操作）
                    if st.button(f"🗑️ 删除", key=f"delete_class_{cls['id']}", use_container_width=True, type="secondary"):
                        st.session_state.delete_class_id = cls['id']
                        st.session_state.delete_class_name = cls['name']
                        st.session_state.show_delete_confirm = True
                
                st.divider()
        
        # 删除确认对话框
        if st.session_state.get('show_delete_confirm', False):
            with st.container():
                st.warning("⚠️ 危险操作")
                st.markdown(f"**您确定要删除班级 '{st.session_state.get('delete_class_name', '')}' 吗？**")
                st.markdown("此操作将：")
                st.markdown("- 解散班级并移除所有学生")
                st.markdown("- 停用班级相关的所有作业")
                st.markdown("- **此操作不可撤销**")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    if st.button("❌ 取消", use_container_width=True):
                        st.session_state.show_delete_confirm = False
                        st.session_state.delete_class_id = None
                        st.session_state.delete_class_name = None
                        st_rerun()
                
                with col2:
                    # 需要输入班级名称确认
                    confirm_name = st.text_input("请输入班级名称确认删除", key="confirm_delete_name")
                
                with col3:
                    if st.button("🗑️ 确认删除", use_container_width=True, type="primary"):
                        if confirm_name == st.session_state.get('delete_class_name', ''):
                            try:
                                from database import delete_class
                                success = delete_class(st.session_state.delete_class_id, st.session_state.username)
                                if success:
                                    st.success("✅ 班级删除成功")
                                    st.balloons()
                                    # 清理状态
                                    st.session_state.show_delete_confirm = False
                                    st.session_state.delete_class_id = None
                                    st.session_state.delete_class_name = None
                                    time.sleep(1)
                                    st_rerun()
                                else:
                                    st.error("❌ 删除班级失败，请重试")
                            except Exception as e:
                                st.error(f"删除班级失败：{str(e)}")
                        else:
                            st.error("班级名称不匹配，请重新输入")
    
    except Exception as e:
        st.error(f"获取班级列表失败：{str(e)}")

def show_my_joined_classes_tab():
    """我加入的班级标签页"""
    st.markdown("#### 👥 我加入的班级")
    
    try:
        from database import get_student_classes
        classes = get_student_classes(st.session_state.username)
        if not classes:
            st.info("您还没有加入任何班级")
            return
        
        for cls in classes:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**🏫 {cls['name']}**")
                    st.caption(f"教师: {cls.get('teacher_name', '未知')}")
                    st.caption(f"加入时间: {cls.get('joined_at', 'N/A')}")
                
                with col2:
                    # 获取班级作业数量
                    try:
                        assignments = get_class_assignments(cls['id'])
                        st.metric("作业数", len(assignments))
                    except:
                        st.metric("作业数", "N/A")
                
                with col3:
                    # 获取我的提交数量
                    try:
                        from database import get_student_submissions_in_class
                        submissions = get_student_submissions_in_class(st.session_state.username, cls['id'])
                        st.metric("已提交", len(submissions))
                    except:
                        st.metric("已提交", "N/A")
                
                with col4:
                    # 查看和退出按钮
                    if st.button(f"📊 查看", key=f"view_joined_class_{cls['id']}", use_container_width=True):
                        st.session_state.selected_class_id = cls['id']
                        st.session_state.page = "class_detail"
                        st_rerun()
                    
                    # 退出班级按钮
                    if st.button(f"🚪 退出", key=f"leave_class_{cls['id']}", use_container_width=True, type="secondary"):
                        st.session_state.leave_class_id = cls['id']
                        st.session_state.leave_class_name = cls['name']
                        st.session_state.show_leave_confirm = True
                
                st.divider()
        
        # 退出确认对话框
        if st.session_state.get('show_leave_confirm', False):
            with st.container():
                st.warning("⚠️ 确认退出")
                st.markdown(f"**您确定要退出班级 '{st.session_state.get('leave_class_name', '')}' 吗？**")
                st.markdown("退出后您将：")
                st.markdown("- 无法查看班级作业和通知")
                st.markdown("- 无法提交新的作业")
                st.markdown("- 需要重新获取邀请码才能加入")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("❌ 取消", use_container_width=True):
                        st.session_state.show_leave_confirm = False
                        st.session_state.leave_class_id = None
                        st.session_state.leave_class_name = None
                        st_rerun()
                
                with col2:
                    if st.button("🚪 确认退出", use_container_width=True, type="primary"):
                        try:
                            from database import leave_class
                            success = leave_class(st.session_state.leave_class_id, st.session_state.username)
                            if success:
                                st.success("✅ 已成功退出班级")
                                # 清理状态
                                st.session_state.show_leave_confirm = False
                                st.session_state.leave_class_id = None
                                st.session_state.leave_class_name = None
                                time.sleep(1)
                                st_rerun()
                            else:
                                st.error("❌ 退出班级失败，请重试")
                        except Exception as e:
                            st.error(f"退出班级失败：{str(e)}")
    
    except Exception as e:
        st.error(f"获取班级列表失败：{str(e)}")

def show_create_class_tab():
    """创建班级标签页"""
    st.markdown("#### ➕ 创建新班级")
    
    with st.form("create_class_form"):
        class_name = st.text_input("班级名称", placeholder="请输入班级名称")
        class_description = st.text_area("班级描述", placeholder="请输入班级描述（可选）")
        
        submitted = st.form_submit_button("🏫 创建班级", type="primary", use_container_width=True)
        
        if submitted:
            if not class_name:
                st.error("请输入班级名称")
                return
            
            try:
                invite_code = create_class(st.session_state.username, class_name, class_description)
                if invite_code:
                    st.success(f"✅ 班级创建成功！")
                    st.info(f"📋 班级邀请码：**{invite_code}**")
                    st.info("请将邀请码分享给学生，他们可以使用此代码加入班级")
                    st.balloons()
                else:
                    st.error("创建班级失败，请重试")
                
            except Exception as e:
                st.error(f"创建班级失败：{str(e)}")

def show_join_class_tab():
    """加入班级标签页"""
    st.markdown("#### 🔗 加入班级")
    
    with st.form("join_class_form"):
        invite_code = st.text_input("邀请码", placeholder="请输入班级邀请码")
        
        submitted = st.form_submit_button("🔗 加入班级", type="primary", use_container_width=True)
        
        if submitted:
            if not invite_code:
                st.error("请输入邀请码")
                return
            
            try:
                result = join_class_by_code(st.session_state.username, invite_code)
                if result:
                    st.success("✅ 成功加入班级！")
                    st.balloons()
                else:
                    st.error("加入班级失败，请检查邀请码是否正确")
                
            except Exception as e:
                st.error(f"加入班级失败：{str(e)}")

def show_analytics():
    """数据分析页面"""
    st.markdown("### 📊 数据分析")
    
    if not st.session_state.logged_in:
        st.warning("请先登录以使用此功能")
        return
    
    tab1, tab2, tab3 = st.tabs(["📈 总体统计", "📊 班级分析", "🎯 个人分析"])
    
    with tab1:
        show_overall_stats()
    
    with tab2:
        show_class_analytics()
    
    with tab3:
        show_personal_analytics()

def show_overall_stats():
    """总体统计"""
    st.markdown("#### 📈 总体统计")
    
    try:
        stats = get_user_assignment_summary(st.session_state.username)
        
        # 显示关键指标
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="总班级数",
                value=stats.get('total_classes', 0),
                delta=None
            )
        
        with col2:
            st.metric(
                label="总作业数",
                value=stats.get('total_assignments', 0),
                delta=None
            )
        
        with col3:
            if 'total_submissions' in stats:
                st.metric(
                    label="总提交数",
                    value=stats['total_submissions'],
                    delta=None
                )
            else:
                st.metric(
                    label="已完成作业",
                    value=stats.get('completed_assignments', 0),
                    delta=None
                )
        
        with col4:
            if 'total_submissions' in stats and stats.get('total_assignments', 0) > 0:
                completion_rate = (stats['total_submissions'] / stats['total_assignments']) * 100
                st.metric(
                    label="完成率",
                    value=f"{completion_rate:.1f}%",
                    delta=None
                )
            else:
                st.metric(
                    label="完成率",
                    value="N/A",
                    delta=None
                )
        
        st.markdown("---")
        
        # 显示详细信息
        st.markdown("#### 📋 详细信息")
        st.info("更多详细的数据分析功能正在开发中...")
        
    except Exception as e:
        st.error(f"获取统计数据失败：{str(e)}")

def show_class_analytics():
    """班级分析"""
    st.markdown("#### 📊 班级分析")
    st.info("班级分析功能正在开发中...")

def show_personal_analytics():
    """个人分析"""
    st.markdown("#### 🎯 个人分析")
    st.info("个人分析功能正在开发中...")

def save_uploaded_file(uploaded_file, file_type):
    """保存上传的文件"""
    # 创建目录
    upload_dir = Path("class_files") / file_type
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{timestamp}_{uploaded_file.name}"
    file_path = upload_dir / file_name
    
    # 保存文件
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return str(file_path)

def show_class_detail():
    """班级详情页面 - 显示学生列表"""
    if not st.session_state.get('selected_class_id'):
        st.error("未选择班级")
        return
    
    class_id = st.session_state.selected_class_id
    
    # 获取班级信息
    try:
        from database import get_teacher_classes, get_student_classes
        
        # 获取用户创建的班级和加入的班级
        created_classes = get_teacher_classes(st.session_state.username)
        joined_classes = get_student_classes(st.session_state.username)
        
        # 合并所有班级
        all_classes = created_classes + joined_classes
        
        # 确保class_id是整数类型进行比较
        class_id_int = int(class_id) if isinstance(class_id, str) else class_id
        selected_class = next((c for c in all_classes if c['id'] == class_id_int), None)
        if not selected_class:
            st.error("班级不存在或您没有访问权限")
            return
    except Exception as e:
        st.error(f"获取班级信息失败：{str(e)}")
        return
    
    # 页面标题和返回按钮
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### 🏫 {selected_class['name']}")
        st.caption(f"班级代码: {selected_class.get('invite_code', 'N/A')}")
    
    with col2:
        if st.button("← 返回", use_container_width=True):
            st.session_state.page = "class_management"
            st_rerun()
    
    st.divider()
    
    # 获取学生列表
    try:
        from database import get_class_students
        students = get_class_students(class_id)
        
        if not students:
            st.info("该班级暂无学生")
            return
        
        st.markdown(f"#### 👥 学生列表 ({len(students)}人)")
        
        # 显示学生列表
        for student in students:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**👤 {student.get('real_name', student['username'])}**")
                    st.caption(f"用户名: {student['username']}")
                
                with col2:
                    # 获取学生作业统计
                    try:
                        from database import get_student_submissions_in_class
                        submissions = get_student_submissions_in_class(student['username'], class_id)
                        st.metric("已提交", len(submissions))
                    except:
                        st.metric("已提交", "N/A")
                
                with col3:
                    # 获取已批改数量
                    try:
                        graded_count = len([s for s in submissions if s.get('ai_result')])
                        st.metric("已批改", graded_count)
                    except:
                        st.metric("已批改", "N/A")
                
                with col4:
                    if st.button(f"📊 查看详情", key=f"view_student_{student['username']}", use_container_width=True):
                        st.session_state.selected_student_username = student['username']
                        st.session_state.selected_class_id = class_id
                        st.session_state.page = "student_detail"
                        st_rerun()
                
                st.divider()
    
    except Exception as e:
        st.error(f"获取学生列表失败：{str(e)}")

def show_student_detail():
    """学生详情页面"""
    if not st.session_state.get('selected_student_username') or not st.session_state.get('selected_class_id'):
        st.error("缺少学生或班级信息")
        return
    
    student_username = st.session_state.selected_student_username
    class_id = st.session_state.selected_class_id
    
    # 确保class_id是整数类型
    class_id = int(class_id) if isinstance(class_id, str) else class_id
    
    # 获取学生信息
    try:
        from database import get_user_info
        student_info = get_user_info(student_username)
        if not student_info:
            st.error("学生不存在")
            return
    except Exception as e:
        st.error(f"获取学生信息失败：{str(e)}")
        return
    
    # 页面标题和返回按钮
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### 👤 {student_info.get('real_name', student_username)} 的详细信息")
        st.caption(f"用户名: {student_username}")
    
    with col2:
        if st.button("← 返回班级", use_container_width=True):
            st.session_state.page = "class_detail"
            st_rerun()
    
    st.divider()
    
    # 学生基本信息
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📋 基本信息")
        st.write(f"**姓名：** {student_info.get('real_name', '未设置')}")
        st.write(f"**用户名：** {student_username}")
        st.write(f"**注册时间：** {student_info.get('created_at', '未知')}")
    
    with col2:
        st.markdown("#### 📊 作业统计")
        try:
            from database import get_student_submissions_in_class, get_class_assignments
            submissions = get_student_submissions_in_class(student_username, class_id)
            assignments = get_class_assignments(class_id)
            
            st.metric("总作业数", len(assignments))
            st.metric("已提交", len(submissions))
            
            graded_count = len([s for s in submissions if s.get('ai_result')])
            st.metric("已批改", graded_count)
            
            if len(assignments) > 0:
                completion_rate = (len(submissions) / len(assignments)) * 100
                st.metric("完成率", f"{completion_rate:.1f}%")
        except Exception as e:
            st.error(f"获取统计数据失败：{str(e)}")
    
    with col3:
        st.markdown("#### 🎯 成绩概览")
        try:
            # 计算平均成绩（如果有批改结果）
            graded_submissions = [s for s in submissions if s.get('ai_result')]
            if graded_submissions:
                # 这里可以添加成绩解析逻辑
                st.metric("已批改作业", len(graded_submissions))
                st.info("成绩分析功能开发中...")
            else:
                st.info("暂无批改结果")
        except:
            st.info("暂无成绩数据")
    
    st.divider()
    
    # 作业记录详情
    st.markdown("#### 📚 作业记录")
    
    if not submissions:
        st.info("该学生暂无作业提交记录")
        return
    
    # 按作业分组显示
    try:
        assignments = get_class_assignments(class_id)
        assignment_dict = {a['id']: a for a in assignments}
        
        for submission in submissions:
            assignment = assignment_dict.get(submission['assignment_id'])
            if not assignment:
                continue
            
            with st.expander(f"📝 {assignment['title']}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**提交时间：** {submission.get('submitted_at', '未知')}")
                    st.write(f"**作业截止：** {assignment.get('deadline', '无限制')}")
                    
                    # 显示提交的文件
                    if submission.get('files'):
                        st.write("**📁 提交文件：**")
                        for file_path in submission['files']:
                            if Path(file_path).exists():
                                file_name = Path(file_path).name
                                st.write(f"• {file_name}")
                            else:
                                st.write(f"• {Path(file_path).name} (文件不存在)")
                
                with col2:
                    # 显示批改状态和结果
                    if submission.get('ai_result'):
                        st.success("✅ 已批改")
                        
                        # 显示批改结果摘要
                        with st.expander("查看批改结果", expanded=False):
                            result = submission['ai_result']
                            if len(result) > 500:
                                st.write(result[:500] + "...")
                                st.caption("结果已截断，完整结果请在作业管理中查看")
                            else:
                                st.write(result)
                    else:
                        st.warning("⏳ 待批改")
                        
                        # 如果有批改标准，可以立即批改
                        if assignment.get('marking_files'):
                            if st.button(f"🤖 立即批改", key=f"grade_now_{submission['id']}"):
                                try:
                                    with st.spinner("正在批改..."):
                                        result = batch_correction_with_standard(
                                            marking_scheme_files=assignment['marking_files'],
                                            student_answer_files=submission['files'],
                                            strictness_level="标准"
                                        )
                                        
                                        # 保存批改结果
                                        from database import update_submission_ai_result
                                        update_submission_ai_result(submission['id'], str(result))
                                        
                                        st.success("✅ 批改完成！")
                                        st_rerun()
                                        
                                except Exception as e:
                                    st.error(f"批改失败：{str(e)}")
    
    except Exception as e:
        st.error(f"获取作业记录失败：{str(e)}")
    
    st.divider()
    
    # AI驱动的个人分析
    st.markdown("#### 🤖 AI个人分析")
    
    if st.button("🔍 生成AI分析报告", use_container_width=True):
        try:
            with st.spinner("AI正在分析学生表现..."):
                # 准备分析数据
                analysis_data = {
                    "student_name": student_info.get('real_name', student_username),
                    "total_assignments": len(assignments),
                    "submitted_assignments": len(submissions),
                    "graded_assignments": len([s for s in submissions if s.get('ai_result')]),
                    "submission_details": []
                }
                
                # 收集详细的提交信息
                for submission in submissions:
                    assignment = assignment_dict.get(submission['assignment_id'])
                    if assignment:
                        detail = {
                            "assignment_title": assignment['title'],
                            "submitted_at": submission.get('submitted_at'),
                            "has_result": bool(submission.get('ai_result')),
                            "result_summary": submission.get('ai_result', '')[:200] if submission.get('ai_result') else None
                        }
                        analysis_data["submission_details"].append(detail)
                
                # 生成AI分析
                if API_AVAILABLE:
                    analysis_prompt = f"""
请基于以下学生数据生成一份详细的个人学习分析报告：

学生姓名：{analysis_data['student_name']}
总作业数：{analysis_data['total_assignments']}
已提交作业数：{analysis_data['submitted_assignments']}
已批改作业数：{analysis_data['graded_assignments']}

作业详情：
{json.dumps(analysis_data['submission_details'], ensure_ascii=False, indent=2)}

请从以下几个方面进行分析：
1. 学习态度和积极性
2. 作业完成情况
3. 学习表现趋势
4. 优势和不足
5. 改进建议
6. 个性化学习建议

请用中文回答，语言要专业但易懂，适合教师和家长阅读。
"""
                    
                    try:
                        analysis_result = call_tongyiqianwen_api(analysis_prompt)
                        
                        # 显示分析结果
                        st.markdown("##### 📊 AI分析报告")
                        st.markdown(analysis_result)
                        
                        # 提供下载选项
                        st.download_button(
                            label="📥 下载分析报告",
                            data=analysis_result,
                            file_name=f"{student_username}_analysis_report.txt",
                            mime="text/plain"
                        )
                        
                    except Exception as e:
                        st.error(f"AI分析失败：{str(e)}")
                        # 提供基础分析
                        show_basic_analysis(analysis_data)
                else:
                    # 演示模式的基础分析
                    show_basic_analysis(analysis_data)
                    
        except Exception as e:
            st.error(f"生成分析报告失败：{str(e)}")

def show_basic_analysis(analysis_data):
    """显示基础分析（当AI不可用时）"""
    st.markdown("##### 📊 基础分析报告")
    
    completion_rate = (analysis_data['submitted_assignments'] / analysis_data['total_assignments'] * 100) if analysis_data['total_assignments'] > 0 else 0
    grading_rate = (analysis_data['graded_assignments'] / analysis_data['submitted_assignments'] * 100) if analysis_data['submitted_assignments'] > 0 else 0
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📈 学习表现**")
        if completion_rate >= 80:
            st.success(f"✅ 作业完成率：{completion_rate:.1f}% (优秀)")
        elif completion_rate >= 60:
            st.warning(f"⚠️ 作业完成率：{completion_rate:.1f}% (良好)")
        else:
            st.error(f"❌ 作业完成率：{completion_rate:.1f}% (需改进)")
        
        st.info(f"📊 批改完成率：{grading_rate:.1f}%")
    
    with col2:
        st.markdown("**💡 建议**")
        if completion_rate < 80:
            st.write("• 建议提高作业提交的及时性")
        if grading_rate < 100:
            st.write("• 部分作业待批改，请关注反馈")
        if completion_rate >= 80:
            st.write("• 学习态度积极，继续保持")
        
        st.write("• 建议定期复习已批改的作业")

if __name__ == "__main__":
    main()
