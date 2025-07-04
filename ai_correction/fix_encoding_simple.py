#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的编码修复脚本
"""

import re

def fix_encoding_issues():
    """修复streamlit_simple.py中的编码问题"""
    
    # 读取文件
    with open('streamlit_simple.py', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 修复常见的编码问题
    fixes = [
        (r'�离', ''),  # 删除损坏的字符
        (r'st\.success\(f"[^"]*个题目文[^"]*\)', 'st.success(f"已上传 {len(question_files)} 个题目文件")'),
        (r'st\.success\(f"[^"]*个答案文[^"]*\)', 'st.success(f"已上传 {len(answer_files)} 个答案文件")'),
        (r'st\.success\(f"[^"]*个标准文[^"]*\)', 'st.success(f"已上传 {len(marking_files)} 个标准文件")'),
        (r'st\.text\(f"保存[^"]*QUESTION_', 'st.text(f"保存为: QUESTION_'),
        (r'st\.text\(f"保存[^"]*ANSWER_', 'st.text(f"保存为: ANSWER_'),
        (r'st\.text\(f"保存[^"]*MARKING_', 'st.text(f"保存为: MARKING_'),
        (r'st\.error\(".*AI批改引擎未就绪.*"\)', 'st.error("❌ AI批改引擎未就绪，请检查API配置")'),
        (r'status_text\.text\(".*正在分析上传的文.*"\)', 'status_text.text("🔍 正在分析上传的文件...")'),
        (r'status_text\.text\(".*批改完成.*正在整理结.*"\)', 'status_text.text("✅ 批改完成，正在整理结果...")'),
        (r'status_text\.text\(".*批改完成.*"\)', 'status_text.text("🎉 批改完成!")'),
        (r'st\.success\(".*批改完成.*即将跳转.*"\)', 'st.success("✅ 批改完成！即将跳转到批改详情页面...")'),
        (r'st\.error\(".*批改失败.*"\)', 'st.error("❌ 批改失败，请检查文件格式或重试")'),
        (r'st\.error\(f".*批改过程中出现错误.*"\)', 'st.error(f"❌ 批改过程中出现错误：{str(e)}")'),
        (r'"""显示侧边.*"""', '"""显示侧边栏"""'),
        (r'st\.header\(".*批改控制"\)', 'st.header("🛠️ 批改控制")'),
        (r'help="处理大量题目时推荐启.*"', 'help="处理大量题目时推荐启用"'),
        (r'st\.checkbox\("跳过缺失文件的题.*"', 'st.checkbox("跳过缺失文件的题目"'),
        (r'help="避免分批中出现总结.*最后单独生.*"', 'help="避免分批中出现总结，最后单独生成"'),
        (r'help="限制每题的最大步骤数.*防止循.*"', 'help="限制每题的最大步骤数，防止循环"'),
        (r'st\.session_state\.batch_settings.*保存设.*', 'st.session_state.batch_settings  # 保存设置'),
        (r'# 系统状.*', '# 系统状态'),
        (r'st\.success\(".*AI引擎正常"\)', 'st.success("✅ AI引擎正常")'),
        (r'if st\.button\(".*退出登.*"', 'if st.button("🚪 退出登录"'),
        (r'# 未登录状.*', '# 未登录状态'),
    ]
    
    # 应用修复
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # 写回文件
    with open('streamlit_simple.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("编码修复完成！")

if __name__ == "__main__":
    fix_encoding_issues() 