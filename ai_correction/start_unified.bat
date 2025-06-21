@echo off
chcp 65001 >nul
title AI智能批改系统 - 统一启动器

echo.
echo ╔══════════════════════════════════════╗
echo ║        AI智能批改系统 v1.0         ║
echo ║          统一启动器                ║
echo ╚══════════════════════════════════════╝
echo.

REM 清理可能的端口占用
echo 🧹 清理旧的服务进程...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
netstat -ano | findstr :8000 >nul && (
    echo 发现端口8000被占用，正在清理...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do taskkill /F /PID %%a 2>nul
)
netstat -ano | findstr :3000 >nul && (
    echo 发现端口3000被占用，正在清理...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do taskkill /F /PID %%a 2>nul
)
timeout /t 3 /nobreak >nul

echo ✅ 进程清理完成
echo.

REM 检查依赖
echo 🔍 检查系统依赖...

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或未添加到PATH
    echo 请先安装Python 3.8+并添加到系统PATH
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js未安装或未添加到PATH
    echo 请先安装Node.js 18+并添加到系统PATH
    pause
    exit /b 1
)

REM 检查Python依赖
echo 📦 检查Python依赖...
python -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  FastAPI/uvicorn未安装，正在安装...
    pip install fastapi uvicorn[standard] python-multipart python-jose[cryptography] passlib[bcrypt]
    if errorlevel 1 (
        echo ❌ Python依赖安装失败
        pause
        exit /b 1
    )
)

echo ✅ 系统依赖检查完成
echo.

REM 检查前端依赖
echo 📦 检查前端依赖...
if not exist "frontend\node_modules" (
    echo 正在安装前端依赖...
    pushd frontend
    npm install
    if errorlevel 1 (
        echo ❌ 前端依赖安装失败
        popd
        pause
        exit /b 1
    )
    popd
    echo ✅ 前端依赖安装完成
) else (
    echo ✅ 前端依赖已存在
)
echo.

REM 创建必要目录
echo 📁 创建必要目录...
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs
if not exist "user_data" mkdir user_data
echo ✅ 目录结构已准备
echo.

REM 启动后端服务 - 使用app.py作为主服务文件
echo 🚀 启动后端服务 (FastAPI)...
start "AI批改系统-后端API" cmd /k "title 后端API服务 - 端口8000 && echo 启动后端服务... && python app.py"

echo 🔄 等待后端服务启动...
timeout /t 8 /nobreak >nul

REM 健康检查后端 - 多次尝试
echo 🏥 检查后端服务健康状态...
set backend_ready=0
for /l %%i in (1,1,5) do (
    curl -s http://localhost:8000/health >nul 2>&1
    if not errorlevel 1 (
        set backend_ready=1
        goto backend_ok
    )
    echo 尝试 %%i/5: 后端服务尚未就绪，继续等待...
    timeout /t 3 /nobreak >nul
)

:backend_ok
if %backend_ready%==0 (
    echo ❌ 后端服务启动失败或超时
    echo 请检查：
    echo   1. 端口8000是否被其他程序占用
    echo   2. Python依赖是否正确安装
    echo   3. 后端服务窗口是否有错误信息
    pause
    exit /b 1
)
echo ✅ 后端服务运行正常

REM 启动前端服务
echo.
echo 🎨 启动前端服务 (Next.js)...
start "AI批改系统-前端应用" cmd /k "title 前端应用服务 - 端口3000 && cd frontend && echo 启动前端服务... && npm run dev"

echo 🔄 等待前端服务启动...
timeout /t 12 /nobreak >nul

REM 检查前端服务 - 多次尝试
echo 🏥 检查前端服务状态...
set frontend_ready=0
for /l %%i in (1,1,3) do (
    curl -s http://localhost:3000 >nul 2>&1
    if not errorlevel 1 (
        set frontend_ready=1
        goto frontend_ok
    )
    echo 尝试 %%i/3: 前端服务编译中，请稍候...
    timeout /t 5 /nobreak >nul
)

:frontend_ok
if %frontend_ready%==0 (
    echo ⚠️  前端服务可能仍在编译中，这是正常的
    echo 请稍后手动访问 http://localhost:3000
)

echo.
echo ╔══════════════════════════════════════╗
echo ║           🎉 启动完成！             ║
echo ╚══════════════════════════════════════╝
echo.
echo 📋 服务地址:
echo   🔗 前端应用: http://localhost:3000
echo   🔗 后端API:  http://localhost:8000
echo   🔗 API文档:  http://localhost:8000/docs
echo.
echo 🔑 测试账户:
echo   👤 用户名: test_user_1
echo   🔐 密码:   password1
echo.
echo 📊 服务状态监控:
echo   🟢 后端状态: http://localhost:8000/api/system/status
echo   🟢 健康检查: http://localhost:8000/health
echo.
echo ⚡ 热重载功能已启用
echo   • 后端代码修改会自动重启 (app.py)
echo   • 前端代码修改会自动更新
echo.
echo 💡 使用说明:
echo   1. 首次访问前端需要等待Next.js编译完成
echo   2. 可以同时打开多个浏览器标签页
echo   3. 所有数据会保存在本地JSON文件中
echo   4. 上传的文件保存在uploads目录
echo.
echo 🔧 故障排除:
echo   • 后端问题: 检查后端服务窗口的错误信息
echo   • 前端问题: 检查前端服务窗口的编译状态
echo   • 端口占用: 重新运行此启动器会自动清理
echo   • 依赖问题: 删除node_modules重新安装
echo.
echo 🛑 关闭服务:
echo   • 关闭此窗口或按Ctrl+C
echo   • 或者手动关闭后端/前端服务窗口
echo.

REM 等待用户输入或自动打开浏览器
echo 按任意键打开浏览器，或直接关闭此窗口...
pause >nul

REM 自动打开浏览器
echo 🌐 正在打开浏览器...
start http://localhost:3000

echo.
echo 浏览器已打开，享受使用吧！
echo.
echo 💻 开发提示:
echo   • 后端日志: 查看后端服务窗口
echo   • 前端日志: 查看前端服务窗口  
echo   • 系统日志: logs/app_debug.log
echo.
echo 按任意键关闭此启动器窗口...
pause >nul 