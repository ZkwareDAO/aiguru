# 设计讨论与权衡分析

## 📌 文档概述

本文档讨论设计过程中的关键决策、权衡分析和最佳实践建议,帮助您更好地理解和优化系统设计。

---

## 1. Agent架构设计讨论

### 1.1 为什么选择LangGraph而不是简单的函数调用?

**问题**: 我们可以用简单的函数调用链来实现批改流程,为什么要使用LangGraph?

**答案**:

**LangGraph的优势**:
1. **可视化工作流**: 清晰的状态图,易于理解和维护
2. **状态管理**: 内置的状态管理机制,避免手动传递状态
3. **条件分支**: 支持复杂的条件路由,灵活性高
4. **可观测性**: 每个节点的执行都有清晰的追踪
5. **错误恢复**: 支持断点续传和状态持久化
6. **可扩展性**: 易于添加新的Agent节点

**简单函数调用的局限**:
```python
# 简单方式 - 难以维护
async def grade_submission(submission_id):
    # 预处理
    preprocessed = await preprocess(submission_id)
    if not preprocessed:
        return error
    
    # 批改
    graded = await grade(preprocessed)
    if not graded:
        return error
    
    # 审核
    if should_review(graded):
        reviewed = await review(graded)
        if not reviewed:
            return error
    
    # 反馈
    feedback = await generate_feedback(graded)
    return feedback
```

**LangGraph方式 - 清晰可维护**:
```python
# LangGraph方式 - 清晰的状态流转
workflow = StateGraph(GradingState)
workflow.add_node("preprocess", preprocess_agent.process)
workflow.add_node("grade", grading_agent.process)
workflow.add_node("review", review_agent.process)
workflow.add_node("feedback", feedback_agent.process)

workflow.add_conditional_edges("grade", should_review, {
    "review": "review",
    "feedback": "feedback"
})
```

**建议**: 对于复杂的多步骤流程,使用LangGraph;对于简单的单步任务,可以使用函数调用。

---

### 1.2 Agent粒度如何划分?

**问题**: Agent应该划分得多细?是否应该有更多的子Agent?

**权衡分析**:

**粗粒度Agent** (当前设计):
- ✅ 简单易懂
- ✅ 减少通信开销
- ✅ 易于部署和维护
- ❌ 单个Agent职责可能过重
- ❌ 难以独立优化

**细粒度Agent**:
- ✅ 职责更单一
- ✅ 易于独立优化和测试
- ✅ 更好的可复用性
- ❌ 增加系统复杂度
- ❌ 更多的通信开销
- ❌ 调试困难

**推荐方案**:
```
当前设计 (推荐):
OrchestratorAgent
├── PreprocessAgent
├── GradingAgent
├── ReviewAgent
└── FeedbackAgent

细粒度设计 (可选):
OrchestratorAgent
├── PreprocessAgent
│   ├── FileParserAgent
│   ├── OCRAgent
│   └── ValidatorAgent
├── GradingAgent
│   ├── ErrorDetectorAgent
│   ├── ScoreCalculatorAgent
│   └── AnnotationGeneratorAgent
├── ReviewAgent
│   ├── QualityCheckerAgent
│   └── ConsistencyValidatorAgent
└── FeedbackAgent
    ├── SuggestionGeneratorAgent
    └── KnowledgeLinkerAgent
```

**建议**: 
- 初期使用粗粒度设计(当前方案)
- 当某个Agent变得过于复杂时,再拆分为子Agent
- 遵循"先简单后复杂"的原则

---

### 1.3 同步 vs 异步处理?

**问题**: 批改流程应该同步还是异步?

**场景分析**:

**同步处理**:
```python
@app.post("/grading/submit")
async def submit_grading(request: GradingRequest):
    # 直接执行批改
    result = await orchestrator.execute(request)
    return result  # 等待完成后返回
```

**优点**:
- ✅ 实现简单
- ✅ 用户立即获得结果
- ✅ 无需额外的状态管理

**缺点**:
- ❌ 请求超时风险(批改可能需要30秒+)
- ❌ 无法处理大批量任务
- ❌ 服务器资源占用高

