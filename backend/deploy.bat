@echo off
echo 🚀 开始部署AI教育平台到Railway...

REM 检查Railway CLI是否已安装
railway --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Railway CLI未安装，请先安装：
    echo npm install -g @railway/cli
    pause
    exit /b 1
)

REM 检查是否已登录Railway
railway whoami >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 📝 请先登录Railway...
    railway login --browserless
    echo 请访问上面显示的链接完成登录，然后按任意键继续...
    pause
)

REM 创建新项目或链接现有项目
echo 🔗 创建或链接Railway项目...
if not exist ".railway" (
    echo 创建新项目...
    railway create ai-education-backend
) else (
    echo 项目已存在，继续部署...
)

REM 添加PostgreSQL数据库
echo 📊 添加PostgreSQL数据库...
railway add postgresql

REM 添加Redis缓存  
echo 🗄️ 添加Redis缓存...
railway add redis

REM 设置环境变量
echo ⚙️ 配置环境变量...
railway variables set ENVIRONMENT=production
railway variables set DEBUG=false
railway variables set LOG_LEVEL=INFO
railway variables set HOST=0.0.0.0
railway variables set PORT=8000

echo.
echo 🔑 请手动设置以下环境变量：
echo 1. SECRET_KEY - 应用密钥
echo 2. JWT_SECRET_KEY - JWT密钥  
echo 3. OPENAI_API_KEY - OpenRouter API密钥
echo 4. Firebase Auth相关配置
echo.
echo 使用命令: railway variables set KEY=value
echo.
echo 按任意键继续部署...
pause

REM 部署应用
echo 🚢 开始部署...
railway deploy

echo ✅ 部署完成！
echo 🌐 请访问Railway控制台查看应用URL
pause