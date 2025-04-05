import streamlit as st
import os

def main_menu_page():
    st.title("🎯 AI智能批改系统")
    
    # 加载Logo
    with open(os.path.join("static", "images", "logo.svg"), "r", encoding="utf-8") as f:
        logo_svg = f.read()
    st.image(logo_svg, use_column_width=True)
    
    # 应用介绍
    st.header("📖 应用介绍")
    st.write("""
    AI智能批改系统是一款专业的自动化批改工具，结合了OCR识别、AI分析和PDF标注等功能，
    为教师提供高效、精准的作业批改解决方案。系统支持多种文件格式，可以自动识别试题内容，
    根据评分标准进行智能评分，并提供详细的批改反馈。
    """)
    
    # 加载工作流程图
    with open(os.path.join("static", "images", "workflow.svg"), "r", encoding="utf-8") as f:
        workflow_svg = f.read()
    st.image(workflow_svg, use_column_width=True)
    
    # 功能特点
    st.header("✨ 功能特点")
    with open(os.path.join("static", "images", "features.svg"), "r", encoding="utf-8") as f:
        features_svg = f.read()
    st.image(features_svg, use_column_width=True)
    
    # 使用说明
    st.header("📝 使用说明")
    st.write("""
    1. **文件上传**
       - 支持PDF、Word、Excel和图片格式
       - 分别上传题目文件、评分标准和学生作答
    
    2. **AI批改**
       - 系统自动识别文件内容
       - 根据评分标准进行智能评分
       - 生成详细的批改报告
    
    3. **PDF标注**
       - 支持手动添加批注和评语
       - 可以导出带有标注的PDF文件
    
    4. **文件管理**
       - 查看所有上传的文件
       - 下载批改后的文件
       - 管理批改历史记录
    """)
    
    # 开发历程
    st.header("🚀 开发历程")
    with open(os.path.join("static", "images", "timeline.svg"), "r", encoding="utf-8") as f:
        timeline_svg = f.read()
    st.image(timeline_svg, use_column_width=True)
    
    # 功能区导航
    st.header("🎯 功能区导航")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝 AI批改", use_container_width=True):
            st.session_state.page = "file_mgmt"
            st.rerun()
    
    with col2:
        if st.button("📥 文件管理", use_container_width=True):
            st.session_state.page = "download"
            st.rerun()