**异步处理** (推荐):
```python
@app.post("/grading/submit")
async def submit_grading(request: GradingRequest):
    # 创建任务
    task = await task_queue.enqueue_task(
        task_name="grading_task",
        payload={"submission_id": request.submission_id}
    )
    return {"task_id": task.id, "status": "pending"}

@app.get("/grading/task/{task_id}")
async def get_task_status(task_id: UUID):
    # 查询任务状态
    task = await task_queue.get_task_result(task_id)
    return task
```

**优点**:
- ✅ 快速响应
- ✅ 支持大批量处理
- ✅ 更好的资源利用
- ✅ 支持进度追踪

**缺点**:
- ❌ 实现复杂
- ❌ 需要额外的任务队列
- ❌ 需要WebSocket或轮询获取结果

**建议**: 
- 单份批改: 可以同步(如果能在10秒内完成)
- 批量批改: 必须异步
- 提供两种模式供用户选择

---

## 2. 可扩展性设计讨论

### 2.1 如何防止系统过载?

**问题**: 当有1000个学生同时提交作业时,系统如何应对?

**多层防护策略**:

**1. API层限流**:
```python
# 用户级限流: 每分钟最多10次提交
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    user_id = request.state.user_id
    allowed = await rate_limiter.check_rate_limit(
        key=f"user:{user_id}",
        limit=10,
        window=60
    )
    if not allowed:
        return JSONResponse(status_code=429, content={"error": "Too many requests"})
    return await call_next(request)
```

**2. 任务队列限流**:
```python
# 队列级限流: 最多1000个待处理任务
async def enqueue_task(task):
    queue_length = await task_queue.get_queue_length()
    if queue_length > 1000:
        raise QueueFullError("Task queue is full, please try again later")
    await task_queue.enqueue(task)
```

**3. Worker并发控制**:
```python
# Worker级限流: 最多10个并发任务
class WorkerPool:
    def __init__(self, max_concurrent=10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_task(self, task):
        async with self.semaphore:
            return await self._do_process(task)
```

**4. AI API限流**:
```python
# AI API限流: 每秒最多10次调用
class AIRateLimiter:
    def __init__(self, rate=10):
        self.token_bucket = TokenBucket(rate=rate, capacity=20)
    
    async def call_ai(self, prompt):
        await self.token_bucket.wait_for_token()
        return await ai_api.call(prompt)
```

**5. 优先级队列**:
```python
# 紧急任务优先处理
await task_queue.enqueue_task(
    task_name="grading_task",
    payload=data,
    priority=TaskPriority.URGENT  # 教师手动批改优先
)
```

---

### 2.2 如何保证批改顺序不混乱?

**问题**: 批量批改时,如何确保每个学生的作业不会被混淆?

**解决方案**:

**1. 唯一标识符**:
```python
class GradingTask:
    id: UUID  # 任务唯一ID
    submission_id: UUID  # 提交唯一ID
    correlation_id: UUID  # 关联ID(用于追踪整个流程)
```

**2. 状态隔离**:
```python
# 每个任务有独立的状态
class GradingState:
    submission_id: UUID  # 确保状态与提交绑定
    # ... 其他状态
```

**3. 数据库事务**:
```python
async def save_grading_result(result):
    async with db.begin():  # 事务保证原子性
        # 检查是否已存在
        existing = await db.get(GradingResult, result.submission_id)
        if existing:
            raise DuplicateError("Result already exists")
        
        # 保存结果
        db.add(result)
        await db.commit()
```

**4. 幂等性设计**:
```python
# 使用幂等性键防止重复处理
@app.post("/grading/submit")
async def submit_grading(
    request: GradingRequest,
    idempotency_key: str = Header(None)
):
    if await is_processed(idempotency_key):
        return await get_cached_result(idempotency_key)
    
    result = await process_grading(request)
    await cache_result(idempotency_key, result)
    return result
```

---

## 3. 用户体验设计讨论

### 3.1 实时反馈 vs 批量通知?

**问题**: 应该实时推送每个批改结果,还是批量完成后统一通知?

**场景分析**:

**实时反馈** (推荐):
```typescript
// WebSocket实时推送
wsManager.subscribe('grading_completed', (data) => {
  showNotification(`${data.studentName}的作业已批改完成`);
  updateResultList(data);
});
```

