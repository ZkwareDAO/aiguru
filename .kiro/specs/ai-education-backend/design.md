# 设计文档

## 概述

本设计文档描述了AI智能批改系统后端的技术架构和实现方案。系统采用现代Python技术栈，使用FastAPI作为Web框架，PostgreSQL作为主数据库，Redis作为缓存和消息队列，部署在Railway平台上。系统设计遵循微服务架构原则，确保高可用性、可扩展性和安全性。

## 架构

### 系统架构图

```mermaid
graph TB
    subgraph "前端层"
        FE[Next.js 前端应用]
    end
    
    subgraph "API网关层"
        GW[Nginx/Railway 负载均衡]
    end
    
    subgraph "应用服务层"
        API[FastAPI 主服务]
        AUTH[认证服务]
        AI[AI批改服务]
        AGENT[LangChain Agent服务]
        WS[WebSocket服务]
    end
    
    subgraph "数据层"
        PG[(PostgreSQL 主数据库)]
        REDIS[(Redis 缓存/队列)]
        S3[文件存储服务]
    end
    
    subgraph "外部服务"
        AIAPI[AI批改API]
        OPENAI[OpenAI API]
        EMAIL[邮件服务]
    end
    
    FE --> GW
    GW --> API
    API --> AUTH
    API --> AI
    API --> AGENT
    API --> WS
    
    AUTH --> PG
    AUTH --> REDIS
    AI --> PG
    AI --> REDIS
    AI --> AIAPI
    AGENT --> PG
    AGENT --> OPENAI
    WS --> REDIS
    
    API --> S3
    AUTH --> EMAIL
```

### 技术栈选择

**后端框架：** FastAPI
- 高性能异步框架
- 自动生成OpenAPI文档
- 内置数据验证和序列化
- 优秀的类型提示支持

**数据库：** PostgreSQL + Redis
- PostgreSQL：主数据存储，支持复杂查询和事务
- Redis：缓存、会话存储、消息队列

**AI集成：** LangChain + OpenAI
- LangChain：AI Agent框架
- OpenAI API：GPT模型调用
- 自定义AI批改服务集成

**部署平台：** Railway
- 简化的部署流程
- 自动扩展和负载均衡
- 集成数据库服务

## 组件和接口

### 1. 认证服务 (Authentication Service)

**职责：**
- 用户注册、登录、密码管理
- JWT令牌生成和验证
- 角色权限管理
- 会话管理

**核心接口：**
```python
class AuthService:
    async def register_user(self, user_data: UserCreate) -> User
    async def authenticate_user(self, email: str, password: str) -> TokenResponse
    async def verify_token(self, token: str) -> User
    async def refresh_token(self, refresh_token: str) -> TokenResponse
    async def reset_password(self, email: str) -> bool
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool
```

### 2. 用户管理服务 (User Management Service)

**职责：**
- 用户信息CRUD操作
- 角色权限管理
- 用户关系管理（教师-学生-家长）

**核心接口：**
```python
class UserService:
    async def get_user_profile(self, user_id: str) -> UserProfile
    async def update_user_profile(self, user_id: str, profile_data: UserUpdate) -> User
    async def get_user_by_role(self, role: UserRole) -> List[User]
    async def link_parent_student(self, parent_id: str, student_id: str) -> bool
    async def get_teacher_classes(self, teacher_id: str) -> List[Class]
```

### 3. 班级管理服务 (Class Management Service)

**职责：**
- 班级创建和管理
- 学生班级关系管理
- 班级统计数据

**核心接口：**
```python
class ClassService:
    async def create_class(self, teacher_id: str, class_data: ClassCreate) -> Class
    async def add_student_to_class(self, class_id: str, student_id: str) -> bool
    async def get_class_students(self, class_id: str) -> List[User]
    async def get_class_statistics(self, class_id: str) -> ClassStats
    async def generate_class_code(self, class_id: str) -> str
```

### 4. 作业管理服务 (Assignment Service)

**职责：**
- 作业发布和管理
- 作业提交处理
- 作业状态跟踪

**核心接口：**
```python
class AssignmentService:
    async def create_assignment(self, teacher_id: str, assignment_data: AssignmentCreate) -> Assignment
    async def submit_assignment(self, student_id: str, assignment_id: str, files: List[UploadFile]) -> Submission
    async def get_assignment_submissions(self, assignment_id: str) -> List[Submission]
    async def get_student_assignments(self, student_id: str) -> List[Assignment]
    async def update_assignment_status(self, assignment_id: str, status: AssignmentStatus) -> Assignment
```

### 5. AI批改服务 (AI Grading Service)

