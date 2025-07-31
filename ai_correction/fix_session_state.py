#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复Streamlit session state的undefined问题
"""

import streamlit as st
import os
import sys

def fix_session_state():
    """修复session state中的undefined值"""
    
    # 清理所有session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # 重新初始化session state
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.page = "home"
    st.session_state.correction_result = ""
    st.session_state.uploaded_files_data = []
    st.session_state.current_file_index = 0
    st.session_state.correction_settings = {}
    st.session_state.show_class_system = False
    st.session_state.user_role = ""
    st.session_state.current_class_id = ""
    st.session_state.current_assignment_id = ""
    
    print("✅ Session state已修复")

def main():
    """主函数"""
    print("🔧 正在修复Streamlit session state...")
    
    try:
        # 导入streamlit并修复session state
        import streamlit as st
        fix_session_state()
        print("✅ 修复完成")
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main() 