**优点**:
- ✅ 用户体验好
- ✅ 及时获得反馈
- ✅ 可以边批改边查看

**缺点**:
- ❌ 通知频繁,可能打扰用户
- ❌ 需要WebSocket连接

**批量通知**:
```typescript
// 批量完成后通知
await batchGrading.onComplete(() => {
  showNotification(`批改完成!共${count}份作业`);
});
```

**优点**:
- ✅ 减少通知干扰
- ✅ 实现简单

**缺点**:
- ❌ 用户需要等待
- ❌ 无法及时发现问题

**推荐方案**: 
- 提供两种模式供用户选择
- 默认使用实时反馈
- 允许用户关闭实时通知

---

### 3.2 坐标标注 vs 局部图卡片?

**问题**: 两种可视化方式各有什么优缺点?

**坐标标注模式**:
```tsx
<CoordinateAnnotationView 
  imageUrl={originalImage}
  annotations={[
    {x: 100, y: 200, width: 150, height: 80, label: "错误1"}
  ]}
/>
```

**优点**:
- ✅ 保留完整上下文
- ✅ 可以看到整体布局
- ✅ 适合查看多个错误的关系

**缺点**:
- ❌ 小屏幕上难以查看细节
- ❌ 需要缩放操作
- ❌ 标注可能重叠

**局部图卡片模式**:
```tsx
<CroppedRegionView 
  errors={[
    {croppedImageUrl: "/crop1.jpg", description: "..."}
  ]}
/>
```

**优点**:
- ✅ 细节清晰
- ✅ 移动端友好
- ✅ 易于浏览

**缺点**:
- ❌ 失去上下文
- ❌ 需要额外的图片裁剪
- ❌ 占用更多存储空间

**推荐方案**: 
- 同时提供两种模式
- 允许用户切换
- 桌面端默认坐标标注
- 移动端默认局部图卡片

---

## 4. 性能优化讨论

### 4.1 缓存策略如何设计?

**问题**: 哪些数据应该缓存?缓存多久?

**缓存策略矩阵**:

| 数据类型 | 是否缓存 | 缓存时长 | 缓存层级 | 原因 |
|---------|---------|---------|---------|------|
| 批改结果 | ✅ | 24小时 | Redis | 频繁查询,不常变化 |
| 作业信息 | ✅ | 1小时 | Redis + 内存 | 高频访问 |
| 用户信息 | ✅ | 30分钟 | Redis + 内存 | 高频访问 |
| OCR结果 | ✅ | 永久 | Redis + 数据库 | 计算成本高 |
| LLM响应 | ✅ | 7天 | Redis | API成本高 |
| 文件内容 | ❌ | - | - | 占用空间大 |
| 实时进度 | ❌ | - | - | 频繁变化 |

**缓存实现**:
```python
class CacheStrategy:
    @cache(ttl=3600, key="assignment:{assignment_id}")
    async def get_assignment(self, assignment_id: UUID):
        return await db.get(Assignment, assignment_id)
    
    @cache(ttl=86400, key="grading_result:{submission_id}")
    async def get_grading_result(self, submission_id: UUID):
        return await db.get(GradingResult, submission_id)
    
    @cache(ttl=604800, key="llm_response:{prompt_hash}")
    async def call_llm(self, prompt: str):
        return await llm.ainvoke(prompt)
```

---

### 4.2 数据库查询如何优化?

**常见问题**:

**N+1查询问题**:
```python
# ❌ 错误: N+1查询
assignments = await db.query(Assignment).all()
for assignment in assignments:
    submissions = await db.query(Submission).filter_by(
        assignment_id=assignment.id
    ).all()  # 每次循环都查询一次

# ✅ 正确: 使用JOIN
assignments = await db.query(Assignment).options(
    selectinload(Assignment.submissions)
).all()
```

**索引优化**:
```python
# 添加索引
class Submission(Base):
    __tablename__ = "submissions"
    
    id = Column(UUID, primary_key=True)
    assignment_id = Column(UUID, index=True)  # 添加索引
    student_id = Column(UUID, index=True)  # 添加索引
    status = Column(String, index=True)  # 添加索引
    submitted_at = Column(DateTime, index=True)  # 添加索引
    
    # 复合索引
    __table_args__ = (
        Index('idx_assignment_student', 'assignment_id', 'student_id'),
        Index('idx_status_submitted', 'status', 'submitted_at'),
    )
```

