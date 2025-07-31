@echo off
echo ========================================
echo 🚀 使用Python 3.13.5运行AI批改系统
echo ========================================

echo 设置Python 3.13环境...
set PYTHON_PATH=C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe

echo 验证Python版本...
%PYTHON_PATH% --version

echo 验证必要库...
%PYTHON_PATH% -c "from openai import OpenAI; import fitz; import pypdfium2; print('✅ 所有库验证成功')"

echo.
echo 选择运行模式:
echo 1. 运行PDF处理测试
echo 2. 运行批改功能测试  
echo 3. 启动Streamlit批改系统
echo 4. 退出

set /p choice=请输入选择 (1-4): 

if "%choice%"=="1" (
    echo 🔍 运行PDF处理测试...
    %PYTHON_PATH% test_pdf_processing.py
    pause
) else if "%choice%"=="2" (
    echo 📝 运行批改功能测试...
    %PYTHON_PATH% test_grading_function.py
    pause
) else if "%choice%"=="3" (
    echo 🌐 启动Streamlit批改系统...
    %PYTHON_PATH% -m streamlit run streamlit_simple.py
) else if "%choice%"=="4" (
    echo 👋 再见!
    exit
) else (
    echo ❌ 无效选择，请重新运行脚本
    pause
)