**职责：**
- 文件处理和AI多模态分析
- AI批改API调用
- 批改结果处理和存储
- 异步任务管理

**核心接口：**
```python
class GradingService:
    async def start_grading_task(self, submission_id: str, files: GradingFiles) -> GradingTask
    async def process_grading_files(self, files: List[UploadFile]) -> ProcessedFiles
    async def call_ai_grading_api(self, processed_files: ProcessedFiles) -> GradingResult
    async def get_grading_status(self, task_id: str) -> GradingTaskStatus
    async def save_grading_result(self, task_id: str, result: GradingResult) -> bool
```

### 6. LangChain AI Agent服务

**职责：**
- 智能对话处理
- 学习数据分析
- 个性化建议生成
- 上下文管理

**核心接口：**
```python
class AIAgentService:
    async def process_chat_message(self, user_id: str, message: str) -> ChatResponse
    async def analyze_learning_data(self, user_id: str) -> LearningAnalysis
    async def generate_study_plan(self, user_id: str, goals: List[str]) -> StudyPlan
    async def get_chat_history(self, user_id: str, limit: int = 50) -> List[ChatMessage]
    async def update_user_context(self, user_id: str, context_data: dict) -> bool
```

### 7. 文件存储服务 (File Storage Service)

**职责：**
- 文件上传和存储
- 文件类型验证
- AI多模态内容分析
- 文件访问权限控制

**核心接口：**
```python
class FileService:
    async def upload_file(self, file: UploadFile, user_id: str) -> FileRecord
    async def analyze_content_with_ai(self, file_path: str) -> AIAnalysisResult
    async def analyze_document_with_ai(self, file_path: str) -> DocumentAnalysis
    async def get_file_url(self, file_id: str, user_id: str) -> str
    async def delete_file(self, file_id: str, user_id: str) -> bool
```

### 8. 通知服务 (Notification Service)

**职责：**
- 实时消息推送
- 邮件通知
- WebSocket连接管理
- 消息队列处理

**核心接口：**
```python
class NotificationService:
    async def send_realtime_notification(self, user_id: str, notification: Notification) -> bool
    async def send_email_notification(self, email: str, template: str, data: dict) -> bool
    async def broadcast_to_class(self, class_id: str, message: str) -> bool
    async def get_user_notifications(self, user_id: str) -> List[Notification]
    async def mark_notification_read(self, notification_id: str) -> bool
```

### 9. 数据分析服务 (Analytics Service)

**职责：**
- 学习数据统计
- 成绩趋势分析
- 报告生成
- 数据可视化

**核心接口：**
```python
class AnalyticsService:
    async def generate_student_report(self, student_id: str, period: str) -> StudentReport
    async def get_class_performance_stats(self, class_id: str) -> ClassPerformance
    async def analyze_error_patterns(self, student_id: str) -> ErrorAnalysis
    async def export_report(self, report_id: str, format: str) -> bytes
    async def get_learning_trends(self, user_id: str) -> LearningTrends
```

## 数据模型

### 核心数据表设计

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('student', 'teacher', 'parent')),
    avatar_url VARCHAR(500),
    school VARCHAR(200),
    grade VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- 班级表
CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    teacher_id UUID NOT NULL REFERENCES users(id),
    class_code VARCHAR(10) UNIQUE NOT NULL,
    school VARCHAR(200),
    grade VARCHAR(50),
    subject VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- 班级学生关系表
CREATE TABLE class_students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES classes(id),
    student_id UUID NOT NULL REFERENCES users(id),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(class_id, student_id)
);

-- 家长学生关系表
CREATE TABLE parent_student_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID NOT NULL REFERENCES users(id),
    student_id UUID NOT NULL REFERENCES users(id),
    relation_type VARCHAR(20) DEFAULT 'parent',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(parent_id, student_id)
);

-- 作业表
CREATE TABLE assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    teacher_id UUID NOT NULL REFERENCES users(id),
    class_id UUID NOT NULL REFERENCES classes(id),
    subject VARCHAR(100),
    due_date TIMESTAMP,
    total_points INTEGER DEFAULT 100,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 作业提交表
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES assignments(id),
    student_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'submitted',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    graded_at TIMESTAMP,
    score INTEGER,
    feedback TEXT,
    UNIQUE(assignment_id, student_id)
);

-- 文件表
CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL,
    file_url VARCHAR(500) NOT NULL,
    uploaded_by UUID NOT NULL REFERENCES users(id),
    submission_id UUID REFERENCES submissions(id),
    ai_analysis_result JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI批改任务表
