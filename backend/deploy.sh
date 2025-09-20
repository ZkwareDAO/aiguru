#!/bin/bash
# Railway部署脚本

echo "🚀 开始部署AI教育平台到Railway..."

# 检查Railway CLI是否已安装
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI未安装，请先安装："
    echo "npm install -g @railway/cli"
    exit 1
fi

# 检查是否已登录Railway
if ! railway whoami &> /dev/null; then
    echo "📝 请先登录Railway..."
    railway login
fi

# 创建新项目或链接现有项目
echo "🔗 创建或链接Railway项目..."
if [ ! -f ".railway/project" ]; then
    echo "创建新项目..."
    railway create
else
    echo "项目已存在，继续部署..."
fi

# 添加PostgreSQL数据库
echo "📊 添加PostgreSQL数据库..."
railway add postgresql

# 添加Redis缓存
echo "🗄️ 添加Redis缓存..."
railway add redis

# 设置环境变量
echo "⚙️ 配置环境变量..."
railway variables set ENVIRONMENT=production
railway variables set DEBUG=false
railway variables set LOG_LEVEL=INFO
railway variables set HOST=0.0.0.0

# 提示用户设置必要的API密钥
echo "🔑 请手动设置以下环境变量："
echo "1. SECRET_KEY - 应用密钥"
echo "2. JWT_SECRET_KEY - JWT密钥"
echo "3. OPENAI_API_KEY - OpenRouter API密钥"
echo "4. Firebase Auth相关配置"
echo ""
echo "使用命令: railway variables set KEY=value"
echo ""

# 部署应用
echo "🚢 开始部署..."
railway deploy

echo "✅ 部署完成！"
echo "🌐 访问你的应用: $(railway status --json | jq -r '.deployments[0].url')"