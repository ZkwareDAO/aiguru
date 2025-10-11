# Phase 2 详细实施方案

**制定日期**: 2025-10-05  
**实施周期**: 2周 (10个工作日)  
**当前状态**: 📋 计划中  

---

## 🎯 Phase 2 要做什么？

### 核心任务
Phase 2的核心任务是**将Phase 1开发的Agent批改系统集成到实际应用中**，让用户可以通过前端界面使用AI批改功能。

### 具体目标
1. **后端集成** - 将Agent系统与现有数据库、API集成
2. **前端开发** - 创建用户友好的批改界面
3. **实时反馈** - 实现批改进度的实时显示
4. **完整测试** - 端到端功能测试
5. **用户体验** - 优化交互流程

---

## 🔍 Phase 2 怎么做？

### 整体流程

```
用户提交作业 → 触发批改 → 实时进度 → 显示结果 → 查看历史
     ↓              ↓            ↓           ↓          ↓
  前端页面      API调用      WebSocket    结果页面   历史页面
     ↓              ↓            ↓           ↓          ↓
  文件上传      Agent编排    进度推送    数据展示   数据查询
     ↓              ↓            ↓           ↓          ↓
  数据库存储    批改执行     状态更新    结果存储   历史记录
```

---

## 📅 详细实施步骤

### Week 1: 后端完善 (Day 1-5)

#### 🔹 Day 1-2: 数据库集成

**要做什么**:
- 检查现有数据库模型
- 添加Agent批改相关字段
- 创建数据存储服务
- 测试数据读写

**怎么做**:

**步骤1**: 检查现有Submission模型
```bash
# 查看现有模型
cat backend/app/models/submission.py
```

**步骤2**: 添加Agent批改字段
```python
# 在Submission模型中添加:
agent_grading_status: str       # 批改状态
agent_score: float              # AI评分
agent_confidence: float         # 置信度
agent_errors: JSON              # 错误列表
agent_feedback: Text            # 总体反馈
agent_suggestions: JSON         # 改进建议
agent_knowledge_points: JSON    # 知识点分析
agent_processing_time_ms: int   # 处理时间
agent_graded_at: DateTime       # 批改时间
```

**步骤3**: 创建数据库迁移
```bash
cd backend
alembic revision --autogenerate -m "Add agent grading fields"
alembic upgrade head
```

**步骤4**: 创建存储服务
```python
# backend/app/services/grading_result_service.py
class GradingResultService:
    async def save_result(self, submission_id, result):
        # 保存批改结果到数据库
        pass
    
    async def get_result(self, submission_id):
        # 获取批改结果
        pass
```

**步骤5**: 测试数据库操作
```python
# 创建测试脚本
python backend/scripts/test_db_integration.py
```

**产出**:
- ✅ 更新的数据库模型
- ✅ 数据库迁移文件
- ✅ 存储服务代码
- ✅ 测试脚本

---

#### 🔹 Day 3-4: WebSocket实时通知

**要做什么**:
- 检查现有WebSocket实现
- 添加批改进度事件
- 实现进度推送
- 测试实时通知

**怎么做**:

**步骤1**: 检查现有WebSocket
```bash
cat backend/app/api/websocket.py
```

**步骤2**: 定义进度事件
```python
# backend/app/schemas/websocket.py
class GradingProgressEvent(BaseModel):
    type: str = "grading_progress"
    submission_id: str
    status: str  # preprocessing, grading, completed, failed
    progress: int  # 0-100
    message: str
```

**步骤3**: 修改Agent编排器，添加进度回调
```python
# backend/app/agents/smart_orchestrator.py
class SmartOrchestrator:
    async def run_with_progress(
        self,
        state: GradingState,
        progress_callback: Callable
    ):
        # 预处理
        await progress_callback(20, "preprocessing", "正在处理文件...")
        
        # 批改
        await progress_callback(60, "grading", "正在批改...")
        
        # 完成
        await progress_callback(100, "completed", "批改完成!")
```

**步骤4**: 更新API，集成WebSocket
```python
# backend/app/api/v1/grading_v2.py
@router.post("/submit")
async def submit_grading(
    request: GradingRequest,
    background_tasks: BackgroundTasks,
    websocket_manager: WebSocketManager = Depends(get_websocket_manager)
):
    # 后台任务中执行批改
    background_tasks.add_task(
        grade_with_progress,
        request.submission_id,
        websocket_manager
    )
```

