# AI自动批改系统 - 设计文档集

> 基于LangChain/LangGraph的智能批改系统完整设计文档

---

## 📚 文档目录

### 🎯 [00. 设计总览](./00_DESIGN_OVERVIEW.md)
**快速了解整个系统的设计理念和架构**

- 文档导航指南
- 系统架构概览
- 核心技术栈
- 关键指标
- 实施路线图
- 设计原则

👉 **推荐所有人首先阅读此文档**

---

### 📋 [01. 需求文档](./01_REQUIREMENTS_DOCUMENT.md)
**详细的业务需求和功能规格说明**

- 系统概述与目标
- 用户角色与需求(教师、学生、管理员)
- 核心功能需求
  - 作业管理模块
  - AI批改模块
  - 任务调度模块
  - 学习分析模块
- 非功能性需求(性能、可靠性、安全性)
- 技术约束与成功标准
- 风险评估与项目里程碑

**适合**: 产品经理、项目经理、开发团队、测试团队

---

### 🏗️ [02. Agent架构设计](./02_AGENT_ARCHITECTURE_DESIGN.md)
**LangGraph多Agent协作架构的核心设计**

- 架构概览与设计理念
- Agent层次结构
- 详细的Agent设计
  - **OrchestratorAgent** - 编排器
  - **PreprocessAgent** - 预处理器
  - **GradingAgent** - 批改器
  - **ReviewAgent** - 审核器
  - **FeedbackAgent** - 反馈生成器
- 状态管理与工作流设计
- Agent实现细节与代码示例

**适合**: 架构师、后端开发工程师、AI工程师

**关键亮点**:
```python
# LangGraph工作流示例
workflow = StateGraph(GradingState)
workflow.add_node("preprocess", preprocess_agent.process)
workflow.add_node("grade", grading_agent.process)
workflow.add_node("review", review_agent.process)
workflow.add_conditional_edges("grade", should_review, {...})
```

---

### 🤝 [03. 协作策略](./03_COLLABORATION_STRATEGY.md)
**Agent之间的通信、协作和错误处理机制**

- 协作模式设计
  - 线性Pipeline模式
  - 并行处理模式
  - 条件分支模式
- 通信机制
  - 状态共享
  - 消息传递
  - 消息总线
- 数据流转设计
- 错误处理与恢复
  - 重试策略
  - 降级策略
  - 断点续传
- 并发控制与限流

**适合**: 后端开发工程师、系统架构师

**关键亮点**:
```python
# 指数退避重试
@with_retry(max_retries=3)
async def call_llm(prompt: str):
    return await llm.ainvoke(prompt)

# 优雅降级
await execute_with_fallback(
    primary_func=detailed_review,
    fallback_func=simple_review
)
```

---

### 🚀 [04. 可扩展性与可靠性](./04_SCALABILITY_RELIABILITY.md)
**系统的扩展性设计和可靠性保障**

- 可扩展性设计
  - 水平扩展架构
  - 分布式任务队列
  - 动态Worker扩缩容
  - 数据库读写分离与分片
- 可靠性保障
  - 数据一致性(分布式锁、幂等性)
  - 故障恢复与自动恢复
  - 健康检查
- 高可用架构
  - 服务降级
  - 熔断器
  - 限流保护
- 性能优化
  - 多级缓存
  - 查询优化

**适合**: 系统架构师、运维工程师、后端开发工程师

**关键亮点**:
```python
# 动态Worker扩缩容
class WorkerPool:
    async def _auto_scale(self):
        if load_ratio > threshold:
            await self._spawn_worker()  # 扩容
        elif load_ratio < threshold:
            await self._stop_worker()   # 缩容

# 分布式锁
async with DistributedLock(redis, f"submission:{id}"):
    # 原子操作
    pass
```

---

### 🎨 [05. 用户体验设计](./05_USER_EXPERIENCE_DESIGN.md)
**前端界面设计和用户交互流程**

- 用户界面设计
  - 教师端界面(作业管理、批改管理、结果审核)
  - 学生端界面(作业提交、结果查看)
- 实时反馈机制
  - WebSocket通信
  - 进度追踪
  - 通知系统
- 响应式设计与移动端适配
- 性能优化
  - 虚拟滚动
  - 图片懒加载

**适合**: 前端开发工程师、UI/UX设计师、产品经理

