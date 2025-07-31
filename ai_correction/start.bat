@echo off
chcp 65001 >nul
echo ================================================
echo AI智能批改系统启动器
echo ================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.8+
    echo 💡 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✓ Python已安装
echo.

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo ✓ 发现虚拟环境，正在激活...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo ✓ 发现虚拟环境，正在激活...
    call .venv\Scripts\activate.bat
) else (
    echo ⚠️ 未发现虚拟环境，使用系统Python
)

echo.

REM 安装依赖
echo 📦 检查并安装依赖包...
pip install -r requirements.txt --quiet

echo.

REM 创建必要目录
if not exist "temp_uploads" mkdir temp_uploads
if not exist "logs" mkdir logs
if not exist "uploads" mkdir uploads

echo ✓ 目录结构检查完成
echo.

REM 检查API配置
if not exist ".env" (
    echo ⚠️ 未发现.env配置文件
    echo 💡 请复制config_template.env为.env并配置API密钥
    echo 🔗 获取API密钥: https://openrouter.ai/keys
    echo.
)

echo 🚀 正在启动AI批改系统...
echo 📍 访问地址: http://localhost:8501
echo.
echo 按 Ctrl+C 停止服务
echo ================================================

REM 启动应用
python start_simple.py

pause 