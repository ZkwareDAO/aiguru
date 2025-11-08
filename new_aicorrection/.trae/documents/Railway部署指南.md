# AI教育平台Railway部署指南

## 1. 部署概述

本指南将帮助您将AI教育平台部署到Railway云平台，包括后端API服务、PostgreSQL数据库和Redis缓存的完整配置。

### 1.1 部署架构

```mermaid
graph TD
    A[GitHub仓库] --> B[Railway项目]
    B --> C[Web Service - 后端API]
    B --> D[PostgreSQL数据库]
    B --> E[Redis缓存]
    
    F[前端应用] --> G[Vercel/Netlify]
    G --> C
    
    subgraph "Railway环境"
        C
        D
        E
    end
```

## 2. 准备工作

### 2.1 账户准备
- Railway账户 (https://railway.app)
- GitHub账户
- OpenAI API密钥
- AWS S3账户（可选，用于文件存储）

### 2.2 代码准备
确保您的代码已推送到GitHub仓库，并包含以下文件：
- `backend/Dockerfile`
- `backend/requirements.txt`
- `backend/alembic.ini`
- `backend/alembic/versions/`

## 3. Railway后端部署

### 3.1 创建Railway项目

1. **登录Railway控制台**
   - 访问 https://railway.app
   - 使用GitHub账户登录

2. **创建新项目**
   ```bash
   # 点击 "New Project"
   # 选择 "Deploy from GitHub repo"
   # 选择您的AI教育平台仓库
   ```

3. **配置服务**
   - 选择 `backend` 目录作为根目录
   - Railway会自动检测Dockerfile

### 3.2 添加数据库服务

1. **添加PostgreSQL**
   ```bash
   # 在项目中点击 "+ New"
   # 选择 "Database" -> "Add PostgreSQL"
   # Railway会自动创建数据库实例
   ```

2. **添加Redis**
   ```bash
   # 在项目中点击 "+ New"
   # 选择 "Database" -> "Add Redis"
   # Railway会自动创建Redis实例
   ```

### 3.3 环境变量配置

在Railway Web Service中配置以下环境变量：

```bash
# 应用基础配置
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
APP_NAME="AI Education Backend"
HOST=0.0.0.0
PORT=8000

# 安全配置
SECRET_KEY=your-super-secret-production-key-min-32-chars
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 数据库配置（Railway自动提供）
DATABASE_URL=${{Postgres.DATABASE_URL}}
DATABASE_ECHO=false

# Redis配置（Railway自动提供）
REDIS_URL=${{Redis.REDIS_URL}}

# CORS配置
ALLOWED_HOSTS=your-domain.railway.app,localhost,127.0.0.1
CORS_ORIGINS=https://your-frontend-domain.vercel.app,http://localhost:3000

# AI服务配置
OPENAI_API_KEY=sk-your-openai-api-key
AI_GRADING_API_URL=https://api.openai.com/v1

# 文件存储配置（AWS S3）
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_S3_BUCKET=your-s3-bucket-name
AWS_REGION=us-east-1

# 邮件服务配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_USE_TLS=true
```

### 3.4 部署配置

1. **Dockerfile优化**
   确保 `backend/Dockerfile` 包含以下内容：
   ```dockerfile
   FROM python:3.11-slim
   
   ENV PYTHONDONTWRITEBYTECODE=1 \
       PYTHONUNBUFFERED=1 \
       PYTHONPATH=/app
   
   WORKDIR /app
   
   # 安装系统依赖
   RUN apt-get update \
       && apt-get install -y --no-install-recommends \
           gcc \
           libpq-dev \
           curl \
       && rm -rf /var/lib/apt/lists/*
   
   # 安装Python依赖
   COPY requirements.txt .
   RUN pip install --no-cache-dir --upgrade pip \
       && pip install --no-cache-dir -r requirements.txt
   
   # 复制应用代码
   COPY . .
   
   # 创建非root用户
   RUN adduser --disabled-password --gecos '' appuser \
       && chown -R appuser:appuser /app
   USER appuser
   
   # 暴露端口
   EXPOSE 8000
   
   # 健康检查
   HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
       CMD curl -f http://localhost:8000/health || exit 1
   
   # 启动应用
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **数据库迁移**
   在部署后运行数据库迁移：
   ```bash
   # 在Railway控制台中打开终端
   # 或者在本地连接到Railway数据库
   alembic upgrade head
   ```

## 4. 数据库初始化

### 4.1 连接到Railway数据库

1. **获取数据库连接信息**
   - 在Railway PostgreSQL服务中查看连接详情
   - 复制DATABASE_URL

2. **本地连接数据库**
   ```bash
   # 安装PostgreSQL客户端
   pip install psycopg2-binary
   
   # 或使用psql命令行工具
   psql "postgresql://username:password@host:port/database"
   ```

### 4.2 运行数据库迁移

```bash
# 在项目根目录下
cd backend

# 设置数据库URL环境变量
export DATABASE_URL="postgresql://username:password@host:port/database"

# 运行迁移
alembic upgrade head

# 验证表创建
psql $DATABASE_URL -c "\dt"
```

### 4.3 插入初始数据

```sql
-- 创建测试用户
INSERT INTO users (email, password_hash, name, role, school, grade, is_verified) VALUES
('admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3QJflHQrxG', '系统管理员', 'teacher', 'AI教育平台', '管理员', true),
('teacher@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3QJflHQrxG', '张老师', 'teacher', '示例中学', '高三', true),
('student@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3QJflHQrxG', '李同学', 'student', '示例中学', '高三', true);

-- 创建示例班级
INSERT INTO classes (name, description, class_code, school, grade, subject, teacher_id)
SELECT 
    '高三数学1班', 
    '高三数学重点班', 
    'MATH001', 
    '示例中学', 
    '高三', 
    '数学',
    id
FROM users WHERE email = 'teacher@example.com';

-- 添加学生到班级
INSERT INTO class_students (class_id, student_id)
SELECT 
    c.id,
    u.id
FROM classes c, users u
WHERE c.class_code = 'MATH001' AND u.email = 'student@example.com';
```

## 5. 前端部署配置

### 5.1 Vercel部署

1. **连接GitHub仓库**
   - 登录Vercel控制台
   - 导入GitHub仓库
   - 选择 `frontend` 目录

2. **环境变量配置**
   ```bash
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   NEXT_PUBLIC_WS_URL=wss://your-backend.railway.app
   NEXT_PUBLIC_APP_NAME="AI教育平台"
   ```

3. **构建配置**
   ```json
   {
     "buildCommand": "npm run build",
     "outputDirectory": ".next",
     "installCommand": "npm install"
   }
   ```

### 5.2 Netlify部署

1. **部署配置文件** (`netlify.toml`)
   ```toml
   [build]
     command = "npm run build"
     publish = ".next"
   
   [build.environment]
     NEXT_PUBLIC_API_URL = "https://your-backend.railway.app"
     NEXT_PUBLIC_WS_URL = "wss://your-backend.railway.app"
   
   [[redirects]]
     from = "/*"
     to = "/index.html"
     status = 200
   ```

## 6. 域名和SSL配置

### 6.1 自定义域名

1. **Railway域名配置**
   ```bash
   # 在Railway项目设置中
   # 添加自定义域名
   # 配置DNS记录指向Railway
   ```

2. **SSL证书**
   - Railway自动提供Let's Encrypt SSL证书
   - 确保HTTPS重定向已启用

### 6.2 CORS配置更新

更新后端CORS配置以包含新域名：
```python
# app/core/config.py
CORS_ORIGINS = [
    "https://your-custom-domain.com",
    "https://your-frontend.vercel.app",
    "http://localhost:3000"
]
```

## 7. 监控和日志

### 7.1 Railway监控

1. **应用监控**
   - CPU和内存使用情况
   - 请求响应时间
   - 错误率统计

2. **数据库监控**
   - 连接数
   - 查询性能
   - 存储使用情况

### 7.2 日志配置

```python
# app/core/logging.py
import structlog
import logging

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

## 8. 性能优化

### 8.1 数据库优化

```sql
-- 创建必要的索引
CREATE INDEX CONCURRENTLY idx_users_email_active ON users(email) WHERE is_active = true;
CREATE INDEX CONCURRENTLY idx_assignments_class_status ON assignments(class_id, status);
CREATE INDEX CONCURRENTLY idx_submissions_assignment_student ON submissions(assignment_id, student_id);

-- 分析表统计信息
ANALYZE users;
ANALYZE classes;
ANALYZE assignments;
ANALYZE submissions;
```

### 8.2 Redis缓存策略

```python
# app/core/cache.py
from redis import Redis
import json
from typing import Any, Optional

class CacheManager:
    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url)
    
    async def get_class_stats(self, class_id: str) -> Optional[dict]:
        """获取班级统计缓存"""
        cache_key = f"class_stats:{class_id}"
        cached_data = self.redis.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
        return None
    
    async def set_class_stats(self, class_id: str, stats: dict, ttl: int = 300):
        """设置班级统计缓存"""
        cache_key = f"class_stats:{class_id}"
        self.redis.setex(cache_key, ttl, json.dumps(stats))
```

## 9. 安全配置

### 9.1 环境变量安全

```bash
# 生成安全的密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 确保所有密钥都是随机生成的
SECRET_KEY=your-generated-secret-key
JWT_SECRET_KEY=your-generated-jwt-key
```

### 9.2 API安全

```python
# app/core/middleware.py
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# 速率限制
limiter = Limiter(key_func=get_remote_address)

# 应用到路由
@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    pass
```

## 10. 故障排除

### 10.1 常见问题

1. **数据库连接失败**
   ```bash
   # 检查DATABASE_URL格式
   # 确保数据库服务正在运行
   # 验证网络连接
   ```

2. **Redis连接失败**
   ```bash
   # 检查REDIS_URL格式
   # 确保Redis服务正在运行
   # 验证连接参数
   ```

3. **CORS错误**
   ```python
   # 检查CORS_ORIGINS配置
   # 确保前端域名已添加
   # 验证协议（HTTP/HTTPS）
   ```

### 10.2 调试工具

```bash
# Railway CLI安装
npm install -g @railway/cli

# 登录Railway
railway login

# 查看日志
railway logs

# 连接到服务
railway shell
```

## 11. 备份和恢复

### 11.1 数据库备份

```bash
# 创建备份
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复备份
psql $DATABASE_URL < backup_file.sql
```

### 11.2 自动备份脚本

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="ai_education_backup_$DATE.sql"

# 创建备份
pg_dump $DATABASE_URL > $BACKUP_FILE

# 上传到S3（可选）
aws s3 cp $BACKUP_FILE s3://your-backup-bucket/

# 清理本地文件
rm $BACKUP_FILE

echo "Backup completed: $BACKUP_FILE"
```

## 12. 部署检查清单

- [ ] Railway项目创建完成
- [ ] PostgreSQL数据库已添加
- [ ] Redis缓存已添加
- [ ] 所有环境变量已配置
- [ ] 数据库迁移已运行
- [ ] 初始数据已插入
- [ ] 前端已部署到Vercel/Netlify
- [ ] 自定义域名已配置
- [ ] SSL证书已启用
- [ ] CORS配置已更新
- [ ] 监控和日志已配置
- [ ] 备份策略已实施
- [ ] 安全配置已完成
- [ ] 性能优化已实施
- [ ] 功能测试已通过

完成以上步骤后，您的AI教育平台将成功部署到Railway云平台，可以开始为用户提供服务。