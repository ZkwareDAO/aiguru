# API文档和开发者指南

## 概述

班级作业批改系统提供了完整的REST API接口，供开发者集成和扩展系统功能。本文档详细介绍了所有可用的API端点、请求格式、响应格式和使用示例。

## 目录

1. [API概述](#api概述)
2. [认证授权](#认证授权)
3. [用户管理API](#用户管理api)
4. [班级管理API](#班级管理api)
5. [作业管理API](#作业管理api)
6. [提交管理API](#提交管理api)
7. [批改管理API](#批改管理api)
8. [文件管理API](#文件管理api)
9. [统计分析API](#统计分析api)
10. [错误处理](#错误处理)
11. [SDK和示例](#sdk和示例)

## API概述

### 基础信息

- **Base URL**: `http://localhost:8501/api/v1`
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8
- **API版本**: v1.0

### 通用响应格式

所有API响应都遵循统一的格式：

```json
{
    "success": true,
    "data": {},
    "message": "操作成功",
    "timestamp": "2025-01-01T12:00:00Z",
    "request_id": "req_123456789"
}
```

#### 成功响应
```json
{
    "success": true,
    "data": {
        "id": 1,
        "name": "示例数据"
    },
    "message": "操作成功"
}
```

#### 错误响应
```json
{
    "success": false,
    "error": {
        "code": "INVALID_PARAMETER",
        "message": "参数无效",
        "details": "字段'name'不能为空"
    },
    "message": "请求失败"
}
```

### HTTP状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 500 | 服务器内部错误 |

## 认证授权

### JWT Token认证

系统使用JWT Token进行身份认证。

#### 获取Token

**请求**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
    "username": "teacher1",
    "password": "password123"
}
```

**响应**
```json
{
    "success": true,
    "data": {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "expires_in": 3600,
        "user": {
            "id": 1,
            "username": "teacher1",
            "role": "teacher",
            "full_name": "张老师"
        }
    }
}
```

#### 使用Token

在所有需要认证的请求中，在Header中包含Token：

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 刷新Token

**请求**
```http
POST /api/v1/auth/refresh
Authorization: Bearer <current_token>
```

**响应**
```json
{
    "success": true,
    "data": {
        "token": "new_jwt_token_here",
        "expires_in": 3600
    }
}
```

### 权限控制

API端点根据用户角色进行权限控制：

- **admin**: 所有权限
- **teacher**: 班级和作业管理权限
- **student**: 作业查看和提交权限

## 用户管理API

### 获取用户信息

**请求**
```http
GET /api/v1/users/me
Authorization: Bearer <token>
```

**响应**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "username": "teacher1",
        "email": "teacher1@school.com",
        "role": "teacher",
        "full_name": "张老师",
        "created_at": "2025-01-01T10:00:00Z",
        "last_login": "2025-01-01T12:00:00Z"
    }
}
```

### 更新用户信息

**请求**
```http
PUT /api/v1/users/me
Authorization: Bearer <token>
Content-Type: application/json

{
    "full_name": "张老师",
    "email": "teacher1@newschool.com"
}
```

**响应**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "username": "teacher1",
        "email": "teacher1@newschool.com",
        "full_name": "张老师"
    },
    "message": "用户信息更新成功"
}
```

### 修改密码

**请求**
```http
POST /api/v1/users/change-password
Authorization: Bearer <token>
Content-Type: application/json

{
    "current_password": "old_password",
    "new_password": "new_password"
}
```

**响应**
```json
{
    "success": true,
    "message": "密码修改成功"
}
```

## 班级管理API

### 创建班级

**请求**
```http
POST /api/v1/classes
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "高一(1)班数学",
    "subject": "数学",
    "grade": "高一",
    "description": "高一年级数学班级"
}
```

**响应**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "name": "高一(1)班数学",
        "subject": "数学",
        "grade": "高一",
        "class_code": "ABC123",
        "teacher_id": 1,
        "created_at": "2025-01-01T10:00:00Z"
    },
    "message": "班级创建成功"
}
```

### 获取班级列表

**请求**
```http
GET /api/v1/classes
Authorization: Bearer <token>
```

**响应**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "name": "高一(1)班数学",
            "subject": "数学",
            "grade": "高一",
            "class_code": "ABC123",
            "student_count": 30,
            "assignment_count": 5
        }
    ]
}
```

### 获取班级详情

**请求**
```http
GET /api/v1/classes/{class_id}
Authorization: Bearer <token>
```

**响应**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "name": "高一(1)班数学",
        "subject": "数学",
        "grade": "高一",
        "class_code": "ABC123",
        "description": "高一年级数学班级",
        "teacher": {
            "id": 1,
            "username": "teacher1",
            "full_name": "张老师"
        },
        "students": [
            {
                "id": 2,
                "username": "student1",
                "full_name": "李同学"
            }
        ],
        "created_at": "2025-01-01T10:00:00Z"
    }
}
```

### 加入班级

**请求**
```http
POST /api/v1/classes/join
Authorization: Bearer <token>
Content-Type: application/json

{
    "class_code": "ABC123"
}
```

**响应**
```json
{
    "success": true,
    "data": {
        "class_id": 1,
        "class_name": "高一(1)班数学"
    },
    "message": "成功加入班级"
}
```

## 作业管理API

### 创建作业

**请求**
```http
POST /api/v1/assignments
Authorization: Bearer <token>
Content-Type: multipart/form-data

class_id: 1
title: 数学作业1
description: 解方程练习
deadline: 2025-01-15T23:59:59Z
question_files: [file1.pdf, file2.docx]
marking_files: [marking_standard.pdf]
```

**响应**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "class_id": 1,
        "title": "数学作业1",
        "description": "解方程练习",
        "deadline": "2025-01-15T23:59:59Z",
        "question_files": [
            {
                "filename": "file1.pdf",
                "url": "/api/v1/files/assignments/1/questions/file1.pdf"
            }
        ],
        "marking_files": [
            {
                "filename": "marking_standard.pdf",
                "url": "/api/v1/files/assignments/1/marking/marking_standard.pdf"
            }
        ],
        "created_at": "2025-01-01T10:00:00Z"
    },
    "message": "作业创建成功"
}
```

### 获取作业列表

**请求**
```http
GET /api/v1/assignments?class_id=1&status=active
Authorization: Bearer <token>
```

**响应**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "title": "数学作业1",
            "description": "解方程练习",
            "deadline": "2025-01-15T23:59:59Z",
            "status": "active",
            "submission_count": 25,
            "total_students": 30,
            "graded_count": 20
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 1,
        "pages": 1
    }
}
```

### 获取作业详情

**请求**
```http
GET /api/v1/assignments/{assignment_id}
Authorization: Bearer <token>
```

**响应**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "class_id": 1,
        "title": "数学作业1",
        "description": "解方程练习",
        "deadline": "2025-01-15T23:59:59Z",
        "question_files": [
            {
                "filename": "question1.pdf",
                "size": 1024000,
                "url": "/api/v1/files/assignments/1/questions/question1.pdf"
            }
        ],
        "marking_files": [
            {
                "filename": "marking_standard.pdf",
                "size": 512000,
                "url": "/api/v1/files/assignments/1/marking/marking_standard.pdf"
            }
        ],
        "statistics": {
            "total_students": 30,
            "submitted": 25,
            "graded": 20,
            "pending": 5,
            "average_score": 85.5
        },
        "created_at": "2025-01-01T10:00:00Z"
    }
}
```

### 更新作业

**请求**
```http
PUT /api/v1/assignments/{assignment_id}
Authorization: Bearer <token>
Content-Type: application/json

