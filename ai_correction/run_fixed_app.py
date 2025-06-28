#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI批改系统修复版启动脚本
完全抑制MuPDF错误输出，提供最佳用户体验
"""

import os
import sys
import warnings
import subprocess
from pathlib import Path

def setup_environment():
    """设置环境变量和错误抑制"""
    # 抑制所有警告
    warnings.filterwarnings("ignore")
    
    # 设置环境变量抑制MuPDF输出
    os.environ['MUPDF_QUIET'] = '1'
    os.environ['PYTHONWARNINGS'] = 'ignore'
    
    # 重定向stderr到devnull
    if hasattr(os, 'devnull'):
        sys.stderr = open(os.devnull, 'w')

def check_dependencies():
    """检查关键依赖"""
    required = ['streamlit', 'PIL', 'openai']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
            print(f"✓ {pkg}")
        except ImportError:
            missing.append(pkg)
            print(f"❌ {pkg}")
    
    return missing

def main():
    """主函数"""
    print("🚀 AI批改系统启动中...")
    print("="*40)
    
    # 设置环境
    setup_environment()
    
    # 检查依赖
    print("检查依赖包...")
    missing = check_dependencies()
    
    if missing:
        print(f"\n❌ 缺少依赖: {', '.join(missing)}")
        print("请运行: pip install streamlit Pillow openai PyMuPDF")
        return
    
    print("\n✅ 所有依赖检查通过")
    print("="*40)
    
    # 创建必要目录
    Path("temp_uploads").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    print("🌐 启动Web应用...")
    print("📍 访问地址: http://localhost:8501")
    print("💡 配置API密钥后即可使用")
    print("="*40)
    
    # 启动Streamlit，抑制错误输出
    try:
        # Windows下抑制错误输出的方法
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            subprocess.run([
                sys.executable, "-m", "streamlit", "run", 
                "streamlit_simple.py",
                "--server.port", "8501",
                "--server.address", "localhost",
                "--browser.gatherUsageStats", "false",
                "--logger.level", "error"
            ], startupinfo=startupinfo, stderr=subprocess.DEVNULL)
        else:
            # Unix/Linux/Mac
            subprocess.run([
                sys.executable, "-m", "streamlit", "run", 
                "streamlit_simple.py",
                "--server.port", "8501", 
                "--server.address", "localhost",
                "--browser.gatherUsageStats", "false",
                "--logger.level", "error"
            ], stderr=subprocess.DEVNULL)
            
    except KeyboardInterrupt:
        print("\n\n✋ 应用已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {str(e)}")

if __name__ == "__main__":
    main() 