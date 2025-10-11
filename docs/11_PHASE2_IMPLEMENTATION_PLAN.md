# Phase 2 实施计划 - 前端集成与完整测试

**计划日期**: 2025-10-05  
**预计工期**: 2周 (10个工作日)  
**目标**: 将Agent批改系统集成到前端，实现完整的用户体验  

---

## 📋 Phase 2 目标

### 核心目标
1. ✅ **前端集成** - 创建批改相关的前端页面
2. ✅ **实时反馈** - WebSocket实时进度更新
3. ✅ **数据库集成** - 确保数据正确存储和查询
4. ✅ **完整测试** - 端到端功能测试
5. ✅ **用户体验优化** - 流畅的交互体验

### 成功标准
- [ ] 用户可以通过前端提交作业批改
- [ ] 实时显示批改进度
- [ ] 批改结果正确显示和存储
- [ ] 支持查看历史批改记录
- [ ] 响应时间 < 15秒
- [ ] 用户体验流畅

---

## 🗓️ 详细时间表

### Week 1: 后端完善与API集成

#### Day 1-2: 数据库集成与测试
**目标**: 确保批改结果正确存储到数据库

**任务**:
1. 检查现有数据库模型
2. 更新Submission模型以支持Agent批改结果
3. 创建批改结果存储服务
4. 测试数据库读写

**产出**:
- [ ] 更新的数据库模型
- [ ] 批改结果存储服务
- [ ] 数据库集成测试

---

#### Day 3-4: WebSocket实时通知
**目标**: 实现批改进度的实时推送

**任务**:
1. 检查现有WebSocket实现
2. 添加批改进度事件
3. 实现进度推送逻辑
4. 测试WebSocket连接

**产出**:
- [ ] WebSocket进度推送
- [ ] 进度事件定义
- [ ] WebSocket测试

---

#### Day 5: API完善与文档
**目标**: 完善API接口，生成文档

**任务**:
1. 完善grading_v2 API
2. 添加错误处理
3. 生成API文档
4. 编写API使用示例

**产出**:
- [ ] 完善的API接口
- [ ] API文档
- [ ] 使用示例

---

### Week 2: 前端开发与测试

#### Day 6-7: 前端页面开发
**目标**: 创建批改相关的前端页面

**任务**:
1. 创建作业提交页面
2. 创建批改进度页面
3. 创建批改结果页面
4. 创建历史记录页面

**产出**:
- [ ] 作业提交页面
- [ ] 批改进度页面
- [ ] 批改结果页面
- [ ] 历史记录页面

---

#### Day 8: 前端API集成
**目标**: 连接前端与后端API

**任务**:
1. 创建API客户端
2. 实现数据获取逻辑
3. 实现WebSocket连接
4. 处理错误和加载状态

**产出**:
- [ ] API客户端
- [ ] 数据获取hooks
- [ ] WebSocket集成
- [ ] 错误处理

---

#### Day 9: 端到端测试
**目标**: 完整流程测试

**任务**:
1. 测试完整批改流程
2. 测试实时进度更新
3. 测试错误处理
4. 性能测试

**产出**:
- [ ] 端到端测试报告
- [ ] 性能测试报告
- [ ] Bug修复列表

---

#### Day 10: 优化与部署准备
**目标**: 优化用户体验，准备部署

**任务**:
1. UI/UX优化
2. 性能优化
3. 文档完善
4. 部署准备

**产出**:
- [ ] 优化后的界面
- [ ] 部署文档
- [ ] 用户手册

---

## 🎯 详细实施方案

### 1. 数据库集成 (Day 1-2)

#### 1.1 检查现有模型

需要检查的模型:
- `Submission` - 作业提交
- `Assignment` - 作业
- `GradingResult` - 批改结果 (可能需要新增)

#### 1.2 更新Submission模型

```python
# app/models/submission.py
class Submission(Base):
    __tablename__ = "submissions"
    
    # 现有字段...
    
    # 新增Agent批改相关字段
    agent_grading_status: str = Column(String, default="pending")
    agent_grading_mode: str = Column(String, nullable=True)
    agent_score: float = Column(Float, nullable=True)
    agent_confidence: float = Column(Float, nullable=True)
    agent_errors: JSON = Column(JSON, nullable=True)
    agent_feedback: Text = Column(Text, nullable=True)
    agent_suggestions: JSON = Column(JSON, nullable=True)
    agent_knowledge_points: JSON = Column(JSON, nullable=True)
    agent_processing_time_ms: int = Column(Integer, nullable=True)
    agent_graded_at: DateTime = Column(DateTime, nullable=True)
```

#### 1.3 创建批改结果存储服务

```python
# app/services/grading_result_service.py
class GradingResultService:
    """批改结果存储服务"""
    
    async def save_grading_result(
        self,
        submission_id: UUID,
        result: GradingState
    ) -> Submission:
        """保存批改结果到数据库"""
        submission = await self.db.get(Submission, submission_id)
        
        submission.agent_grading_status = result["status"]
        submission.agent_score = result["score"]
        submission.agent_confidence = result["confidence"]
        submission.agent_errors = result["errors"]
        submission.agent_feedback = result["feedback_text"]
        submission.agent_suggestions = result["suggestions"]
        submission.agent_knowledge_points = result["knowledge_points"]
        submission.agent_processing_time_ms = result["processing_time_ms"]
        submission.agent_graded_at = datetime.now(UTC)
        
        await self.db.commit()
        return submission
```

---

### 2. WebSocket实时通知 (Day 3-4)

#### 2.1 进度事件定义