{
    "title": "数学作业1（修订版）",
    "description": "解方程练习，增加难题",
    "deadline": "2025-01-20T23:59:59Z"
}
```

**响应**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "title": "数学作业1（修订版）",
        "description": "解方程练习，增加难题",
        "deadline": "2025-01-20T23:59:59Z"
    },
    "message": "作业更新成功"
}
```

## 提交管理API

### 提交作业

**请求**
```http
POST /api/v1/submissions
Authorization: Bearer <token>
Content-Type: multipart/form-data

assignment_id: 1
answer_files: [answer1.pdf, answer2.docx]
notes: 这是我的作业提交
```

**响应**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "assignment_id": 1,
        "student_username": "student1",
        "answer_files": [
            {
                "filename": "answer1.pdf",
                "size": 2048000,
                "url": "/api/v1/files/submissions/1/answer1.pdf"
            }
        ],
        "status": "submitted",
        "submitted_at": "2025-01-10T14:30:00Z",
        "notes": "这是我的作业提交"
    },
    "message": "作业提交成功"
}
```

### 获取提交列表

**请求**
```http
GET /api/v1/submissions?assignment_id=1
Authorization: Bearer <token>
```

**响应**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "assignment_id": 1,
            "student": {
                "username": "student1",
                "full_name": "李同学"
            },
            "status": "graded",
            "score": 88.5,
            "submitted_at": "2025-01-10T14:30:00Z",
            "graded_at": "2025-01-10T15:00:00Z"
        }
    ]
}
```