**关键亮点**:
```tsx
// 实时进度追踪
<RealTimeProgressTracker taskId={taskId} />

// 交互式错误标注
<CoordinateAnnotationView 
  imageUrl={originalImage}
  annotations={annotations}
  onAnnotationClick={handleClick}
/>
```

---

### 🎭 [06. 前端Mock实现](./06_FRONTEND_MOCK_IMPLEMENTATION.md)
**前端开发的Mock数据和API实现**

- Mock数据结构设计
  - 用户、作业、提交、批改结果等完整数据模型
- Mock数据生成器
  - 使用Faker.js生成真实的测试数据
- Mock API实现
  - 模拟网络延迟
  - 模拟随机失败
  - 完整的CRUD操作
- Mock WebSocket实现
  - 实时进度更新
  - 批改完成通知
- 开发工作流
  - Mock开关配置
  - 开发模式切换

**适合**: 前端开发工程师

**关键亮点**:
```typescript
// Mock数据工厂
const assignment = MockDataFactory.createAssignment({
  title: "数学作业",
  dueDate: "2025-10-10"
});

// Mock API with delay
await mockAPI.getAssignments({ page: 1, pageSize: 10 });

// Mock WebSocket
mockWS.subscribe('grading_completed', (data) => {
  showNotification(data.message);
});
```

---

### 💻 [07. 实现指南](./07_IMPLEMENTATION_GUIDE.md)
**基于设计文档的具体实现指南**

- LangGraph Agent实现
  - 环境准备
  - 状态定义
  - Agent实现示例
  - Orchestrator实现
- API集成
- 数据库模型
- 测试策略

**适合**: 所有开发工程师

**关键亮点**:
```python
# 完整的Agent实现示例
class PreprocessAgent:
    async def process(self, state: GradingState) -> GradingState:
        # 1. 获取文件
        files = await self.file_service.get_submission_files(...)
        
        # 2. 处理文件
        preprocessed = await self._process_files(files)
        
        # 3. 更新状态
        state["preprocessed_files"] = preprocessed
        return state
```

---

### 💡 [08. 设计讨论](./08_DESIGN_DISCUSSION.md)
**设计决策的权衡分析和最佳实践**

- Agent架构设计讨论
  - 为什么选择LangGraph?
  - Agent粒度如何划分?
  - 同步 vs 异步处理?
- 可扩展性设计讨论
  - 如何防止系统过载?
  - 如何保证批改顺序不混乱?
- 用户体验设计讨论
  - 实时反馈 vs 批量通知?
  - 坐标标注 vs 局部图卡片?
- 性能优化讨论
  - 缓存策略如何设计?
  - 数据库查询如何优化?
- 安全性讨论
  - 如何防止恶意提交?
- 成本优化讨论
  - 如何降低AI API成本?

**适合**: 所有团队成员

**关键亮点**: 深入分析每个设计决策的利弊,提供实用的建议

---

### 💰 [09. 成本优化策略](./09_COST_OPTIMIZATION_STRATEGY.md)
**详细的Agent成本分析和优化方案**

- 成本分析
  - 各Agent的成本结构
  - 月度成本估算
- 优化方案
  - **Agent融合**: 一次LLM调用完成多个任务(节省23%)
  - **智能模式选择**: 根据复杂度选择Agent组合(节省40%)
  - **批量处理**: 合并多份作业到一次调用(节省60%)
  - **智能缓存**: 缓存相似问题的结果(节省30%)
- 实施策略
  - 阶段1: 立即实施(节省~40%)
  - 阶段2: 中期优化(节省~60%)
  - 阶段3: 长期优化(节省~80%)
- 成本对比总结

**适合**: 架构师、后端开发工程师、产品经理

**关键亮点**:
```python
# 智能Agent融合
class UnifiedGradingAgent:
    async def process(self, state):
        # 一次LLM调用完成批改+反馈
        # 成本: $0.010 (vs 原设计 $0.013)
        return await self.unified_grading(state)

# 智能模式选择
if complexity == "simple":
    result = await unified_agent.process()  # $0.005
elif complexity == "medium":
    result = await standard_pipeline()     # $0.009
else:
    result = await full_pipeline()         # $0.015
```

---

### 🚀 [10. 阶段一实施计划](./10_PHASE1_IMPLEMENTATION_PLAN.md)
**2周完成基础功能的详细实施计划**