---

## 5. 安全性讨论

### 5.1 如何防止恶意提交?

**威胁场景**:
1. 上传超大文件耗尽存储
2. 频繁提交占用资源
3. 上传恶意文件(病毒、脚本)

**防护措施**:

**1. 文件大小限制**:
```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@app.post("/upload")
async def upload_file(file: UploadFile):
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large")
```

**2. 文件类型检查**:
```python
ALLOWED_TYPES = ["image/jpeg", "image/png", "application/pdf"]

def validate_file_type(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise ValueError("Invalid file type")
    
    # 检查文件头(防止伪造)
    magic_bytes = file.file.read(8)
    file.file.seek(0)
    
    if not is_valid_file(magic_bytes, file.content_type):
        raise ValueError("File content doesn't match type")
```

**3. 病毒扫描**:
```python
async def scan_file(file_path: str):
    # 使用ClamAV或其他病毒扫描工具
    result = await virus_scanner.scan(file_path)
    if result.is_infected:
        os.remove(file_path)
        raise SecurityError("Malicious file detected")
```

**4. 频率限制**:
```python
# 每个学生每天最多提交10次
@rate_limit(key="student:{student_id}", limit=10, window=86400)
async def submit_assignment(student_id: UUID, ...):
    pass
```

---

## 6. 成本优化讨论

### 6.1 如何降低AI API成本?

**成本分析**:
- 单次批改调用: ~$0.01
- 每天1000次批改: $10
- 每月成本: ~$300

**优化策略**:

**1. 智能缓存**:
```python
# 相似问题使用缓存结果
@cache_similar(similarity_threshold=0.9)
async def call_llm(prompt: str):
    return await llm.ainvoke(prompt)
```

**2. 批量处理**:
```python
# 批量调用减少API次数
async def batch_grade(submissions: List[Submission]):
    # 合并多个提交到一次API调用
    combined_prompt = build_batch_prompt(submissions)
    result = await llm.ainvoke(combined_prompt)
    return parse_batch_result(result)
```

**3. 模型选择**:
```python
# 简单任务使用便宜的模型
if is_simple_task(submission):
    model = "gpt-3.5-turbo"  # $0.001/1K tokens
else:
    model = "gpt-4-turbo"  # $0.01/1K tokens
```

**4. 提示词优化**:
```python
# 减少token数量
# ❌ 冗长的提示词
prompt = f"""
请你作为一个专业的教师,仔细阅读以下学生的答案,
然后根据标准答案进行详细的批改...
(1000+ tokens)
"""

# ✅ 精简的提示词
prompt = f"""
批改学生答案,找出错误并评分。
标准答案: {answer}
学生答案: {student_answer}
(200 tokens)
"""
```

---

## 7. 下一步行动建议

### 7.1 MVP(最小可行产品)功能

**第一阶段** (2周):
- [ ] 基础Agent框架
- [ ] 单份批改功能
- [ ] 简单的前端界面
- [ ] 基础数据库模型

**第二阶段** (2周):
- [ ] 批量批改
- [ ] 任务队列
- [ ] 实时进度追踪
- [ ] 批改结果可视化

**第三阶段** (2周):
- [ ] 审核机制
- [ ] 学习分析
- [ ] 性能优化
- [ ] 完整测试

### 7.2 技术选型建议

**必须使用**:
- ✅ LangChain/LangGraph (核心框架)
- ✅ FastAPI (后端API)
- ✅ PostgreSQL (主数据库)
- ✅ Redis (缓存+队列)

**推荐使用**:
- ✅ Next.js (前端框架)
- ✅ Docker (容器化)
- ✅ GitHub Actions (CI/CD)

**可选使用**:
- ⚪ Celery (如果Redis Streams不够用)
- ⚪ Kafka (如果需要更强大的消息队列)
- ⚪ Elasticsearch (如果需要全文搜索)

---

**讨论完成!** 🎉

如有更多问题,欢迎继续讨论!

