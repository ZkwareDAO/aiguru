@echo off
chcp 65001 >nul
title 系统状态检查

echo.
echo ╔══════════════════════════════════════╗
echo ║       AI智能批改系统状态检查        ║
echo ╚══════════════════════════════════════╝
echo.

echo 🔍 检查服务状态...
echo.

REM 检查后端服务
echo 🔧 后端服务 (端口8000):
netstat -an | findstr ":8000.*LISTENING" >nul 2>&1
if errorlevel 1 (
    echo   ❌ 后端服务未运行
    set backend_status=down
) else (
    echo   ✅ 后端服务正在运行
    set backend_status=up
)

REM 检查前端服务
echo 🎨 前端服务 (端口3000):
netstat -an | findstr ":3000.*LISTENING" >nul 2>&1
if errorlevel 1 (
    echo   ❌ 前端服务未运行
    set frontend_status=down
) else (
    echo   ✅ 前端服务正在运行
    set frontend_status=up
)

echo.

REM API健康检查
if "%backend_status%"=="up" (
    echo 🏥 API健康检查:
    curl -s http://localhost:8000/health >nul 2>&1
    if errorlevel 1 (
        echo   ⚠️  后端API响应异常
    ) else (
        echo   ✅ 后端API响应正常
    )
    
    curl -s http://localhost:8000/api/system/status >nul 2>&1
    if errorlevel 1 (
        echo   ⚠️  系统状态API异常
    ) else (
        echo   ✅ 系统状态API正常
    )
)

echo.
echo ╔══════════════════════════════════════╗
echo ║             🎯 访问地址              ║
echo ╚══════════════════════════════════════╝
echo.
if "%frontend_status%"=="up" (
    echo 🌐 前端应用: http://localhost:3000
) else (
    echo 🌐 前端应用: 未运行
)

if "%backend_status%"=="up" (
    echo 🔗 后端API:  http://localhost:8000
    echo 📚 API文档:  http://localhost:8000/docs
    echo 🏥 健康检查: http://localhost:8000/health
    echo 📊 系统状态: http://localhost:8000/api/system/status
) else (
    echo 🔗 后端API:  未运行
)

echo.
echo ╔══════════════════════════════════════╗
echo ║             💡 建议操作              ║
echo ╚══════════════════════════════════════╝
echo.

if "%backend_status%"=="down" if "%frontend_status%"=="down" (
    echo 🚀 两个服务都未运行，建议运行: start_unified.bat
) else if "%backend_status%"=="down" (
    echo 🔧 后端服务未运行，建议运行: start_simple.bat
) else if "%frontend_status%"=="down" (
    echo 🎨 前端服务未运行，建议在前端目录运行: npm run dev
) else (
    echo ✨ 所有服务正常运行！
    echo 👆 按任意键打开浏览器访问应用
    pause >nul
    start http://localhost:3000
    exit /b 0
)

echo.
echo 按任意键关闭...
pause >nul 