- 时间安排
  - Week 1: 后端核心功能 (Day 1-7)
  - Week 2: 前端界面与测试 (Day 8-10)
- 详细任务分解
  - **Day 1-2**: 环境搭建与基础架构
  - **Day 3-4**: UnifiedGradingAgent实现
  - **Day 5-6**: 智能模式选择与缓存
  - **Day 7**: API接口实现
  - **Day 8**: 前端基础界面
  - **Day 9**: Mock数据实现
  - **Day 10**: 集成测试与验收
- 每日检查清单
- 验收标准
- 快速启动指南
- 常见问题解答

**适合**: 所有开发人员

**关键亮点**:
```python
# Day 3-4: UnifiedGradingAgent
class UnifiedGradingAgent:
    async def process(self, state: GradingState):
        # 一次LLM调用完成批改+反馈
        prompt = self._build_unified_prompt(state)
        response = await self.llm.ainvoke(prompt)
        return self._parse_result(response)

# Day 5-6: SmartOrchestrator
class SmartOrchestrator:
    async def execute(self, input_data):
        complexity = await self._assess_complexity(input_data)
        if complexity == "simple":
            return await self.unified_agent.process()
        # ...
```

**预期成果**:
- ✅ 完成单份批改功能
- ✅ 成本降低40%
- ✅ 批改时间 < 15秒
- ✅ 基础前端界面

---

## 🚀 快速开始

### 第一次阅读建议

**如果你是产品经理/项目经理**:
1. [00. 设计总览](./00_DESIGN_OVERVIEW.md) - 了解整体架构
2. [01. 需求文档](./01_REQUIREMENTS_DOCUMENT.md) - 了解详细需求
3. [05. 用户体验设计](./05_USER_EXPERIENCE_DESIGN.md) - 了解界面设计

**如果你是架构师**:
1. [00. 设计总览](./00_DESIGN_OVERVIEW.md) - 了解整体架构
2. [02. Agent架构设计](./02_AGENT_ARCHITECTURE_DESIGN.md) - 了解核心架构
3. [09. 成本优化策略](./09_COST_OPTIMIZATION_STRATEGY.md) - ⭐ 了解成本控制
4. [03. 协作策略](./03_COLLABORATION_STRATEGY.md) - 了解Agent协作
5. [04. 可扩展性与可靠性](./04_SCALABILITY_RELIABILITY.md) - 了解系统保障
6. [08. 设计讨论](./08_DESIGN_DISCUSSION.md) - 了解设计权衡

**如果你是后端开发工程师**:
1. [02. Agent架构设计](./02_AGENT_ARCHITECTURE_DESIGN.md) - 了解Agent实现
2. [09. 成本优化策略](./09_COST_OPTIMIZATION_STRATEGY.md) - ⭐ 了解成本优化
3. [03. 协作策略](./03_COLLABORATION_STRATEGY.md) - 了解通信机制
4. [07. 实现指南](./07_IMPLEMENTATION_GUIDE.md) - 开始编码
5. [04. 可扩展性与可靠性](./04_SCALABILITY_RELIABILITY.md) - 了解系统设计

**如果你是前端开发工程师**:
1. [05. 用户体验设计](./05_USER_EXPERIENCE_DESIGN.md) - 了解界面设计
2. [06. 前端Mock实现](./06_FRONTEND_MOCK_IMPLEMENTATION.md) - 开始开发
3. [08. 设计讨论](./08_DESIGN_DISCUSSION.md) - 了解UX决策

**如果你是AI工程师**:
1. [02. Agent架构设计](./02_AGENT_ARCHITECTURE_DESIGN.md) - 了解Agent设计
2. [03. 协作策略](./03_COLLABORATION_STRATEGY.md) - 了解工作流
3. [07. 实现指南](./07_IMPLEMENTATION_GUIDE.md) - 实现Agent

---