```python
# app/schemas/websocket.py
class GradingProgressEvent(BaseModel):
    """批改进度事件"""
    type: str = "grading_progress"
    submission_id: str
    status: str  # preprocessing, grading, reviewing, completed, failed
    progress: int  # 0-100
    message: str
    timestamp: datetime
```

#### 2.2 WebSocket推送实现

```python
# app/api/v1/grading_v2.py
async def grade_with_progress(
    submission_id: UUID,
    websocket_manager: WebSocketManager
):
    """带进度推送的批改"""
    
    # 1. 预处理阶段
    await websocket_manager.send_to_user(
        user_id,
        {
            "type": "grading_progress",
            "submission_id": str(submission_id),
            "status": "preprocessing",
            "progress": 20,
            "message": "正在处理文件..."
        }
    )
    
    # 2. 批改阶段
    await websocket_manager.send_to_user(
        user_id,
        {
            "type": "grading_progress",
            "submission_id": str(submission_id),
            "status": "grading",
            "progress": 60,
            "message": "正在批改..."
        }
    )
    
    # 3. 完成
    await websocket_manager.send_to_user(
        user_id,
        {
            "type": "grading_progress",
            "submission_id": str(submission_id),
            "status": "completed",
            "progress": 100,
            "message": "批改完成!"
        }
    )
```

---

### 3. 前端页面开发 (Day 6-7)

#### 3.1 页面结构

```
frontend/app/
├── (dashboard)/
│   ├── assignments/
│   │   └── [id]/
│   │       ├── page.tsx          # 作业详情
│   │       └── submit/
│   │           └── page.tsx      # 提交作业
│   └── submissions/
│       └── [id]/
│           ├── page.tsx          # 批改结果
│           └── grading/
│               └── page.tsx      # 批改进度
```

#### 3.2 作业提交页面

```typescript
// app/(dashboard)/assignments/[id]/submit/page.tsx
export default function SubmitAssignmentPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const handleSubmit = async () => {
    setIsSubmitting(true);
    
    // 1. 上传文件
    const uploadedFiles = await uploadFiles(files);
    
    // 2. 创建提交
    const submission = await createSubmission({
      assignment_id,
      files: uploadedFiles
    });
    
    // 3. 触发批改
    await triggerGrading(submission.id);
    
    // 4. 跳转到进度页面
    router.push(`/submissions/${submission.id}/grading`);
  };
  
  return (
    <div>
      <h1>提交作业</h1>
      <FileUpload onChange={setFiles} />
      <Button onClick={handleSubmit} disabled={isSubmitting}>
        提交并批改
      </Button>
    </div>
  );
}
```

#### 3.3 批改进度页面

```typescript
// app/(dashboard)/submissions/[id]/grading/page.tsx
export default function GradingProgressPage() {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("pending");
  const [message, setMessage] = useState("");
  
  useEffect(() => {
    // 连接WebSocket
    const ws = connectWebSocket();
    
    ws.on("grading_progress", (data) => {
      setProgress(data.progress);
      setStatus(data.status);
      setMessage(data.message);
      
      if (data.status === "completed") {
        router.push(`/submissions/${submissionId}`);
      }
    });
    
    return () => ws.disconnect();
  }, []);
  
  return (
    <div>
      <h1>批改中...</h1>
      <ProgressBar value={progress} />
      <p>{message}</p>
      <StatusIndicator status={status} />
    </div>
  );
}
```

#### 3.4 批改结果页面

```typescript
// app/(dashboard)/submissions/[id]/page.tsx
export default function SubmissionResultPage() {
  const { data: result } = useQuery({
    queryKey: ["submission", submissionId],
    queryFn: () => fetchSubmission(submissionId)
  });
  
  return (
    <div>
      <h1>批改结果</h1>
      
      {/* 分数卡片 */}
      <ScoreCard 
        score={result.agent_score}
        maxScore={result.max_score}
        confidence={result.agent_confidence}
      />
      
      {/* 错误列表 */}
      <ErrorList errors={result.agent_errors} />
      
      {/* 总体反馈 */}
      <FeedbackSection feedback={result.agent_feedback} />
      
      {/* 改进建议 */}
      <SuggestionsList suggestions={result.agent_suggestions} />
      
      {/* 知识点分析 */}
      <KnowledgePointsChart points={result.agent_knowledge_points} />
    </div>
  );
}
```

---

## 📊 技术栈

### 后端
- FastAPI - Web框架
- SQLAlchemy - ORM
- WebSocket - 实时通信
- LangGraph - Agent编排

### 前端
- Next.js 14 - React框架
- TypeScript - 类型安全
- TanStack Query - 数据获取
- Socket.io - WebSocket客户端
- Tailwind CSS - 样式
- shadcn/ui - UI组件

---

## ✅ 验收标准

### 功能验收
- [ ] 用户可以提交作业并触发批改
- [ ] 实时显示批改进度
- [ ] 批改结果正确显示
- [ ] 支持查看历史记录
- [ ] 错误处理完善

### 性能验收
- [ ] 批改时间 < 15秒
- [ ] API响应时间 < 500ms
- [ ] WebSocket延迟 < 100ms
- [ ] 页面加载时间 < 2秒

### 用户体验验收
- [ ] 界面美观
- [ ] 交互流畅
- [ ] 反馈及时
- [ ] 错误提示清晰

---

## 🎯 Phase 2 完成标准

1. ✅ 所有前端页面开发完成
2. ✅ 数据库集成测试通过
3. ✅ WebSocket实时通知正常
4. ✅ 端到端测试通过
5. ✅ 性能指标达标
6. ✅ 用户体验良好

---

**计划制定时间**: 2025-10-05  
**预计开始时间**: 2025-10-05  
**预计完成时间**: 2025-10-19  
**状态**: 待开始

