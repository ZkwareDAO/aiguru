# AI Education Backend

AI智能批改系统后端服务，基于FastAPI构建。

## 功能特性

- 用户认证与授权系统
- AI批改服务集成
- 基于LangChain的AI Agent
- 班级与作业管理
- 文件存储与处理
- 实时通信与通知
- 数据分析与报告

## 技术栈

- **框架**: FastAPI
- **数据库**: PostgreSQL + Redis
- **AI集成**: LangChain + OpenAI
- **部署**: Railway
- **语言**: Python 3.11+

## 快速开始

### 环境要求

- Python 3.11+
- PostgreSQL 14+
- Redis 6+

### 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 开发环境依赖
pip install -r requirements-dev.txt
```

### 环境配置

复制环境变量模板并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置必要的环境变量。

### 运行应用

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 数据库迁移

```bash
# 初始化迁移
alembic init alembic

# 创建迁移
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head
```

## 开发指南

### 代码规范

项目使用以下工具确保代码质量：

- **Black**: 代码格式化
- **isort**: 导入排序
- **flake8**: 代码检查
- **mypy**: 类型检查

```bash
# 格式化代码
black app/
isort app/

# 代码检查
flake8 app/
mypy app/
```

### 测试

```bash
# 运行测试
pytest

# 测试覆盖率
pytest --cov=app --cov-report=html
```

### Pre-commit Hooks

```bash
# 安装pre-commit hooks
pre-commit install

# 手动运行所有hooks
pre-commit run --all-files
```

## API文档

启动应用后，访问以下地址查看API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI应用入口
│   ├── core/                   # 核心配置
│   │   ├── config.py          # 应用配置
│   │   └── logging.py         # 日志配置
│   ├── api/                   # API路由
│   │   └── v1/
│   │       ├── router.py      # 主路由
│   │       └── endpoints/     # 端点实现
│   ├── models/                # 数据库模型
│   ├── schemas/               # Pydantic模式
│   ├── services/              # 业务逻辑
│   └── utils/                 # 工具函数
├── tests/                     # 测试文件
├── alembic/                   # 数据库迁移
├── pyproject.toml            # 项目配置
├── requirements.txt          # 生产依赖
├── requirements-dev.txt      # 开发依赖
└── README.md
```

## 部署

### Railway部署

1. 连接GitHub仓库到Railway
2. 配置环境变量
3. 自动部署

### Docker部署

```bash
# 构建镜像
docker build -t ai-education-backend .

# 运行容器
docker run -p 8000:8000 ai-education-backend
```

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 许可证

MIT License