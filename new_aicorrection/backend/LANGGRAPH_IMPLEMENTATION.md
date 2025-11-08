# LangGraph AI 批改系统实现文档

## 概述

本文档描述了基于 LangGraph 框架实现的新一代 AI 批改后端系统。该系统采用多 Agent 协作架构，提供更强大、更灵活的批改能力。

## 架构设计

### 核心组件

1. **LangGraph StateGraph**: 状态图编排引擎
2. **专业化节点 (Nodes)**: 8 个专门的处理节点
3. **状态管理 (State)**: 统一的状态定义和传递
4. **API 层**: RESTful API 和 WebSocket 支持

### 节点架构

```
UploadValidator → DocumentIngestor → RubricInterpreter → ScoringAgent → ResultAssembler → END
```

#### 1. UploadValidator (上传验证器)
- **职责**: 验证上传文件的格式、大小和完整性
- **输入**: 原始文件路径
- **输出**: 验证结果、任务 ID
- **文件**: `app/services/langgraph_nodes/upload_validator.py`

#### 2. DocumentIngestor (文档摄取器)
- **职责**: 图像预处理、OCR 识别、区域检测
- **技术**: PaddleOCR / OCR.space API
- **输出**: 结构化文本、坐标信息
- **文件**: `app/services/langgraph_nodes/document_ingestor.py`

#### 3. RubricInterpreter (评分标准解释器)
- **职责**: 解析评分标准、构建 rubric schema
- **输入**: 评分标准文件或自动生成
- **输出**: 结构化评分规则
- **文件**: `app/services/langgraph_nodes/rubric_interpreter.py`

#### 4. ScoringAgent (评分代理)
- **职责**: 调用 LLM 进行智能评分
- **模型**: Gemini / GPT / OpenRouter
- **输出**: 分数、详细反馈、建议
- **文件**: `app/services/langgraph_nodes/scoring_agent.py`

#### 5. ResultAssembler (结果汇总器)
- **职责**: 汇总所有结果并保存到数据库
- **输出**: 完整的批改结果 JSON
- **文件**: `app/services/langgraph_nodes/result_assembler.py`

## 状态定义

### GraphState 结构

```python
class GraphState(TypedDict):
    # 任务标识
    task_id: str
    submission_id: Optional[str]
    assignment_id: Optional[str]
    user_id: Optional[str]
    
    # 输入文件
    question_files: List[str]
    answer_files: List[str]
    marking_scheme_files: List[str]
    
    # 配置参数
    task_type: str
    strictness_level: str
    language: str
    max_score: int
    
    # 处理结果
    ocr_output: Optional[Dict[str, Any]]
    rubric: Optional[Dict[str, Any]]
    scores: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    
    # 状态跟踪
    status: str
    current_phase: str
    progress: int
    events: List[Dict[str, Any]]
```

## API 端点

### 1. 创建批改任务

**POST** `/api/v1/langgraph/grading/tasks`

```json
{
  "question_files": ["path/to/question.jpg"],
  "answer_files": ["path/to/answer.jpg"],
  "marking_scheme_files": ["path/to/rubric.pdf"],
  "task_type": "auto",
  "strictness_level": "中等",
  "language": "zh",
  "max_score": 100,
  "stream": false
}
```

**响应**:
```json
{
  "task_id": "uuid-here",
  "status": "queued",
  "message": "批改任务已创建，正在后台处理"
}
```

### 2. 查询任务状态

**GET** `/api/v1/langgraph/grading/tasks/{task_id}`

**响应**:
```json
{
  "task_id": "uuid-here",
  "status": "processing",
  "phase": "scoring",
  "progress": 60,
  "result": null,
  "error": null
}
```

### 3. 流式批改 (Server-Sent Events)

**POST** `/api/v1/langgraph/grading/tasks` (with `stream: true`)

返回 SSE 流:
```
data: {"type": "progress", "phase": "upload_validation", "progress": 5}
data: {"type": "progress", "phase": "document_ingestion", "progress": 20}
data: {"type": "progress", "phase": "scoring", "progress": 60}
data: {"type": "complete", "result": {...}}
```

### 4. 批量批改

**POST** `/api/v1/langgraph/grading/tasks/batch`

```json
[
  {
    "answer_files": ["student1/answer.jpg"],
    "max_score": 100
  },
  {
    "answer_files": ["student2/answer.jpg"],
    "max_score": 100
  }
]
```

### 5. 取消任务

**DELETE** `/api/v1/langgraph/grading/tasks/{task_id}`

## 使用示例

### Python 客户端

```python
import requests

# 创建批改任务
response = requests.post(
    "http://localhost:8000/api/v1/langgraph/grading/tasks",
    json={
        "answer_files": ["uploads/answer.jpg"],
        "question_files": ["uploads/question.jpg"],
        "max_score": 100,
        "strictness_level": "中等"
    },
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

task_id = response.json()["task_id"]

# 查询状态
status = requests.get(
    f"http://localhost:8000/api/v1/langgraph/grading/tasks/{task_id}",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

print(status.json())
```

### JavaScript 客户端 (SSE)

```javascript
const eventSource = new EventSource(
  '/api/v1/langgraph/grading/tasks?stream=true',
  {
    headers: {
      'Authorization': 'Bearer YOUR_TOKEN'
    }
  }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'progress') {
    console.log(`进度: ${data.progress}% - ${data.phase}`);
  } else if (data.type === 'complete') {
    console.log('批改完成:', data.result);
    eventSource.close();
  }
};
```

## 部署配置

### 环境变量

```bash
# LangGraph 配置
LANGGRAPH_CHECKPOINT_BACKEND=memory  # 或 redis
LANGGRAPH_MAX_WORKERS=4

# AI 模型配置
OPENAI_API_KEY=your_key
OPENROUTER_API_KEY=your_key
GEMINI_API_KEY=your_key

# OCR 配置
OCR_ENGINE=paddleocr  # 或 ocrspace
OCR_SPACE_API_KEY=your_key

# 数据库
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
```

### Railway 部署

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 启动服务:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

3. 健康检查:
```bash
curl http://localhost:8000/health
```

## 性能优化

### 1. 并发处理
- 使用异步 I/O (asyncio)
- 数据库连接池
- Redis 缓存

### 2. 批量处理
- 支持批量任务提交
- 后台任务队列
- 优先级调度

### 3. 资源管理
- 文件上传大小限制: 50MB
- 任务超时: 5 分钟
- 并发任务数限制: 10

## 监控和日志

### 日志级别
- INFO: 正常操作
- WARNING: 可恢复错误
- ERROR: 严重错误

### 关键指标
- 任务处理时间
- 成功率
- OCR 准确率
- AI 评分质量

## 故障排查

### 常见问题

1. **OCR 识别失败**
   - 检查图像质量
   - 验证 PaddleOCR 安装
   - 尝试备用 OCR 引擎

2. **AI 评分超时**
   - 检查 API 密钥
   - 增加超时时间
   - 使用更快的模型

3. **数据库连接错误**
   - 验证连接字符串
   - 检查网络连接
   - 查看连接池状态

## 未来改进

- [ ] 支持更多 OCR 引擎
- [ ] 实现节点级重试机制
- [ ] 添加 Redis checkpoint 持久化
- [ ] 支持自定义节点扩展
- [ ] 实现任务优先级队列
- [ ] 添加详细的性能分析
- [ ] 支持多语言批改
- [ ] 集成更多 AI 模型

## 参考资料

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangChain 文档](https://python.langchain.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [PaddleOCR 文档](https://github.com/PaddlePaddle/PaddleOCR)