### 获取提交详情

**请求**
```http
GET /api/v1/submissions/{submission_id}
Authorization: Bearer <token>
```

**响应**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "assignment": {
            "id": 1,
            "title": "数学作业1"
        },
        "student": {
            "username": "student1",
            "full_name": "李同学"
        },
        "answer_files": [
            {
                "filename": "answer1.pdf",
                "size": 2048000,
                "url": "/api/v1/files/submissions/1/answer1.pdf"
            }
        ],
        "status": "graded",
        "score": 88.5,
        "ai_result": {
            "score": 88.5,
            "confidence": 0.92,
            "feedback": "解题思路正确，计算准确。",
            "details": {
                "question1": {"score": 20, "max_score": 20},
                "question2": {"score": 18, "max_score": 20}
            }
        },
        "teacher_feedback": "很好的作业，继续保持！",
        "submitted_at": "2025-01-10T14:30:00Z",
        "graded_at": "2025-01-10T15:00:00Z"
    }
}
```

### 更新提交反馈

**请求**
```http
PUT /api/v1/submissions/{submission_id}/feedback
Authorization: Bearer <token>
Content-Type: application/json

{
    "score": 90.0,
    "teacher_feedback": "优秀的作业，解题思路清晰！",
    "detailed_scores": {
        "question1": 20,
        "question2": 20,
        "question3": 18
    }
}
```

**响应**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "score": 90.0,
        "teacher_feedback": "优秀的作业，解题思路清晰！",
        "updated_at": "2025-01-10T16:00:00Z"
    },
    "message": "反馈更新成功"
}
```

## 批改管理API

### 触发批改任务

**请求**
```http
POST /api/v1/grading/trigger
Authorization: Bearer <token>
Content-Type: application/json

{
    "submission_id": 1,
    "grading_config_id": "standard_math"
}
```

**响应**
```json
{
    "success": true,
    "data": {
        "task_id": "task_123456",
        "submission_id": 1,
        "status": "pending",
        "estimated_completion": "2025-01-10T15:05:00Z"
    },
    "message": "批改任务已创建"
}
```

### 获取批改任务状态

**请求**
```http
GET /api/v1/grading/tasks/{task_id}
Authorization: Bearer <token>
```

**响应**
```json
{
    "success": true,
    "data": {
        "task_id": "task_123456",
        "submission_id": 1,
        "status": "completed",
        "progress": 100,
        "result": {
            "score": 88.5,
            "confidence": 0.92,
            "feedback": "解题思路正确，计算准确。"
        },
        "created_at": "2025-01-10T15:00:00Z",
        "completed_at": "2025-01-10T15:03:00Z"
    }
}
```

### 批量批改

**请求**
```http
POST /api/v1/grading/batch
Authorization: Bearer <token>
Content-Type: application/json

{
    "assignment_id": 1,
    "submission_ids": [1, 2, 3, 4, 5],
    "grading_config_id": "standard_math"
}
```

**响应**
```json
{
    "success": true,
    "data": {
        "batch_id": "batch_789",
        "total_submissions": 5,
        "tasks": [
            {
                "task_id": "task_123456",
                "submission_id": 1,
                "status": "pending"
            }
        ]
    },
    "message": "批量批改任务已创建"
}
```

## 文件管理API

### 上传文件

**请求**
```http
POST /api/v1/files/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: [binary_file_data]
type: assignment_question
assignment_id: 1
```

