#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph 依赖安装脚本
自动安装 LangGraph AI 批改系统所需的依赖包
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description=""):
    """运行命令并显示结果"""
    print(f"🔄 {description}")
    print(f"   执行: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(f"✅ {description} 成功")
        if result.stdout:
            print(f"   输出: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败")
        print(f"   错误: {e.stderr.strip()}")
        return False

def check_python_version():
    """检查Python版本"""
    print("🐍 检查Python版本...")
    version = sys.version_info
    print(f"   当前版本: Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python版本过低，需要Python 3.8+")
        return False
    
    print("✅ Python版本符合要求")
    return True

def install_langgraph_dependencies():
    """安装LangGraph相关依赖"""
    print("\n📦 安装LangGraph依赖包...")
    
    dependencies = [
        "langgraph>=0.0.40",
        "langchain-core>=0.1.0",
        "langchain>=0.1.0",
        "langchain-openai>=0.0.5",
        "langchain-community>=0.0.20",
        "pydantic>=2.0.0",
        "typing-extensions>=4.5.0"
    ]
    
    success_count = 0
    for dep in dependencies:
        if run_command(f"pip install {dep}", f"安装 {dep}"):
            success_count += 1
    
    print(f"\n📊 依赖安装结果: {success_count}/{len(dependencies)} 成功")
    return success_count == len(dependencies)

def install_image_processing_dependencies():
    """安装图像处理依赖"""
    print("\n🖼️ 安装图像处理依赖...")
    
    dependencies = [
        "Pillow>=9.0.0",
        "opencv-python>=4.5.0",
        "numpy>=1.21.0"
    ]
    
    success_count = 0
    for dep in dependencies:
        if run_command(f"pip install {dep}", f"安装 {dep}"):
            success_count += 1
    
    print(f"\n📊 图像处理依赖安装结果: {success_count}/{len(dependencies)} 成功")
    return success_count == len(dependencies)

def install_optional_dependencies():
    """安装可选依赖"""
    print("\n🔧 安装可选依赖...")
    
    optional_deps = [
        ("requests>=2.25.0", "HTTP请求库"),
        ("aiohttp>=3.8.0", "异步HTTP库"),
        ("asyncio", "异步IO库（通常内置）")
    ]
    
    success_count = 0
    for dep, desc in optional_deps:
        if "asyncio" in dep:
            # asyncio是内置库，跳过安装
            print(f"✅ {desc} (内置库)")
            success_count += 1
        else:
            if run_command(f"pip install {dep}", f"安装 {desc}"):
                success_count += 1
    
    print(f"\n📊 可选依赖安装结果: {success_count}/{len(optional_deps)} 成功")
    return success_count == len(optional_deps)

def verify_installation():
    """验证安装"""
    print("\n🔍 验证安装...")
    
    test_imports = [
        ("langgraph", "LangGraph核心库"),
        ("langchain_core", "LangChain核心库"),
        ("PIL", "Pillow图像库"),
        ("cv2", "OpenCV库"),
        ("numpy", "NumPy库")
    ]
    
    success_count = 0
    for module, desc in test_imports:
        try:
            __import__(module)
            print(f"✅ {desc} 导入成功")
            success_count += 1
        except ImportError as e:
            print(f"❌ {desc} 导入失败: {e}")
    
    print(f"\n📊 验证结果: {success_count}/{len(test_imports)} 成功")
    return success_count == len(test_imports)

def create_requirements_file():
    """创建requirements文件"""
    print("\n📝 创建requirements文件...")
    
    requirements_content = """# LangGraph AI 批改系统依赖
# 核心依赖
langgraph>=0.0.40
langchain-core>=0.1.0
langchain>=0.1.0
langchain-openai>=0.0.5
langchain-community>=0.0.20

# 数据处理
pydantic>=2.0.0
typing-extensions>=4.5.0
numpy>=1.21.0

# 图像处理
Pillow>=9.0.0
opencv-python>=4.5.0

# HTTP和异步
requests>=2.25.0
aiohttp>=3.8.0

# Streamlit (如果需要)
streamlit>=1.28.0

# 其他工具
pathlib2>=2.3.0
python-dateutil>=2.8.0
"""
    
    requirements_file = Path(__file__).parent / "requirements_langgraph.txt"
    
    try:
        with open(requirements_file, 'w', encoding='utf-8') as f:
            f.write(requirements_content)
        print(f"✅ Requirements文件已创建: {requirements_file}")
        return True
    except Exception as e:
        print(f"❌ 创建Requirements文件失败: {e}")
        return False

def show_next_steps():
    """显示下一步操作"""
    print("\n🎯 下一步操作:")
    print("1. 运行测试脚本:")
    print("   python test_langgraph.py")
    print("\n2. 启动Streamlit应用:")
    print("   streamlit run streamlit_simple.py")
    print("\n3. 在应用中选择 '🧠 LangGraph智能批改' 模式")
    print("\n4. 上传文件并开始批改")
    
    print("\n📚 文档和帮助:")
    print("- LangGraph文档: https://langchain-ai.github.io/langgraph/")
    print("- 项目文档: 查看 ai_correction/functions/langgraph/ 目录")

def main():
    """主安装函数"""
    print("🚀 LangGraph AI 批改系统依赖安装")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        print("\n❌ 安装终止：Python版本不符合要求")
        return False
    
    # 安装依赖
    langgraph_success = install_langgraph_dependencies()
    image_success = install_image_processing_dependencies()
    optional_success = install_optional_dependencies()
    
    # 验证安装
    verify_success = verify_installation()
    
    # 创建requirements文件
    requirements_success = create_requirements_file()
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 安装总结:")
    print(f"   LangGraph依赖: {'✅ 成功' if langgraph_success else '❌ 失败'}")
    print(f"   图像处理依赖: {'✅ 成功' if image_success else '❌ 失败'}")
    print(f"   可选依赖: {'✅ 成功' if optional_success else '❌ 失败'}")
    print(f"   验证测试: {'✅ 成功' if verify_success else '❌ 失败'}")
    print(f"   Requirements文件: {'✅ 成功' if requirements_success else '❌ 失败'}")
    
    overall_success = all([
        langgraph_success, 
        image_success, 
        optional_success, 
        verify_success
    ])
    
    if overall_success:
        print("\n🎉 安装完成！LangGraph AI 批改系统已就绪。")
        show_next_steps()
    else:
        print("\n⚠️ 安装过程中出现问题，请检查错误信息。")
        print("\n🔧 故障排除:")
        print("1. 确保网络连接正常")
        print("2. 尝试升级pip: python -m pip install --upgrade pip")
        print("3. 如果在中国，可以使用国内镜像:")
        print("   pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ <package_name>")
    
    return overall_success

if __name__ == "__main__":
    main()
