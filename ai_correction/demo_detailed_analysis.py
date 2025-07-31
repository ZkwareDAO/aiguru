#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细分析功能演示
运行: streamlit run demo_detailed_analysis.py
"""

import streamlit as st
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.detailed_analysis_service import DetailedAnalysisService
from src.ui.components.detailed_analysis import DetailedAnalysisComponent


def main():
    """主函数"""
    st.set_page_config(
        page_title="详细分析功能演示",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 详细分析功能演示")
    st.markdown("---")
    
    try:
        # 创建服务和组件
        analysis_service = DetailedAnalysisService()
        analysis_component = DetailedAnalysisComponent(analysis_service)
        
        # 渲染组件
        analysis_component.render()
        
    except Exception as e:
        st.error(f"❌ 加载详细分析组件失败: {e}")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()