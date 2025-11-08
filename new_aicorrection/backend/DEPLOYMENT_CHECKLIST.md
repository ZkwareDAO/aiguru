# LangGraph AI 批改系统部署检查清单

## 部署前检查

### 1. 依赖安装 ✅

确保所有依赖已安装：

```bash
cd new_aicorrection/backend
pip install -r requirements.txt
```

关键依赖：
- ✅ `langgraph>=0.0.40`
- ✅ `langchain>=0.1.0`
- ✅ `langchain-openai>=0.0.5`
- ✅ `langchain-community>=0.0.20`
- ✅ `paddleocr>=2.7.0` (可选，用于 OCR)
- ✅ `paddlepaddle>=2.5.0` (可选，用于 OCR)

### 2. 环境变量配置

创建 `.env` 文件并配置以下变量：

```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# AI 模型 API 密钥
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
GEMINI_API_KEY=...

# OCR 配置
OCR_ENGINE=paddleocr  # 或 ocrspace
OCR_SPACE_API_KEY=K81037081488957  # 如果使用 OCR.space

# Firebase Auth
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=path/to/credentials.json

# Redis (可选，用于任务队列)
REDIS_URL=redis://localhost:6379/0

# 应用配置
DEBUG=false
ALLOWED_HOSTS=["your-domain.com"]
CORS_ORIGINS=["https://your-frontend.com"]
```

### 3. 数据库迁移

确保数据库表已创建：

```bash
# 运行数据库迁移
alembic upgrade head

# 或者使用 SQLAlchemy 创建表
python -c "from app.core.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"
```

### 4. 文件结构检查

确保以下文件存在：

```
new_aicorrection/backend/
├── app/
│   ├── api/
│   │   ├── langgraph_grading.py ✅
│   │   └── v1/
│   │       └── router.py ✅ (已更新)
│   ├── services/
│   │   ├── langgraph_state.py ✅
│   │   ├── langgraph_grading_workflow.py ✅
│   │   └── langgraph_nodes/
│   │       ├── __init__.py ✅
│   │       ├── upload_validator.py ✅
│   │       ├── document_ingestor.py ✅
│   │       ├── rubric_interpreter.py ✅
│   │       ├── scoring_agent.py ✅
│   │       └── result_assembler.py ✅
│   ├── models/
│   │   └── ai.py (确保有 GradingTask 模型)
│   └── main.py ✅
├── requirements.txt ✅ (已更新)
├── LANGGRAPH_IMPLEMENTATION.md ✅
└── test_langgraph_workflow.py ✅
```

## Railway 部署步骤

### 1. 连接 GitHub 仓库

1. 登录 Railway: https://railway.app
2. 创建新项目
3. 连接 GitHub 仓库
4. 选择 `new_aicorrection/backend` 目录

### 2. 配置环境变量

在 Railway 项目设置中添加所有环境变量（参考上面的 `.env` 配置）

### 3. 配置数据库

1. 在 Railway 中添加 PostgreSQL 插件
2. 复制 `DATABASE_URL` 到环境变量
3. 运行数据库迁移

### 4. 配置构建命令

Railway 会自动检测 Python 项目，但可以手动配置：

**Build Command**:
```bash
pip install -r requirements.txt
```

**Start Command**:
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 5. 部署

点击 "Deploy" 按钮，Railway 会自动构建和部署应用。

## 部署后验证

### 1. 健康检查

```bash
curl https://your-app.railway.app/health
```

预期响应：
```json
{
  "status": "healthy",
  "service": "ai-education-backend",
  "version": "0.1.0"
}
```

### 2. API 文档

访问 Swagger UI（仅在 DEBUG 模式下）：
```
https://your-app.railway.app/docs
```

### 3. 测试 LangGraph 端点

```bash
# 创建批改任务
curl -X POST https://your-app.railway.app/api/v1/langgraph/grading/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "answer_files": ["path/to/answer.jpg"],
    "max_score": 100
  }'
```

### 4. 查看日志

在 Railway 控制台查看应用日志，确保没有错误。

## 性能测试

### 1. 单个任务测试

```bash
python test_langgraph_workflow.py workflow
```

### 2. 流式处理测试

```bash
python test_langgraph_workflow.py streaming
```

### 3. 节点单元测试

```bash
python test_langgraph_workflow.py nodes
```

## 监控和维护

### 1. 日志监控

- 检查 Railway 日志面板
- 设置日志告警
- 监控错误率

### 2. 性能指标

关键指标：
- 平均响应时间: < 30 秒
- 成功率: > 95%
- OCR 准确率: > 90%
- 数据库连接池使用率: < 80%

### 3. 定期维护

- 每周检查日志
- 每月更新依赖
- 定期备份数据库
- 监控存储空间

## 故障排查

### 问题 1: 导入错误

**症状**: `ModuleNotFoundError: No module named 'langgraph'`

**解决方案**:
```bash
pip install langgraph langchain langchain-openai langchain-community
```

### 问题 2: 数据库连接失败

**症状**: `sqlalchemy.exc.OperationalError`

**解决方案**:
1. 检查 `DATABASE_URL` 格式
2. 确保数据库服务运行中
3. 验证网络连接

### 问题 3: OCR 失败

**症状**: `PaddleOCR initialization failed`

**解决方案**:
1. 检查 PaddleOCR 安装
2. 使用备用 OCR 引擎 (OCR.space)
3. 验证图像格式和大小

### 问题 4: AI API 超时

**症状**: `TimeoutError` 或 `APIError`

**解决方案**:
1. 检查 API 密钥
2. 增加超时时间
3. 使用更快的模型
4. 检查网络连接

### 问题 5: 内存不足

**症状**: `MemoryError` 或应用崩溃

**解决方案**:
1. 增加 Railway 实例内存
2. 优化图像处理（降低分辨率）
3. 限制并发任务数
4. 使用流式处理

## 安全检查

- ✅ 所有 API 端点都需要认证
- ✅ 文件上传大小限制
- ✅ 输入验证和清理
- ✅ CORS 配置正确
- ✅ 敏感信息使用环境变量
- ✅ HTTPS 强制使用

## 备份策略

### 数据库备份

```bash
# 每日自动备份
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### 文件备份

- 上传的文件存储在对象存储（MinIO/S3）
- 配置自动备份策略
- 定期测试恢复流程

## 扩展性考虑

### 水平扩展

- 使用 Redis 作为共享状态存储
- 配置负载均衡
- 使用消息队列（Celery/RabbitMQ）

### 垂直扩展

- 增加 CPU 和内存
- 优化数据库查询
- 使用缓存（Redis）

## 下一步

- [ ] 配置 CI/CD 流水线
- [ ] 设置监控告警（Sentry/DataDog）
- [ ] 实现自动化测试
- [ ] 配置 CDN 加速
- [ ] 实现 API 限流
- [ ] 添加性能分析工具

## 联系支持

如有问题，请查看：
- 项目文档: `LANGGRAPH_IMPLEMENTATION.md`
- GitHub Issues
- Railway 支持文档

