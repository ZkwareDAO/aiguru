#!/bin/bash

echo "🚀 AI教育平台2.0 - 快速部署脚本"
echo "=================================="

# 检查Railway CLI是否已安装
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI未安装，请先安装: https://docs.railway.com/guides/cli"
    exit 1
fi

# 检查是否已登录
echo "1️⃣ 检查Railway登录状态..."
railway whoami || {
    echo "❌ 未登录Railway，请先运行: railway login"
    exit 1
}

# 检查项目连接
echo "2️⃣ 检查项目连接..."
railway status

# 创建后端应用服务
echo "3️⃣ 创建后端应用服务..."
cd backend
railway add --service backend-app --repo https://github.com/QWERTYjc/aiguru2.0.git

# 设置环境变量（用户需要提供API密钥）
echo "4️⃣ 设置后端环境变量..."
echo "请在Railway控制台中手动设置以下环境变量："
echo "DATABASE_URL=postgresql://postgres:sfraebGPmjkZtWpAsHqeHrxUrxuDSQFz@postgres.railway.internal:5432/railway"
echo "REDIS_URL=redis://default:fXZjFSKZfAfkTiqBfomlFHzcddmZZLLv@redis.railway.internal:6379"
echo "OPENROUTER_API_KEY=<你的OpenRouter API密钥>"
echo "SECRET_KEY=<生成的JWT密钥>"

# 部署后端
echo "5️⃣ 部署后端应用..."
railway up

# 创建前端服务
echo "6️⃣ 创建前端应用服务..."
cd ../frontend
railway add --service frontend-app --repo https://github.com/QWERTYjc/aiguru2.0.git

# 部署前端
echo "7️⃣ 部署前端应用..."
railway up

# 获取服务URL
echo "8️⃣ 获取应用访问地址..."
cd ..
railway status

echo "✅ 部署完成！"
echo "📝 请查看 DEPLOYMENT_STATUS.md 了解详细配置信息"
echo "🌐 访问Railway控制台完成最终配置: https://railway.com/project/9ecbe5a8-9ed5-4c8d-b28f-65eb8dd9f74c"