**步骤5**: 测试WebSocket
```python
# 创建WebSocket测试客户端
python backend/scripts/test_websocket.py
```

**产出**:
- ✅ 进度事件定义
- ✅ 进度推送逻辑
- ✅ 更新的API
- ✅ WebSocket测试

---

#### 🔹 Day 5: API完善与文档

**要做什么**:
- 完善grading_v2 API
- 添加错误处理
- 生成API文档
- 编写使用示例

**怎么做**:

**步骤1**: 完善API端点
```python
# 确保以下端点完整:
POST   /v2/grading/submit        # 提交批改
GET    /v2/grading/result/{id}   # 获取结果
GET    /v2/grading/status/{id}   # 获取状态
GET    /v2/grading/history        # 历史记录
DELETE /v2/grading/cancel/{id}   # 取消批改
```

**步骤2**: 添加错误处理
```python
try:
    result = await orchestrator.run(state)
except Exception as e:
    logger.error(f"Grading failed: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"批改失败: {str(e)}"
    )
```

**步骤3**: 生成API文档
```bash
# FastAPI自动生成文档
# 访问 http://localhost:8000/docs
```

**步骤4**: 编写使用示例
```python
# backend/docs/API_EXAMPLES.md
# 包含各个端点的使用示例
```

**产出**:
- ✅ 完善的API
- ✅ 错误处理
- ✅ API文档
- ✅ 使用示例

---

### Week 2: 前端开发 (Day 6-10)

#### 🔹 Day 6-7: 前端页面开发

**要做什么**:
- 创建作业提交页面
- 创建批改进度页面
- 创建批改结果页面
- 创建历史记录页面

**怎么做**:

**步骤1**: 创建页面结构
```bash
mkdir -p frontend/app/\(dashboard\)/assignments/[id]/submit
mkdir -p frontend/app/\(dashboard\)/submissions/[id]/grading
```

**步骤2**: 开发作业提交页面
```typescript
// frontend/app/(dashboard)/assignments/[id]/submit/page.tsx
- 文件上传组件
- 提交按钮
- 加载状态
- 错误提示
```

**步骤3**: 开发批改进度页面
```typescript
// frontend/app/(dashboard)/submissions/[id]/grading/page.tsx
- 进度条
- 状态指示器
- 实时消息
- WebSocket连接
```

**步骤4**: 开发批改结果页面
```typescript
// frontend/app/(dashboard)/submissions/[id]/page.tsx
- 分数卡片
- 错误列表
- 反馈区域
- 建议列表
- 知识点图表
```

**步骤5**: 开发历史记录页面
```typescript
// frontend/app/(dashboard)/submissions/page.tsx
- 提交列表
- 筛选功能
- 分页
- 详情链接
```

**产出**:
- ✅ 4个前端页面
- ✅ UI组件
- ✅ 样式文件

---

#### 🔹 Day 8: 前端API集成

**要做什么**:
- 创建API客户端
- 实现数据获取
- 集成WebSocket
- 处理错误状态

**怎么做**:

**步骤1**: 创建API客户端
```typescript
// frontend/lib/api/grading.ts
export const gradingApi = {
  submit: (data) => fetch('/api/v2/grading/submit', ...),
  getResult: (id) => fetch(`/api/v2/grading/result/${id}`, ...),
  getStatus: (id) => fetch(`/api/v2/grading/status/${id}`, ...),
};
```

**步骤2**: 创建React Query hooks
```typescript
// frontend/hooks/useGrading.ts
export function useSubmitGrading() {
  return useMutation({
    mutationFn: gradingApi.submit,
  });
}

export function useGradingResult(id: string) {
  return useQuery({
    queryKey: ['grading', id],
    queryFn: () => gradingApi.getResult(id),
  });
}
```

**步骤3**: 集成WebSocket
```typescript
// frontend/hooks/useGradingProgress.ts
export function useGradingProgress(submissionId: string) {
  const [progress, setProgress] = useState(0);
  
  useEffect(() => {
    const socket = io();
    socket.on('grading_progress', (data) => {
      if (data.submission_id === submissionId) {
        setProgress(data.progress);
      }
    });
    return () => socket.disconnect();
  }, [submissionId]);
  
  return progress;
}
```

