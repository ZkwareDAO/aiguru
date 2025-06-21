@echo off
chcp 65001 > nul
echo.
echo ========================================
echo      AI智能批改系统 - 统一启动脚本
echo ========================================
echo.

:: 设置颜色
color 0A

:: 检查是否在正确的目录
if not exist "main.py" (
    echo [错误] 请在项目根目录运行此脚本
    pause
    exit /b 1
)

if not exist "frontend" (
    echo [错误] 未找到frontend目录
    pause
    exit /b 1
)

:: 创建日志目录
if not exist "logs" mkdir logs

:: 记录启动时间
echo [%date% %time%] 系统启动开始 >> logs\startup.log

echo [1/6] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python未安装或未添加到PATH
    echo 请安装Python 3.8+并添加到系统PATH
    pause
    exit /b 1
)

echo [2/6] 检查Node.js环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Node.js未安装或未添加到PATH
    echo 请安装Node.js 18+并添加到系统PATH
    pause
    exit /b 1
)

echo [3/6] 激活Python虚拟环境...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo ✓ 虚拟环境已激活
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo ✓ 虚拟环境已激活
) else (
    echo [警告] 未找到虚拟环境，使用系统Python
)

echo [4/6] 安装Python依赖...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [错误] Python依赖安装失败
    pause
    exit /b 1
)

echo [5/6] 安装前端依赖...
cd frontend
call npm install --silent
if errorlevel 1 (
    echo [错误] 前端依赖安装失败
    cd ..
    pause
    exit /b 1
)
cd ..

echo [6/6] 启动服务...
echo.
echo ========================================
echo            服务启动中...
echo ========================================
echo.

:: 启动后端服务
echo [后端] 启动FastAPI服务 (端口:8001)...
start "AI批改系统-后端" /min cmd /c "python main.py"

:: 等待后端启动
echo [系统] 等待后端服务启动...
timeout /t 3 /nobreak > nul

:: 检查后端是否启动成功
for /L %%i in (1,1,10) do (
    curl -s http://localhost:8001/health > nul 2>&1
    if not errorlevel 1 (
        echo ✓ 后端服务启动成功
        goto backend_ready
    )
    echo [系统] 等待后端服务... (%%i/10)
    timeout /t 2 /nobreak > nul
)

echo [警告] 后端服务可能启动失败，继续启动前端...

:backend_ready
:: 启动前端服务
echo [前端] 启动Next.js服务 (端口:3000)...
cd frontend
start "AI批改系统-前端" cmd /c "npm run dev"
cd ..

:: 等待前端启动
echo [系统] 等待前端服务启动...
timeout /t 5 /nobreak > nul

echo.
echo ========================================
echo            启动完成！
echo ========================================
echo.
echo 🚀 服务访问地址:
echo    前端界面: http://localhost:3000
echo    后端API:  http://localhost:8001
echo    API文档:  http://localhost:8001/docs
echo.
echo 🔐 测试账户:
echo    用户名: testuser
echo    密码:   123456
echo.
echo 📝 操作说明:
echo    1. 前端页面会自动打开
echo    2. 使用测试账户登录
echo    3. 上传文件进行AI批改
echo    4. 查看历史记录和详情
echo.
echo ⚠️  注意事项:
echo    - 请保持此窗口打开
echo    - 关闭此窗口将停止所有服务
echo    - 如遇问题请查看logs目录下的日志
echo.

:: 记录启动完成
echo [%date% %time%] 系统启动完成 >> logs\startup.log

:: 自动打开浏览器
timeout /t 3 /nobreak > nul
echo [系统] 正在打开浏览器...
start http://localhost:3000

:: 保持窗口打开并监控服务
echo [系统] 服务监控中... (按Ctrl+C停止所有服务)
echo.

:monitor_loop
timeout /t 30 /nobreak > nul
curl -s http://localhost:8001/health > nul 2>&1
if errorlevel 1 (
    echo [%time%] [警告] 后端服务异常
) else (
    echo [%time%] [正常] 服务运行正常
)
goto monitor_loop

:: 清理函数
:cleanup
echo.
echo [系统] 正在停止服务...
taskkill /f /im python.exe > nul 2>&1
taskkill /f /im node.exe > nul 2>&1
echo [%date% %time%] 系统停止 >> logs\startup.log
echo [系统] 服务已停止
pause 