**响应**
```json
{
    "success": true,
    "data": {
        "file_id": "file_123",
        "filename": "question1.pdf",
        "size": 1024000,
        "type": "assignment_question",
        "url": "/api/v1/files/assignments/1/questions/question1.pdf",
        "uploaded_at": "2025-01-10T10:00:00Z"
    },
    "message": "文件上传成功"
}
```

### 下载文件

**请求**
```http
GET /api/v1/files/{file_path}
Authorization: Bearer <token>
```

**响应**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="question1.pdf"
Content-Length: 1024000

[binary_file_data]
```

### 删除文件

**请求**
```http
DELETE /api/v1/files/{file_id}
Authorization: Bearer <token>
```

**响应**
```json
{
    "success": true,
    "message": "文件删除成功"
}
```

## 统计分析API

### 获取班级统计

**请求**
```http
GET /api/v1/statistics/class/{class_id}
Authorization: Bearer <token>
```

**响应**
```json
{
    "success": true,
    "data": {
        "class_id": 1,
        "total_students": 30,
        "total_assignments": 5,
        "total_submissions": 120,
        "average_score": 85.2,
        "completion_rate": 0.8,
        "grade_distribution": {
            "A": 8,
            "B": 12,
            "C": 7,
            "D": 2,
            "F": 1
        },
        "recent_activity": [
            {
                "date": "2025-01-10",
                "submissions": 15,
                "average_score": 87.3
            }
        ]
    }
}
```

### 获取学生统计

**请求**
```http
GET /api/v1/statistics/student/{student_username}
Authorization: Bearer <token>
```

**响应**
```json
{
    "success": true,
    "data": {
        "student_username": "student1",
        "total_assignments": 5,
        "completed_assignments": 4,
        "average_score": 88.5,
        "completion_rate": 0.8,
        "grade_trend": [
            {"assignment": "作业1", "score": 85},
            {"assignment": "作业2", "score": 90},
            {"assignment": "作业3", "score": 88},
            {"assignment": "作业4", "score": 92}
        ],
        "subject_performance": {
            "数学": {"average": 88.5, "count": 4},
            "语文": {"average": 85.0, "count": 3}
        }
    }
}
```

### 获取作业统计

**请求**
```http
GET /api/v1/statistics/assignment/{assignment_id}
Authorization: Bearer <token>
```

**响应**
```json
{
    "success": true,
    "data": {
        "assignment_id": 1,
        "title": "数学作业1",
        "total_students": 30,
        "submitted": 25,
        "graded": 20,
        "pending": 5,
        "average_score": 85.5,
        "median_score": 87.0,
        "score_distribution": {
            "90-100": 8,
            "80-89": 10,
            "70-79": 5,
            "60-69": 2,
            "0-59": 0
        },
        "question_analysis": [
            {
                "question": "问题1",
                "average_score": 18.5,
                "max_score": 20,
                "difficulty": "easy"
            }
        ]
    }
}
```

## 错误处理

### 错误代码

| 错误代码 | 说明 | HTTP状态码 |
|----------|------|------------|
| INVALID_PARAMETER | 参数无效 | 400 |
| MISSING_PARAMETER | 缺少必需参数 | 400 |
| UNAUTHORIZED | 未授权访问 | 401 |
| FORBIDDEN | 权限不足 | 403 |
| NOT_FOUND | 资源不存在 | 404 |
| CONFLICT | 资源冲突 | 409 |
| FILE_TOO_LARGE | 文件过大 | 413 |
| UNSUPPORTED_FILE_TYPE | 不支持的文件类型 | 415 |
| RATE_LIMIT_EXCEEDED | 请求频率超限 | 429 |
| INTERNAL_ERROR | 服务器内部错误 | 500 |
| SERVICE_UNAVAILABLE | 服务不可用 | 503 |

### 错误响应示例

```json
{
    "success": false,
    "error": {
        "code": "INVALID_PARAMETER",
        "message": "参数验证失败",
        "details": {
            "field": "title",
            "reason": "标题不能为空"
        }
    },
    "message": "请求失败",
    "timestamp": "2025-01-10T15:00:00Z",
    "request_id": "req_123456789"
}
```

## SDK和示例

### Python SDK

#### 安装
```bash
pip install classroom-grading-sdk
```

#### 使用示例
```python
from classroom_grading_sdk import ClassroomClient