## 📊 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  教师端界面  │  │  学生端界面  │  │  管理端界面  │      │
│  │  Next.js     │  │  Next.js     │  │  Next.js     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      API网关层                               │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │   FastAPI Gateway    │  │   WebSocket Server   │        │
│  │   (REST API)         │  │   (实时通信)          │        │
│  └──────────────────────┘  └──────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   业务逻辑层 (LangGraph)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           OrchestratorAgent (编排器)                  │  │
│  └──────────────────────────────────────────────────────┘  │
│         ↓              ↓              ↓              ↓      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Preprocess│  │ Grading  │  │  Review  │  │ Feedback │  │
│  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    任务调度层                                │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │   Redis Task Queue   │  │   Worker Pool        │        │
│  │   (优先级队列)        │  │   (动态扩缩容)        │        │
│  └──────────────────────┘  └──────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      数据层                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │PostgreSQL│  │  Redis   │  │   S3     │                 │
│  │(主从复制)│  │(缓存+队列)│  │(文件存储)│                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    外部服务                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │   OpenRouter API     │  │   OCR Service        │        │
│  │   (AI模型)           │  │   (文字识别)          │        │
│  └──────────────────────┘  └──────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 核心特性

### ✨ 智能批改
- 基于LangGraph的多Agent协作
- 支持文本、图片、PDF等多种格式
- 自动错误检测和标注
- 智能评分和反馈生成

### 🚀 高性能
- 异步任务处理
- 分布式任务队列
- 动态Worker扩缩容
- 多级缓存策略

### 🛡️ 高可靠
- 完善的错误处理和重试机制
- 断点续传支持
- 数据一致性保障
- 自动故障恢复

### 📱 优秀体验
- 实时进度追踪
- WebSocket实时通知
- 响应式设计
- 移动端友好

---

## 📈 关键指标

| 指标类型 | 目标值 | 说明 |
|---------|--------|------|
| 单份批改时间 | < 30秒 | 从提交到完成 |
| 批量批改(100份) | < 10分钟 | 并发处理 |
| API响应时间 | < 500ms | P95 |
| 系统可用性 | 99.9% | 年停机 < 8.76小时 |
| 批改准确率 | > 90% | 与人工批改对比 |
| 并发处理能力 | 100+ 任务 | 同时处理 |

---

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI (Python 3.11+)
- **AI框架**: LangChain, LangGraph
- **数据库**: PostgreSQL 15+
- **缓存**: Redis 7+
- **任务队列**: Redis Streams
- **AI模型**: OpenRouter API

### 前端
- **框架**: Next.js 14+ (App Router)
- **UI库**: React 18+, TypeScript
- **状态管理**: Zustand / React Query
- **UI组件**: shadcn/ui, Tailwind CSS
- **实时通信**: WebSocket

### 基础设施
- **容器化**: Docker, Docker Compose
- **部署**: Railway / Vercel
- **CI/CD**: GitHub Actions
- **监控**: Prometheus + Grafana

---

## 📝 更新日志

### v3.2 (2025-10-05) - 阶段一实施计划
- ✅ 新增阶段一实施计划文档(10_PHASE1_IMPLEMENTATION_PLAN.md)
- ✅ 详细的2周实施时间表
- ✅ 每日任务分解与代码示例
- ✅ 完整的检查清单与验收标准
- ✅ 快速启动指南与常见问题解答
- ✅ 可视化时间线与任务依赖图

### v3.1 (2025-10-05) - 成本优化专题
- ✅ 新增成本优化策略文档(09_COST_OPTIMIZATION_STRATEGY.md)
- ✅ 详细分析各Agent的成本结构
- ✅ 提供4种优化方案(Agent融合、智能模式、批量处理、智能缓存)
- ✅ 更新Agent架构设计文档,添加成本考虑
- ✅ 提供分阶段实施策略,可节省40-80%成本

### v3.0 (2025-10-05)
- ✅ 完成完整的设计文档系列(8篇)
- ✅ 添加LangGraph Agent架构设计
- ✅ 添加协作策略和可靠性设计
- ✅ 添加用户体验设计和Mock实现
- ✅ 添加实现指南和设计讨论

---

## 🤝 贡献指南

欢迎贡献!如果您发现文档中的问题或有改进建议:

1. 创建Issue描述问题
2. 提交Pull Request更新文档
3. 确保文档格式一致
4. 添加必要的代码示例

---

## 📞 联系方式

如有任何问题或建议,请通过以下方式联系:
- **Issue**: 在GitHub仓库创建Issue
- **Email**: [项目邮箱]
- **文档**: 查看相关设计文档

---

## 📄 许可证

[MIT License](../LICENSE)

---

**祝您开发顺利!** 🎉

如有疑问,请随时查阅相关文档或联系团队成员。

