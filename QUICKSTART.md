# 🚀 快速启动指南

本指南帮助您快速启动新的Agent架构批改系统。

---

## 📋 前置要求

### 必需
- Python 3.10+
- PostgreSQL 15+
- Redis 7+
- Node.js 18+ (前端)

### 可选
- Docker & Docker Compose (推荐)

---

## 🔧 环境配置

### 1. 克隆项目

```bash
cd new_aicorrection
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 环境变量配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
# 必须配置的变量:
```

**最小配置** (.env):
```bash
# 安全密钥 (至少32字符)
SECRET_KEY=your-super-secret-key-at-least-32-characters-long
JWT_SECRET_KEY=your-jwt-secret-key-at-least-32-characters

# 数据库
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/aigrading

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenRouter API (推荐 - 免费额度)
OPENROUTER_API_KEY=your-openrouter-api-key-here
DEFAULT_MODEL=google/gemini-2.0-flash-exp:free

# 或者使用 OpenAI API
# OPENAI_API_KEY=your-openai-api-key-here

# 成本优化 (推荐开启)
ENABLE_UNIFIED_AGENT=true
ENABLE_SMART_CACHE=true
DEFAULT_GRADING_MODE=auto
```

### 4. 数据库初始化

#### 使用Docker (推荐)

```bash
# 启动PostgreSQL和Redis
docker-compose up -d postgres redis

# 等待服务启动 (约10秒)
sleep 10
```

#### 手动安装

如果您已经安装了PostgreSQL和Redis:

```bash
# 创建数据库
createdb aigrading

# 或使用psql
psql -U postgres -c "CREATE DATABASE aigrading;"
```

#### 运行数据库迁移

```bash
# 运行迁移
alembic upgrade head
```

### 5. 启动后端服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用脚本
python -m uvicorn app.main:app --reload
```

后端服务将在 http://localhost:8000 启动

### 6. 验证后端

打开浏览器访问:
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

---

## 🎨 前端配置 (可选)

```bash
cd ../frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务将在 http://localhost:3000 启动

---

## 🧪 测试系统

### 1. 运行单元测试

```bash
cd backend

# 运行所有测试
pytest tests/ -v

# 运行Agent测试
pytest tests/test_agents.py -v

# 运行特定测试
pytest tests/test_agents.py::TestComplexityAssessor -v
```

### 2. 运行演示脚本

```bash
cd backend

# 运行演示 (需要配置API密钥)
python demo_agent_grading.py
```

**预期输出**:
```
🚀 AI批改系统 - Agent架构演示

================================================================================
演示1: 简单数学题批改
================================================================================

【学生答案】
解:
x + y = 10
x - y = 2
x = 6, y = 4
答: 6和4

【开始批改...】

【批改结果】
状态: completed
得分: 8.5/10.0
置信度: 92%

【错误列表】(1个)
...
```

### 3. 测试API接口

#### 使用curl

```bash
# 测试健康检查
curl http://localhost:8000/health

# 测试同步批改 (需要认证token)
curl -X POST http://localhost:8000/api/v1/v2/grading/submit-sync \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "submission_id": "123e4567-e89b-12d3-a456-426614174000",
    "assignment_id": "123e4567-e89b-12d3-a456-426614174001",
    "mode": "fast",
    "max_score": 100,
    "config": {
      "grading_standard": {
        "criteria": "检查答案准确性",
        "answer": "正确答案"
      }
    }
  }'
```

#### 使用API文档

1. 访问 http://localhost:8000/docs
2. 找到 `/api/v1/v2/grading/submit-sync` 接口
3. 点击 "Try it out"
4. 填入测试数据
5. 点击 "Execute"

---

## 📊 验证成本优化

### 查看缓存统计

```bash
curl http://localhost:8000/api/v1/v2/grading/cache/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**预期响应**:
```json
{
  "enabled": true,
  "total_cached": 15,
  "ttl_seconds": 604800,
  "similarity_threshold": 0.85
}
```

### 监控成本

在演示脚本中查看成本对比:

```
【批改模式成本对比】
模式            预估成本        适用场景
------------------------------------------------------------
快速模式        $0.005         简单选择题、填空题
标准模式        $0.009         一般主观题
完整模式        $0.015         复杂论述题、作文

【成本优化效果】
原设计 (多Agent分离): $0.013/次
优化后 (Agent融合):   $0.009/次
节省比例: 31%
```

---

## 🐛 故障排除

### 问题1: 依赖安装失败

```bash
# 升级pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题2: 数据库连接失败

```bash
# 检查PostgreSQL是否运行
docker ps | grep postgres

# 检查数据库是否存在
psql -U postgres -l | grep aigrading

# 测试连接
psql -U postgres -d aigrading -c "SELECT 1;"
```

### 问题3: Redis连接失败

```bash
# 检查Redis是否运行
docker ps | grep redis

# 测试连接
redis-cli ping
# 应该返回: PONG
```

### 问题4: API密钥错误

确保在 `.env` 文件中正确配置了API密钥:

```bash
# 检查环境变量
cat .env | grep API_KEY

# OpenRouter API密钥格式
OPENROUTER_API_KEY=sk-or-v1-xxxxx...
```

获取免费API密钥:
- OpenRouter: https://openrouter.ai/keys
- OpenAI: https://platform.openai.com/api-keys

### 问题5: 导入错误

```bash
# 确保在正确的目录
pwd
# 应该在: .../new_aicorrection/backend

# 确保虚拟环境已激活
which python
# 应该指向: .../venv/bin/python

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

---

## 📚 下一步

### 学习资源

1. **API文档**: http://localhost:8000/docs
2. **设计文档**: [docs/README.md](docs/README.md)
3. **实施计划**: [docs/10_PHASE1_IMPLEMENTATION_PLAN.md](docs/10_PHASE1_IMPLEMENTATION_PLAN.md)
4. **进度跟踪**: [docs/PHASE1_PROGRESS.md](docs/PHASE1_PROGRESS.md)

### 开发任务

1. **集成文件服务**: 完善PreprocessAgent的文件处理
2. **实现数据持久化**: 保存批改结果到数据库
3. **添加WebSocket通知**: 实时推送批改进度
4. **开发前端界面**: 创建批改提交和结果展示页面

### 性能优化

1. **批量处理**: 实现多份作业合并批改
2. **缓存预热**: 预先缓存常见问题
3. **并发优化**: 提高并发处理能力
4. **监控告警**: 添加性能监控和成本追踪

---

## 🎉 成功!

如果您看到以下内容,说明系统已成功启动:

✅ 后端服务运行在 http://localhost:8000  
✅ API文档可访问  
✅ 数据库连接正常  
✅ Redis连接正常  
✅ 测试通过  

**恭喜!您已成功启动AI批改系统!** 🎊

---

## 💬 获取帮助

- 查看文档: [docs/](docs/)
- 查看示例: [demo_agent_grading.py](backend/demo_agent_grading.py)
- 查看测试: [tests/test_agents.py](backend/tests/test_agents.py)

---

**最后更新**: 2025-10-05

