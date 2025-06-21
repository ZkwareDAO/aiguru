@echo off
echo ===================================
echo   AI智能批改系统 - 后端服务启动
echo ===================================
echo.

echo [1/4] 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python未安装或未添加到PATH
    echo 请安装Python 3.8+并添加到系统PATH
    pause
    exit /b 1
)

echo [2/4] 检查项目文件...
if not exist "main.py" (
    echo ❌ main.py文件不存在
    echo 请确保在正确的项目目录中运行此脚本
    pause
    exit /b 1
)

echo [3/4] 检查端口8001...
netstat -an | findstr :8001 > nul
if %errorlevel% equ 0 (
    echo ⚠️  端口8001已被占用
    echo 尝试终止占用进程...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001') do (
        taskkill /pid %%a /f > nul 2>&1
    )
)

echo [4/4] 启动后端服务...
echo.
echo 🚀 正在启动FastAPI服务器...
echo 📝 服务地址: http://localhost:8001
echo 🔍 健康检查: http://localhost:8001/health
echo 🌐 前端地址: http://localhost:3000/auth
echo.
echo 💡 测试账户信息:
echo    用户名: testuser
echo    密码: 123456
echo.
echo ⚠️  按 Ctrl+C 停止服务
echo.

python main.py

echo.
echo 服务已停止
pause 