CREATE TABLE grading_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES submissions(id),
    status VARCHAR(20) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- AI对话记录表
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('user', 'assistant')),
    content TEXT NOT NULL,
    context_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 通知表
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    type VARCHAR(50) NOT NULL,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 学习分析数据表
CREATE TABLE learning_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    subject VARCHAR(100),
    knowledge_point VARCHAR(200),
    mastery_level DECIMAL(3,2),
    error_count INTEGER DEFAULT 0,
    practice_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 索引设计

```sql
-- 性能优化索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_classes_teacher ON classes(teacher_id);
CREATE INDEX idx_class_students_class ON class_students(class_id);
CREATE INDEX idx_class_students_student ON class_students(student_id);
CREATE INDEX idx_assignments_class ON assignments(class_id);
CREATE INDEX idx_assignments_teacher ON assignments(teacher_id);
CREATE INDEX idx_submissions_assignment ON submissions(assignment_id);
CREATE INDEX idx_submissions_student ON submissions(student_id);
CREATE INDEX idx_files_submission ON files(submission_id);
CREATE INDEX idx_grading_tasks_submission ON grading_tasks(submission_id);
CREATE INDEX idx_chat_messages_user ON chat_messages(user_id);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_learning_analytics_user ON learning_analytics(user_id);
```

## 错误处理

### 错误分类和处理策略

**1. 认证和授权错误**
- 401 Unauthorized：无效令牌或未登录
- 403 Forbidden：权限不足
- 处理：返回标准错误响应，前端跳转登录页

**2. 数据验证错误**
- 422 Unprocessable Entity：请求数据格式错误
- 400 Bad Request：参数缺失或无效
- 处理：详细的字段级错误信息

**3. 业务逻辑错误**
- 409 Conflict：资源冲突（如重复注册）
- 404 Not Found：资源不存在
- 处理：友好的业务错误提示

**4. 系统错误**
- 500 Internal Server Error：服务器内部错误
- 503 Service Unavailable：服务不可用
- 处理：错误日志记录，通用错误提示

**5. 外部服务错误**
- AI API调用失败
- 文件存储服务异常
- 处理：重试机制，降级方案

### 错误响应格式

```python
class ErrorResponse(BaseModel):
    error: bool = True
    error_code: str
    message: str
    details: Optional[dict] = None
    timestamp: datetime
    request_id: str
```

## 测试策略

### 测试层级

**1. 单元测试**
- 覆盖所有服务类的核心方法
- 数据模型验证测试
- 工具函数测试
- 目标覆盖率：90%+

**2. 集成测试**
- API端点测试
- 数据库操作测试
- 外部服务集成测试
- 认证流程测试

**3. 端到端测试**
- 完整业务流程测试
- 用户场景测试
- 性能基准测试

**4. 安全测试**
- SQL注入防护测试
- XSS防护测试
- 认证绕过测试
- 权限提升测试

### 测试工具和框架

```python
# 测试依赖
pytest                  # 测试框架
pytest-asyncio         # 异步测试支持
httpx                  # HTTP客户端测试
pytest-cov            # 覆盖率报告
factory-boy           # 测试数据工厂
faker                 # 假数据生成
```

### 测试数据管理

**测试数据库：**
- 使用独立的测试数据库
- 每个测试用例前后清理数据
- 使用事务回滚保证测试隔离

**Mock策略：**
- 外部API调用使用Mock
- 文件操作使用临时目录
- 时间相关测试使用固定时间

## 部署架构

### Railway部署配置

**环境变量配置：**
```bash
# 数据库配置
DATABASE_URL=postgresql://user:password@host:port/dbname
REDIS_URL=redis://host:port/0

# 认证配置
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI服务配置
OPENAI_API_KEY=your-openai-key
AI_GRADING_API_URL=https://api.example.com
AI_GRADING_API_KEY=your-grading-api-key

# 文件存储配置
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1

# 邮件服务配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email
SMTP_PASSWORD=your-password

# 应用配置
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
```

**Dockerfile配置：**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 监控和日志

**日志配置：**
```python
import logging
from pythonjsonlogger import jsonlogger

# 结构化日志配置
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
```

**健康检查端点：**
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "database": await check_database_connection(),
        "redis": await check_redis_connection()
    }
```

### 安全配置

**CORS配置：**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**安全中间件：**
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com"])
app.add_middleware(HTTPSRedirectMiddleware)
```

**速率限制：**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

这个设计文档提供了完整的技术架构方案，涵盖了所有核心组件的设计和实现细节。系统采用现代化的技术栈，确保高性能、可扩展性和安全性。