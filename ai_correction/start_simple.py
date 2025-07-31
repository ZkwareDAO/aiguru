#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI批改系统简化启动脚本
避免session state的undefined问题
"""

import os
import sys
import subprocess
import platform

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"✓ Python版本: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        return False
    return True

def check_dependencies():
    """检查必要的依赖包"""
    required_packages = {
        'streamlit': 'streamlit',
        'PIL': 'Pillow',
        'openai': 'openai',
        'requests': 'requests',
        'docx': 'python-docx'
    }
    
    missing_packages = []
    
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"❌ {package} 未安装")
            missing_packages.append(package)
    
    return missing_packages

def install_packages(packages):
    """安装缺失的包"""
    if not packages:
        return True
    
    print("\n正在安装缺失的依赖包...")
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ 成功安装 {package}")
        except subprocess.CalledProcessError:
            print(f"❌ 安装 {package} 失败")
            return False
    return True

def create_temp_dirs():
    """创建必要的临时目录"""
    dirs = ['temp_uploads', 'logs', 'uploads']
    for dir_name in dirs:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"✓ 创建目录: {dir_name}")

def check_api_config():
    """检查API配置"""
    print("\n检查API配置...")
    print("⚠️  请确保在应用中配置了有效的SiliconFlow API密钥")
    print("💡 访问 https://siliconflow.cn 获取API密钥")

def clear_streamlit_cache():
    """清理Streamlit缓存"""
    try:
        import streamlit as st
        # 清理所有缓存
        st.cache_data.clear()
        st.cache_resource.clear()
        print("✓ Streamlit缓存已清理")
    except:
        print("⚠️ 无法清理Streamlit缓存")

def main():
    """主函数"""
    print("="*50)
    print("AI批改系统启动检查")
    print("="*50)
    
    # 检查Python版本
    if not check_python_version():
        sys.exit(1)
    
    # 检查依赖
    print("\n检查依赖包...")
    missing = check_dependencies()
    
    if missing:
        print(f"\n发现 {len(missing)} 个缺失的依赖包")
        response = input("是否自动安装? (y/n): ")
        if response.lower() == 'y':
            if not install_packages(missing):
                print("\n❌ 依赖安装失败，请手动安装后重试")
                sys.exit(1)
        else:
            print("\n请手动安装以下包:")
            for pkg in missing:
                print(f"  pip install {pkg}")
            sys.exit(1)
    
    # 创建必要目录
    print("\n准备工作目录...")
    create_temp_dirs()
    
    # 检查API配置
    check_api_config()
    
    # 清理缓存
    clear_streamlit_cache()
    
    # 启动应用
    print("\n"+"="*50)
    print("✅ 所有检查通过，正在启动应用...")
    print("="*50+"\n")
    
    # 设置环境变量
    os.environ['STREAMLIT_THEME_BASE'] = 'dark'
    os.environ['STREAMLIT_SERVER_MAX_UPLOAD_SIZE'] = '200'
    
    # 启动Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "streamlit_simple.py",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false",
            "--server.maxUploadSize", "200"
        ])
    except KeyboardInterrupt:
        print("\n\n✋ 应用已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 