**步骤4**: 错误处理
```typescript
// 统一错误处理
if (error) {
  return <ErrorMessage error={error} />;
}
```

**产出**:
- ✅ API客户端
- ✅ React Query hooks
- ✅ WebSocket集成
- ✅ 错误处理

---

#### 🔹 Day 9: 端到端测试

**要做什么**:
- 测试完整批改流程
- 测试实时进度
- 测试错误处理
- 性能测试

**怎么做**:

**步骤1**: 手动测试完整流程
```
1. 登录系统
2. 选择作业
3. 上传文件
4. 提交批改
5. 查看进度
6. 查看结果
7. 查看历史
```

**步骤2**: 自动化测试
```typescript
// frontend/tests/e2e/grading.spec.ts
test('complete grading flow', async ({ page }) => {
  await page.goto('/assignments/123/submit');
  await page.setInputFiles('input[type=file]', 'test.pdf');
  await page.click('button:has-text("提交")');
  await expect(page).toHaveURL(/\/grading/);
  await expect(page.locator('.progress')).toBeVisible();
});
```

**步骤3**: 性能测试
```bash
# 使用k6或artillery进行负载测试
k6 run backend/tests/load/grading_load_test.js
```

**产出**:
- ✅ 测试报告
- ✅ Bug列表
- ✅ 性能报告

---

#### 🔹 Day 10: 优化与部署准备

**要做什么**:
- UI/UX优化
- 性能优化
- 文档完善
- 部署准备

**怎么做**:

**步骤1**: UI/UX优化
- 调整样式
- 优化动画
- 改进交互
- 响应式设计

**步骤2**: 性能优化
- 代码分割
- 懒加载
- 缓存优化
- 图片优化

**步骤3**: 文档完善
- 用户手册
- 开发文档
- API文档
- 部署文档

**步骤4**: 部署准备
- 环境变量配置
- 数据库迁移
- 依赖检查
- 部署脚本

**产出**:
- ✅ 优化后的应用
- ✅ 完整文档
- ✅ 部署脚本

---

## 📊 技术实施细节

### 后端技术栈
```
FastAPI          - Web框架
SQLAlchemy       - ORM
Alembic          - 数据库迁移
WebSocket        - 实时通信
LangGraph        - Agent编排
PostgreSQL       - 数据库
Redis            - 缓存
```

### 前端技术栈
```
Next.js 14       - React框架
TypeScript       - 类型安全
TanStack Query   - 数据获取
Socket.io        - WebSocket客户端
Tailwind CSS     - 样式
shadcn/ui        - UI组件
```

---

## ✅ 验收标准

### 功能验收
- [ ] 用户可以提交作业并触发批改
- [ ] 实时显示批改进度 (WebSocket)
- [ ] 批改结果正确显示
- [ ] 支持查看历史记录
- [ ] 错误处理完善
- [ ] 数据正确存储到数据库

### 性能验收
- [ ] 批改时间 < 15秒
- [ ] API响应时间 < 500ms
- [ ] WebSocket延迟 < 100ms
- [ ] 页面加载时间 < 2秒
- [ ] 并发10个请求无错误

### 用户体验验收
- [ ] 界面美观
- [ ] 交互流畅
- [ ] 反馈及时
- [ ] 错误提示清晰
- [ ] 移动端适配

---

## 🎯 Phase 2 完成标准

1. ✅ 所有后端集成完成
2. ✅ 所有前端页面开发完成
3. ✅ 数据库集成测试通过
4. ✅ WebSocket实时通知正常
5. ✅ 端到端测试通过
6. ✅ 性能指标达标
7. ✅ 用户体验良好
8. ✅ 文档完整

---

## 📝 总结

### Phase 2 要做什么？
**将Agent批改系统集成到实际应用中，让用户可以使用**

### Phase 2 怎么做？
**分两周完成:**
- **Week 1**: 后端集成 (数据库、WebSocket、API)
- **Week 2**: 前端开发 (页面、集成、测试)

### 关键步骤
1. 数据库添加Agent字段
2. WebSocket实现进度推送
3. 前端创建4个页面
4. API客户端集成
5. 端到端测试

### 预期成果
- 完整的批改功能
- 实时进度显示
- 友好的用户界面
- 良好的性能表现

---

**计划制定**: 2025-10-05  
**预计工期**: 10个工作日  
**状态**: 📋 待开始

