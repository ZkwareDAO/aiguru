@echo off
echo 正在部署AI教育平台2.0到Railway...

echo 1. 检查Railway登录状态
railway whoami

echo 2. 检查项目状态
railway status

echo 3. 创建后端服务
cd backend
railway add --service backend-app
if %errorlevel% neq 0 (
    echo 后端服务创建失败，尝试直接部署
    railway up
) else (
    echo 后端服务创建成功，开始部署
    railway up --service backend-app
)

echo 4. 返回根目录并创建前端服务
cd ..
cd frontend
railway add --service frontend-app
if %errorlevel% neq 0 (
    echo 前端服务创建失败，尝试直接部署
    railway up
) else (
    echo 前端服务创建成功，开始部署
    railway up --service frontend-app
)

echo 5. 返回根目录
cd ..

echo 部署完成！请检查Railway控制台确认服务状态。

pause