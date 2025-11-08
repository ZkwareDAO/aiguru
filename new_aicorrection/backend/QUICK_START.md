# LangGraph AI 批改系统快速开始指南

## 🚀 5 分钟快速部署

### 步骤 1: 安装依赖

```bash
cd new_aicorrection/backend
pip install -r requirements.txt
```

### 步骤 2: 配置环境变量

创建 `.env` 文件：

```bash
# 最小配置
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/aiguru
OPENAI_API_KEY=sk-your-key-here

# 可选配置
OCR_ENGINE=paddleocr
DEBUG=true
```

### 步骤 3: 初始化数据库

```bash
# 使用 Alembic
alembic upgrade head

# 或者直接创建表
python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

### 步骤 4: 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 步骤 5: 测试 API

访问 http://localhost:8000/docs 查看 API 文档

## 📝 快速测试

### 使用 curl 测试

```bash
# 1. 健康检查
curl http://localhost:8000/health

# 2. 创建批改任务（需要先登录获取 token）
curl -X POST http://localhost:8000/api/v1/langgraph/grading/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "answer_files": ["path/to/answer.jpg"],
    "question_files": ["path/to/question.jpg"],
    "max_score": 100,
    "strictness_level": "中等"
  }'

# 3. 查询任务状态
curl http://localhost:8000/api/v1/langgraph/grading/tasks/TASK_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 使用 Python 测试

```python
import requests

# 创建任务
response = requests.post(
    "http://localhost:8000/api/v1/langgraph/grading/tasks",
    json={
        "answer_files": ["test.jpg"],
        "max_score": 100
    },
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

print(response.json())
```

### 使用测试脚本

```bash
# 测试完整工作流
python test_langgraph_workflow.py workflow

# 测试流式处理
python test_langgraph_workflow.py streaming

# 测试单个节点
python test_langgraph_workflow.py nodes
```

## 🌐 Railway 部署

### 方法 1: 使用 Railway CLI

```bash
# 安装 Railway CLI
npm i -g @railway/cli

# 登录
railway login

# 初始化项目
railway init

# 链接到现有项目或创建新项目
railway link

# 添加环境变量
railway variables set DATABASE_URL="postgresql://..."
railway variables set OPENAI_API_KEY="sk-..."

# 部署
railway up
```

### 方法 2: 使用 Railway Web UI

1. 访问 https://railway.app
2. 点击 "New Project"
3. 选择 "Deploy from GitHub repo"
4. 选择你的仓库和分支
5. 设置根目录为 `new_aicorrection/backend`
6. 添加环境变量
7. 点击 "Deploy"

### Railway 环境变量配置

在 Railway 项目设置中添加：

```
DATABASE_URL=postgresql://...  (Railway 自动提供)
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
GEMINI_API_KEY=...
OCR_SPACE_API_KEY=K81037081488957
FIREBASE_PROJECT_ID=your-project
DEBUG=false
ALLOWED_HOSTS=["your-app.railway.app"]
CORS_ORIGINS=["https://your-frontend.com"]
```

## 🔧 常见问题

### Q1: 导入错误 `ModuleNotFoundError: No module named 'langgraph'`

**解决方案**:
```bash
pip install langgraph langchain langchain-openai
```

### Q2: 数据库连接失败

**解决方案**:
1. 检查 `DATABASE_URL` 格式是否正确
2. 确保 PostgreSQL 服务正在运行
3. 验证数据库用户权限

### Q3: OCR 识别失败

**解决方案**:
1. 如果 PaddleOCR 安装失败，系统会自动使用 OCR.space API
2. 确保图像格式正确（JPG, PNG）
3. 检查图像大小不超过 50MB

### Q4: AI API 调用失败

**解决方案**:
1. 验证 API 密钥是否正确
2. 检查网络连接
3. 查看 API 配额是否用完

## 📊 监控和日志

### 查看日志

```bash
# 本地开发
tail -f logs/app.log

# Railway
railway logs
```