# 初始化客户端
client = ClassroomClient(
    base_url="http://localhost:8501/api/v1",
    username="teacher1",
    password="password123"
)

# 创建班级
class_data = {
    "name": "高一(1)班数学",
    "subject": "数学",
    "grade": "高一"
}
new_class = client.classes.create(class_data)
print(f"创建班级: {new_class['name']}")

# 创建作业
assignment_data = {
    "class_id": new_class['id'],
    "title": "数学作业1",
    "description": "解方程练习",
    "deadline": "2025-01-15T23:59:59Z"
}
assignment = client.assignments.create(assignment_data)

# 上传作业文件
with open("question.pdf", "rb") as f:
    client.files.upload(
        file=f,
        type="assignment_question",
        assignment_id=assignment['id']
    )

# 获取提交列表
submissions = client.submissions.list(assignment_id=assignment['id'])
for submission in submissions:
    print(f"学生: {submission['student']['full_name']}, 分数: {submission['score']}")
```

### JavaScript SDK

#### 安装
```bash
npm install classroom-grading-sdk
```

#### 使用示例
```javascript
import { ClassroomClient } from 'classroom-grading-sdk';

// 初始化客户端
const client = new ClassroomClient({
    baseURL: 'http://localhost:8501/api/v1',
    username: 'teacher1',
    password: 'password123'
});

// 获取班级列表
const classes = await client.classes.list();
console.log('班级列表:', classes);

// 创建作业
const assignment = await client.assignments.create({
    class_id: 1,
    title: '数学作业1',
    description: '解方程练习',
    deadline: '2025-01-15T23:59:59Z'
});

// 获取作业统计
const stats = await client.statistics.assignment(assignment.id);
console.log('作业统计:', stats);
```

### cURL示例

#### 登录获取Token
```bash
curl -X POST http://localhost:8501/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "teacher1",
    "password": "password123"
  }'
```

#### 创建班级
```bash
curl -X POST http://localhost:8501/api/v1/classes \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "高一(1)班数学",
    "subject": "数学",
    "grade": "高一"
  }'
```

#### 上传文件
```bash
curl -X POST http://localhost:8501/api/v1/files/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@question.pdf" \
  -F "type=assignment_question" \
  -F "assignment_id=1"
```

### 开发环境设置

#### 本地开发
```bash
# 克隆项目
git clone <repository-url>
cd classroom-grading-system

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python -m uvicorn api.main:app --reload --port 8000

# 启动前端
streamlit run streamlit_simple.py --server.port 8501
```

#### 测试API
```bash
# 运行API测试
python -m pytest tests/api/ -v

# 运行集成测试
python -m pytest tests/integration/ -v
```

### 最佳实践

#### 1. 错误处理
```python
try:
    result = client.assignments.create(assignment_data)
except ClassroomAPIError as e:
    if e.code == 'INVALID_PARAMETER':
        print(f"参数错误: {e.details}")
    elif e.code == 'UNAUTHORIZED':
        print("需要重新登录")
        client.auth.refresh_token()
    else:
        print(f"API错误: {e.message}")
```

#### 2. 分页处理
```python
# 获取所有提交（分页）
all_submissions = []
page = 1
while True:
    submissions = client.submissions.list(
        assignment_id=1,
        page=page,
        per_page=50
    )
    all_submissions.extend(submissions['data'])
    if page >= submissions['pagination']['pages']:
        break
    page += 1
```

#### 3. 文件上传
```python
# 大文件分块上传
def upload_large_file(client, file_path, assignment_id):
    chunk_size = 1024 * 1024  # 1MB chunks
    
    with open(file_path, 'rb') as f:
        file_size = os.path.getsize(file_path)
        chunks = (file_size + chunk_size - 1) // chunk_size
        
        for i in range(chunks):
            chunk = f.read(chunk_size)
            client.files.upload_chunk(
                chunk=chunk,
                chunk_index=i,
                total_chunks=chunks,
                assignment_id=assignment_id
            )
```

---

**版本信息**：v1.0  
**更新日期**：2025年1月  
**适用系统**：班级作业批改系统 v1.0+  
**技术支持**：api-support@example.com