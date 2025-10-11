# AI教育平台部署指南

## 🎯 部署概述

本文档将指导您将AI教育平台部署到Railway云平台，包括PostgreSQL数据库、Redis缓存和后端API服务的完整配置。

## 📋 准备工作

### 1. 账户准备
- [x] Railway账户 (https://railway.app)
- [x] GitHub账户  
- [x] OpenRouter API密钥 (https://openrouter.ai)
- [x] Firebase项目 (https://console.firebase.google.com)

### 2. 本地工具
- [x] Railway CLI
- [x] Node.js 18+
- [x] Python 3.11+

## 🚀 自动部署（推荐）

### Windows系统
```bash
cd backend
./deploy.bat
```

### Linux/MacOS系统  
```bash
cd backend
chmod +x deploy.sh
./deploy.sh
```

## 🔧 手动部署步骤

### 1. 安装Railway CLI
```bash
npm install -g @railway/cli
```

### 2. 登录Railway
```bash
railway login --browserless
# 访问显示的链接完成登录
```

### 3. 创建项目
```bash
cd backend
railway create ai-education-backend
```

### 4. 添加数据库服务
```bash
# 添加PostgreSQL
railway add postgresql

# 添加Redis
railway add redis
```

### 5. 配置环境变量

#### 基础配置
```bash
railway variables set ENVIRONMENT=production
railway variables set DEBUG=false
railway variables set LOG_LEVEL=INFO
railway variables set HOST=0.0.0.0
railway variables set PORT=8000
```

#### 安全配置
```bash
# 生成密钥：python -c "import secrets; print(secrets.token_urlsafe(32))"
railway variables set SECRET_KEY="your-generated-secret-key"
railway variables set JWT_SECRET_KEY="your-generated-jwt-key"
railway variables set JWT_ALGORITHM=HS256
railway variables set JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
railway variables set JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

#### AI服务配置
```bash
railway variables set OPENAI_API_KEY="your-openrouter-api-key"
railway variables set AI_GRADING_API_URL="https://openrouter.ai/api/v1"
```

#### CORS配置
```bash
railway variables set CORS_ORIGINS="https://your-frontend-domain.vercel.app,http://localhost:3000"
railway variables set ALLOWED_HOSTS="your-domain.railway.app,localhost,127.0.0.1"
```

#### Firebase Auth配置
```bash
railway variables set FIREBASE_PROJECT_ID="your-firebase-project-id"
railway variables set FIREBASE_PRIVATE_KEY_ID="your-firebase-private-key-id"
railway variables set FIREBASE_PRIVATE_KEY="your-firebase-private-key"
railway variables set FIREBASE_CLIENT_EMAIL="your-firebase-client-email"
railway variables set FIREBASE_CLIENT_ID="your-firebase-client-id"
```

### 6. 部署应用
```bash
railway deploy
```

### 7. 数据库初始化
```bash
# 连接到Railway数据库运行迁移
railway connect postgresql
# 或使用数据库URL
alembic upgrade head
```

## 🔗 前端部署（Vercel推荐）

### 1. 连接GitHub仓库
- 登录Vercel控制台
- 导入GitHub仓库
- 选择 `frontend` 目录

### 2. 环境变量配置
```bash
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
NEXT_PUBLIC_WS_URL=wss://your-backend.railway.app
NEXT_PUBLIC_APP_NAME="AI教育平台"
```

### 3. 构建配置
Framework Preset: Next.js
Build Command: `npm run build`
Output Directory: `.next`
Install Command: `npm install`

## ⚙️ 环境变量详细说明

### 必需环境变量
| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| SECRET_KEY | 应用密钥 | 32字符随机字符串 |
| JWT_SECRET_KEY | JWT密钥 | 32字符随机字符串 |
| OPENAI_API_KEY | OpenRouter API密钥 | sk-or-v1-xxx |
| DATABASE_URL | 数据库连接（自动生成） | postgresql://... |
| REDIS_URL | Redis连接（自动生成） | redis://... |

### 可选环境变量
| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| LOG_LEVEL | 日志级别 | INFO |
| CORS_ORIGINS | 允许的前端域名 | * |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | Token过期时间 | 30 |

## 🧪 部署验证

### 1. 健康检查
```bash
curl https://your-app.railway.app/health
```

### 2. API文档
访问: https://your-app.railway.app/docs

### 3. 数据库连接测试
```bash
railway connect postgresql
\dt  # 列出表
```

### 4. 功能测试
- [ ] 用户注册/登录
- [ ] 班级创建
- [ ] 作业上传
- [ ] AI批改功能
- [ ] 坐标标注显示
- [ ] 局部图卡片显示

## 📊 监控和维护

### 1. 查看日志
```bash
railway logs
```

### 2. 监控指标
- CPU使用率
- 内存使用率  
- 数据库连接数
- API响应时间

### 3. 数据备份
```bash
# 创建数据库备份
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# 恢复备份
psql $DATABASE_URL < backup_file.sql
```

## 🔧 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查DATABASE_URL格式
   - 确保PostgreSQL服务运行
   - 验证网络连接

2. **Redis连接失败**
   - 检查REDIS_URL格式
   - 确保Redis服务运行

3. **AI批改失败**
   - 验证OPENAI_API_KEY
   - 检查OpenRouter余额
   - 查看错误日志

4. **CORS错误**
   - 检查CORS_ORIGINS配置
   - 确保前端域名已添加

### 日志查看
```bash
# 实时日志
railway logs --follow

# 特定服务日志
railway logs --service backend

# 错误日志过滤
railway logs | grep ERROR
```

## 📝 部署检查清单

### Railway后端部署
- [ ] Railway CLI已安装
- [ ] 已登录Railway账户
- [ ] 项目已创建
- [ ] PostgreSQL已添加
- [ ] Redis已添加  
- [ ] 环境变量已配置
- [ ] 应用已部署
- [ ] 数据库已初始化
- [ ] 健康检查通过

### 前端部署
- [ ] Vercel项目已创建
- [ ] GitHub仓库已连接
- [ ] 环境变量已配置
- [ ] 构建成功
- [ ] 域名已配置
- [ ] HTTPS已启用

### 功能验证
- [ ] API文档可访问
- [ ] 用户注册登录正常
- [ ] 班级管理功能正常
- [ ] 作业上传功能正常
- [ ] AI批改功能正常
- [ ] 坐标标注显示正常
- [ ] 局部图显示正常
- [ ] 前后端通信正常

## 🎉 部署完成

恭喜！您的AI教育平台已成功部署到Railway。

- **后端API**: https://your-backend.railway.app
- **API文档**: https://your-backend.railway.app/docs  
- **前端应用**: https://your-frontend.vercel.app
- **管理控制台**: https://railway.app/dashboard

## 📞 技术支持

如遇到部署问题，请检查：
1. 环境变量配置
2. 数据库连接状态
3. 应用日志信息
4. Railway服务状态

## 🔄 更新和维护

### 更新代码
```bash
# 推送代码到GitHub
git push origin main

# Railway自动部署
# 或手动触发部署
railway deploy
```

### 数据库迁移
```bash
# 创建迁移
alembic revision --autogenerate -m "migration description"

# 执行迁移
railway run alembic upgrade head
```