### 关键日志位置

- 应用日志: `logs/app.log`
- 错误日志: `logs/error.log`
- 访问日志: Railway 自动记录

## 🎯 API 端点总览

### LangGraph 批改 API

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/langgraph/grading/tasks` | 创建批改任务 |
| GET | `/api/v1/langgraph/grading/tasks/{id}` | 查询任务状态 |
| DELETE | `/api/v1/langgraph/grading/tasks/{id}` | 取消任务 |
| POST | `/api/v1/langgraph/grading/tasks/batch` | 批量批改 |

### 系统 API

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/docs` | API 文档 (仅开发模式) |
| GET | `/api/v1/health` | API 健康检查 |

## 📖 完整文档

- **实现文档**: `LANGGRAPH_IMPLEMENTATION.md`
- **部署检查清单**: `DEPLOYMENT_CHECKLIST.md`
- **实现总结**: `IMPLEMENTATION_SUMMARY.md`

## 🔐 认证

所有 API 端点都需要 Firebase Auth 认证。

### 获取 Token

```python
import firebase_admin
from firebase_admin import auth

# 初始化 Firebase
cred = credentials.Certificate('path/to/credentials.json')
firebase_admin.initialize_app(cred)

# 创建自定义 token
custom_token = auth.create_custom_token('user_id')
```

### 使用 Token

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/langgraph/grading/tasks
```

## 🧪 测试数据

### 示例请求

```json
{
  "question_files": [
    "uploads/math_question_1.jpg"
  ],
  "answer_files": [
    "uploads/student_answer_1.jpg"
  ],
  "marking_scheme_files": [
    "uploads/rubric.pdf"
  ],
  "task_type": "auto",
  "strictness_level": "中等",
  "language": "zh",
  "subject": "数学",
  "difficulty": "中等",
  "max_score": 100,
  "stream": false
}
```

### 示例响应

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "批改任务已创建，正在后台处理"
}
```

## 🎨 前端集成示例

### React 示例

```javascript
import { useState } from 'react';

function GradingForm() {
  const [result, setResult] = useState(null);
  
  const submitGrading = async (files) => {
    const response = await fetch('/api/v1/langgraph/grading/tasks', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        answer_files: files,
        max_score: 100
      })
    });
    
    const data = await response.json();
    setResult(data);
  };
  
  return (
    <div>
      {/* 文件上传表单 */}
      <button onClick={() => submitGrading(['file1.jpg'])}>
        提交批改
      </button>
      {result && <div>任务ID: {result.task_id}</div>}
    </div>
  );
}
```

### Vue 示例

```vue
<template>
  <div>
    <button @click="submitGrading">提交批改</button>
    <div v-if="result">任务ID: {{ result.task_id }}</div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      result: null
    }
  },
  methods: {
    async submitGrading() {
      const response = await fetch('/api/v1/langgraph/grading/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify({
          answer_files: ['file1.jpg'],
          max_score: 100
        })
      });
      
      this.result = await response.json();
    }
  }
}
</script>
```

## 📈 性能优化建议

1. **使用 Redis 缓存**: 缓存 OCR 结果和评分标准
2. **启用 CDN**: 加速文件上传和下载
3. **数据库索引**: 为常用查询字段添加索引
4. **异步处理**: 使用后台任务队列处理长时间任务
5. **限流**: 防止 API 滥用

## 🆘 获取帮助

- 查看文档: `LANGGRAPH_IMPLEMENTATION.md`
- 检查日志: `railway logs` 或 `tail -f logs/app.log`
- GitHub Issues: 提交问题和建议
- Railway 支持: https://railway.app/help

## ✅ 下一步

1. ✅ 完成基本部署
2. ⬜ 上传测试文件
3. ⬜ 测试批改功能
4. ⬜ 集成前端
5. ⬜ 性能优化
6. ⬜ 生产环境部署

祝你使用愉快！🎉

