# AI教育平台 - 智能批改系统

基于OpenRouter Gemini 2.5 Flash Lite的智能教育平台，支持坐标标注和局部图批改两种可视化展示模式。

## ✨ 核心功能

### 🤖 AI智能批改
- **OpenRouter Gemini 2.5 Flash Lite** 驱动的智能批改引擎
- **双模式可视化展示**：坐标标注 + 局部图卡片
- **知识点自动关联**：错误分析与学习建议
- **批量处理支持**：多作业同时批改

### 📊 可视化反馈
1. **坐标标注模式**
   - 在原图上精确标注错误位置
   - Canvas渲染，支持缩放拖拽
   - 点击查看详细错误分析

2. **局部图卡片模式**  
   - 自动裁剪错误区域
   - 卡片式展示配合文字说明
   - 一键定位回原图

### 🎯 教师工具
- **完全干预权限**：修改分数、添加评语
- **自定义批改标准**：灵活的评分规则
- **Excel数据互通**：无缝对接现有工作流
- **外部作业导入**：统一管理平台内外作业

### 📈 数据分析
- **多样化图表模板**：XY轴、雷达图、排名图等
- **知识点掌握分析**：薄弱环节识别
- **学习轨迹追踪**：个性化学习建议

## 🛠️ 技术架构

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