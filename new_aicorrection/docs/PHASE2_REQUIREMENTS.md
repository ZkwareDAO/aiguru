# 📋 Phase 2 完整需求文档

**项目名称**: AI作业批改系统 - Phase 2 前端集成与完整测试  
**文档版本**: v2.0  
**制定日期**: 2025-10-05  
**预计工期**: 10个工作日  
**当前状态**: 📝 需求文档已完成  

---

## 📑 目录

1. [项目概述](#1-项目概述)
2. [Phase 1 回顾](#2-phase-1-回顾)
3. [Phase 2 目标](#3-phase-2-目标)
4. [核心功能需求](#4-核心功能需求)
5. [技术架构设计](#5-技术架构设计)
6. [Agent系统设计](#6-agent系统设计)
7. [数据库设计](#7-数据库设计)
8. [API设计](#8-api设计)
9. [前端设计](#9-前端设计)
10. [实施计划](#10-实施计划)
11. [验收标准](#11-验收标准)
12. [风险评估](#12-风险评估)
13. [成本分析](#13-成本分析)

---

## 1. 项目概述

### 1.1 背景

Phase 1已完成Agent批改系统的核心开发，包括:
- ✅ UnifiedGradingAgent - 统一批改Agent
- ✅ ComplexityAssessor - 复杂度评估器
- ✅ SmartOrchestrator - 智能编排器
- ✅ CacheService - 智能缓存服务
- ✅ API接口 - 5个RESTful端点

Phase 2的目标是将这套系统集成到实际应用中，让用户可以使用。

### 1.2 Phase 2 核心价值

**让AI批改系统真正可用**:
- 用户可以提交作业并查看批改结果
- 教师可以手动批注和调整
- 支持多页多题的复杂作业
- 提供清晰直观的批改展示

### 1.3 关键创新点

1. **多Agent协作** - PreprocessAgent + GradingAgent + LocationAgent
2. **精确位置标注** - 使用Gemini 2.5 Flash Lite进行像素级定位
3. **多页多题导航** - 三栏布局 + 智能导航
4. **教师批注工具** - 完整的手动批注功能
5. **响应式设计** - 桌面端和移动端不同体验

---

## 2. Phase 1 回顾

### 2.1 已完成的工作

| 模块 | 状态 | 说明 |
|------|------|------|
| UnifiedGradingAgent | ✅ 100% | 统一批改Agent，节省23%成本 |
| ComplexityAssessor | ✅ 100% | 6维度复杂度评估 |
| SmartOrchestrator | ✅ 100% | LangGraph编排器 |
| CacheService | ✅ 100% | 智能缓存服务 |
| API接口 | ✅ 100% | 5个RESTful端点 |
| 测试脚本 | ✅ 100% | 单元测试 + 集成测试 |
| 文档 | ✅ 100% | 17篇文档，60000字 |

### 2.2 测试结果

```
✅ 批改功能: 正常
✅ 复杂度评估: 准确
✅ 成本验证: $0.000043/题 (节省99.7%)
✅ 性能: 平均3秒
✅ 代码质量: 优秀
```

### 2.3 待完成的工作

- ⏳ 数据库集成
- ⏳ WebSocket实时通知
- ⏳ 前端页面开发
- ⏳ 位置标注Agent
- ⏳ 多页多题支持
- ⏳ 教师批注工具

---

## 3. Phase 2 目标

### 3.1 总体目标

**将Agent批改系统集成到实际应用中，提供完整的用户体验**

### 3.2 具体目标

#### 3.2.1 功能目标

1. **用户可以提交作业** - 上传图片，触发批改
2. **实时查看进度** - WebSocket推送批改进度
3. **查看批改结果** - 清晰展示分数、错误、反馈
4. **多页多题支持** - 支持10页以上、15题以上的作业
5. **精确位置标注** - 在原图上精确标注错误位置
6. **教师批注** - 教师可以手动批注和调整
7. **历史记录** - 查看所有提交的批改记录

#### 3.2.2 性能目标

| 指标 | 目标值 |
|------|--------|
| 批改时间 | < 20秒 (15题) |
| API响应时间 | < 500ms |
| WebSocket延迟 | < 100ms |
| 页面加载时间 | < 2秒 |
| 并发支持 | 10个请求无错误 |

#### 3.2.3 准确度目标

| 指标 | 目标值 |
|------|--------|
| 题目分段准确度 | > 90% |
| 批改准确度 | > 95% |
| 位置标注准确度 | > 80% |
| 低置信度标注 | < 20% |

#### 3.2.4 用户体验目标

- 界面美观，符合现代设计规范
- 交互流畅，无卡顿
- 反馈及时，有进度提示
- 错误提示清晰，有解决方案
- 移动端适配良好

---

## 4. 核心功能需求

### 4.1 功能模块概览

```
┌─────────────────────────────────────────────────┐
│                 AI批改系统                      │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐  ┌──────────────┐            │
│  │ 作业提交模块 │  │ 批改处理模块 │            │
│  └──────────────┘  └──────────────┘            │
│         │                  │                     │
│         ↓                  ↓                     │
│  ┌──────────────┐  ┌──────────────┐            │
│  │ 进度查看模块 │  │ 结果展示模块 │            │
│  └──────────────┘  └──────────────┘            │
│         │                  │                     │
│         ↓                  ↓                     │
│  ┌──────────────┐  ┌──────────────┐            │
│  │ 历史记录模块 │  │ 教师批注模块 │            │
│  └──────────────┘  └──────────────┘            │
│                                                  │
└─────────────────────────────────────────────────┘
```

### 4.2 功能详细需求

#### 4.2.1 作业提交模块

**功能描述**: 用户上传作业图片，触发批改

**用户故事**:
```
作为学生，
我想要上传我的作业图片，
以便获得AI批改和反馈。
```

**功能点**:
1. 文件上传
   - 支持格式: JPG, PNG, PDF
   - 单个文件大小: < 10MB
   - 多文件上传: 支持，最多20个文件
   - 拖拽上传: 支持
   - 预览功能: 上传前可预览

2. 作业信息填写
   - 选择作业: 从作业列表中选择
   - 备注: 可选，最多200字

3. 提交验证
   - 文件格式验证
   - 文件大小验证
   - 作业选择验证
   - 重复提交检测

4. 提交反馈
   - 上传进度条
   - 上传成功提示
   - 自动跳转到进度页面

**界面原型**:
```
┌─────────────────────────────────────┐
│ 提交作业                            │
├─────────────────────────────────────┤
│ 选择作业: [下拉选择]                │
│                                      │
│ 上传文件:                            │
│ ┌─────────────────────────────────┐ │
│ │  拖拽文件到这里                  │ │
│ │  或点击选择文件                  │ │
│ │  支持: JPG, PNG, PDF             │ │
│ │  最多20个文件，每个<10MB         │ │
│ └─────────────────────────────────┘ │
│                                      │
│ 已选择文件:                          │
│ • page1.jpg (2.3MB) [删除]          │
│ • page2.jpg (1.8MB) [删除]          │
│                                      │
│ 备注 (可选):                         │
│ ┌─────────────────────────────────┐ │
│ │                                  │ │
│ └─────────────────────────────────┘ │
│                                      │
│ [取消]  [提交并批改]                │
└─────────────────────────────────────┘
```

**API需求**:
```typescript
POST /api/v2/submissions
Content-Type: multipart/form-data

Request:
{
  assignmentId: string;
  files: File[];
  note?: string;
}

Response: 201 Created
{
  submissionId: string;
  status: "processing";
  message: "作业已提交，正在批改中...";
}
```

#### 4.2.2 批改处理模块

**功能描述**: 后台处理批改任务，使用Multi-Agent协作

**处理流程**:
```
用户提交作业
    ↓
[1] 文件上传到云存储
    ↓
[2] 创建Submission记录
    ↓
[3] 触发批改任务 (后台)
    ├─ Agent 1: PreprocessAgent - 题目分段
    ├─ Agent 2: GradingAgent - 批改识别
    └─ Agent 3: LocationAgent - 位置标注
    ↓
[4] 保存批改结果到数据库
    ↓
[5] 推送完成通知 (WebSocket)
```

**Agent协作流程**:
```typescript
// LangGraph状态机
const workflow = new StateGraph<GradingState>({
  channels: {
    submissionId: null,
    images: null,
    questionSegments: null,      // Agent 1 输出
    gradingResults: null,         // Agent 2 输出
    annotatedResults: null,       // Agent 3 输出
    finalResult: null,
    error: null,
  },
});

// 节点定义
workflow.addNode('preprocess', preprocessNode);
workflow.addNode('grade', gradeNode);
workflow.addNode('annotate', annotateNode);
workflow.addNode('finalize', finalizeNode);

// 流程定义
workflow.addEdge('__start__', 'preprocess');
workflow.addEdge('preprocess', 'grade');
workflow.addEdge('grade', 'annotate');
workflow.addEdge('annotate', 'finalize');
workflow.addEdge('finalize', '__end__');
```

**进度推送**:
```typescript
// WebSocket事件
{
  type: "grading_progress",
  submissionId: "uuid",
  stage: "preprocessing" | "grading" | "annotating" | "completed",
  progress: 0-100,
  message: "正在处理第3题...",
  timestamp: "2025-10-05T10:30:00Z"
}
```

#### 4.2.3 进度查看模块

**功能描述**: 实时显示批改进度

**界面原型**:
```
┌─────────────────────────────────────┐
│ 批改中...                           │
├─────────────────────────────────────┤
│  [████████████░░░░░░] 60%           │
│                                      │
│  当前阶段: 批改中                    │
│  正在批改第9题...                    │
│                                      │
│  预计剩余时间: 10秒                  │
│                                      │
│  已完成:                             │
│  ✅ 预处理 (识别到15个题目)          │
│  ✅ 批改 (已批改8题)                 │
│  ⏳ 位置标注 (进行中...)             │
│                                      │
│  [取消批改]                          │
└─────────────────────────────────────┘
```

#### 4.2.4 结果展示模块

**功能描述**: 展示批改结果，支持多页多题

**桌面端布局详细**:
```
┌─────────────────────────────────────────────────────────────┐
│ 批改结果 | 得分: 85/100 | 错误: 8个 | [✏️ 批注模式]        │
├─────────────────────────────────────────────────────────────┤
│ ┌────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│ │ 📑 目录│  │ 📄 作业图片      │  │ 📝 批改详情      │    │
│ │        │  │                  │  │                  │    │
│ │ 📊总览 │  │  [第2页-第3题]   │  │ 当前: 第3题      │    │
│ │ 10页   │  │  ┌────────────┐  │  │                  │    │
│ │ 15题   │  │  │  3.解方程  │  │  │ ❌ 错误1         │    │
│ │ 8错误  │  │  │  ❌1       │  │  │ 计算错误...      │    │
│ │        │  │  │  x+2y=8    │  │  │ 扣分: -2.0       │    │
│ │ 📄页面 │  │  │  ✓2        │  │  │                  │    │
│ │ ✅第1页│  │  │  x=2,y=3   │  │  │ 💡 正确做法:     │    │
│ │ ⚠️第2页│  │  └────────────┘  │  │ ...              │    │
│ │ ❌第3页│  │                  │  │                  │    │
│ │        │  │  [页面导航]      │  │ [上一个][下一个] │    │
│ │ 📝题目 │  │  ◀ 1 2 [3] 4 ▶  │  │                  │    │
│ │ ✅第1题│  │                  │  │                  │    │
│ │ ❌第3题│  │  [缩放: 100%]    │  │                  │    │
│ └────────┘  └──────────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**移动端三种视图**:
1. **图片模式**: 可缩放的原图 + 错误标记
2. **卡片模式**: 左右滑动查看每个批改点
3. **讲解模式**: 时间轴式逐步讲解

#### 4.2.5 历史记录模块

**功能描述**: 查看所有提交的批改记录

**界面原型**:
```
┌─────────────────────────────────────┐
│ 批改历史                            │
├─────────────────────────────────────┤
│ [筛选] [排序]                        │
│                                      │
│ ┌─────────────────────────────────┐ │
│ │ 数学作业1                        │ │
│ │ 2025-10-05 10:30                │ │
│ │ 得分: 85/100 | 8个错误          │ │
│ │ [查看详情] [重新批改]           │ │
│ └─────────────────────────────────┘ │
│                                      │
│ [加载更多...]                        │
└─────────────────────────────────────┘
```

#### 4.2.6 教师批注模块

**功能描述**: 教师可以手动批注和调整

**批注工具**:
- 🖊️ 画笔 - 自由绘制
- ⭕ 圆圈 - 圈出错误
- ✓ 勾 - 标记正确
- ✗ 叉 - 标记错误
- 💬 文字 - 添加批注文字

**界面原型**:
```
┌─────────────────────────────────────────────────┐
│ [批注工具栏]                                    │
│ 🖊️ 画笔 ⭕ 圆圈 ✓ 勾 ✗ 叉 💬 文字              │
│ 颜色: 🔴 🔵 🟢  |  [撤销] [重做] [清除]        │
│ [保存批注] [取消]                               │
├─────────────────────────────────────────────────┤
│ [全屏画布 - 作业图片 + 绘制层]                  │
└─────────────────────────────────────────────────┘
```

---

## 5. 技术架构设计

### 5.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                         前端层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Next.js 14   │  │ React Query  │  │ Socket.io    │     │
│  │ TypeScript   │  │ TanStack     │  │ Client       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                         API层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ FastAPI      │  │ WebSocket    │  │ Background   │     │
│  │ REST API     │  │ Manager      │  │ Tasks        │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                      业务逻辑层                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              GradingOrchestrator                      │  │
│  │              (LangGraph编排器)                        │  │
│  └──────────────────────────────────────────────────────┘  │
│         ↓                  ↓                  ↓             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Preprocess   │  │ Grading      │  │ Location     │     │
│  │ Agent        │  │ Agent        │  │ Agent        │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                       数据层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ PostgreSQL   │  │ Redis        │  │ S3/云存储    │     │
│  │ (主数据库)   │  │ (缓存)       │  │ (文件存储)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 技术栈

#### 5.2.1 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.13+ | 编程语言 |
| FastAPI | 0.104+ | Web框架 |
| SQLAlchemy | 2.0+ | ORM |
| Alembic | 1.12+ | 数据库迁移 |
| LangChain | 0.1+ | Agent框架 |
| LangGraph | 0.0.20+ | Agent编排 |
| Pydantic | 2.0+ | 数据验证 |
| PostgreSQL | 15+ | 主数据库 |
| Redis | 7+ | 缓存 |
| Tesseract.js | 4.0+ | OCR |

#### 5.2.2 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Next.js | 14+ | React框架 |
| TypeScript | 5.0+ | 类型安全 |
| React | 18+ | UI库 |
| TanStack Query | 5.0+ | 数据获取 |
| Socket.io | 4.0+ | WebSocket |
| Tailwind CSS | 3.0+ | 样式 |
| shadcn/ui | latest | UI组件 |
| Fabric.js | 5.0+ | 画布绘制 |

---

## 6. Agent系统设计

### 6.1 Agent架构

```
┌─────────────────────────────────────────────────────────────┐
│                  GradingOrchestrator                        │
│                  (LangGraph编排器)                          │
└─────────────────────────────────────────────────────────────┘
         │                  │                  │
         ↓                  ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Agent 1      │  │ Agent 2      │  │ Agent 3      │
│ Preprocess   │→ │ Grading      │→ │ Location     │
│ Agent        │  │ Agent        │  │ Agent        │
└──────────────┘  └──────────────┘  └──────────────┘
     │                  │                  │
     ↓                  ↓                  ↓
  题目分段           批改识别          位置标注
```

### 6.2 Agent 1: PreprocessAgent

**职责**: 题目分段识别

**输入**:
- 作业图片URL
- 图片尺寸

**输出**:
```typescript
interface QuestionSegment {
  questionNumber: string;    // "第1题"
  pageIndex: number;
  bbox: BoundingBox;         // 题目边界框
  croppedImage: string;      // 题目截图
  ocrText: string;           // OCR识别的文字
}
```

**实现方案**:
1. 使用Tesseract.js进行OCR识别
2. 识别题号 (1. 2. 3. 或 (1) (2) (3) 或 第1题)
3. 计算每个题目的边界框
4. 截取题目图片
5. 提取题目内的文字

**成本**: $0.001/页 (或免费使用Tesseract)

### 6.3 Agent 2: UnifiedGradingAgent

**职责**: 批改识别

**输入**:
- 题目截图
- 题目文字 (OCR结果)
- 标准答案

**输出**:
```typescript
interface GradingResult {
  score: number;
  maxScore: number;
  errors: Array<{
    type: string;
    description: string;
    deduction: number;
    suggestion: string;
    relatedText?: string;
  }>;
  correctParts: Array<{...}>;
  warnings: Array<{...}>;
  overallFeedback: string;
}
```

**成本**: $0.000043/题

### 6.4 Agent 3: LocationAnnotationAgent ⭐ 新增

**职责**: 精确位置标注

**输入**:
```typescript
interface LocationInput {
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  questionBbox: BoundingBox;
  error: {
    description: string;
    type: string;
    relatedText?: string;
  };
}
```

**输出**:
```typescript
interface LocationOutput {
  bbox: BoundingBox;         // 精确的像素坐标
  type: 'point' | 'line' | 'area';
  confidence: number;        // 0-1
  reasoning: string;         // 定位依据
}
```

**Prompt设计**:
```
你是一个专业的位置标注专家。你的任务是在学生作业图片中精确定位错误位置。

图片信息:
- 图片尺寸: {width}px × {height}px
- 题目区域: x={bbox.x}, y={bbox.y}, width={bbox.width}, height={bbox.height}

错误信息:
- 类型: {error.type}
- 描述: {error.description}
- 相关文字: {error.relatedText}

请返回JSON格式:
{
  "bbox": { "x": 150, "y": 200, "width": 200, "height": 50 },
  "type": "area",
  "confidence": 0.95,
  "reasoning": "错误位于第二行的计算结果部分"
}
```

**成本**: $0.000001/题 (几乎免费!)

---

## 7. 数据库设计

### 7.1 表结构

#### 7.1.1 submissions表 (更新)

```sql
CREATE TABLE submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  assignment_id UUID NOT NULL REFERENCES assignments(id),
  
  -- 文件信息
  files JSONB NOT NULL,
  note TEXT,
  
  -- 批改状态
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  
  -- Agent批改结果 (新增)
  agent_grading_status VARCHAR(20),
  agent_total_score FLOAT,
  agent_max_score FLOAT,
  agent_question_count INTEGER,
  agent_error_count INTEGER,
  agent_warning_count INTEGER,
  agent_processing_time_ms INTEGER,
  agent_graded_at TIMESTAMP,
  
  -- 时间戳
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

#### 7.1.2 question_gradings表 (新增)

```sql
CREATE TABLE question_gradings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
  
  -- 题目信息
  question_index INTEGER NOT NULL,
  question_number VARCHAR(50) NOT NULL,
  page_index INTEGER NOT NULL,
  
  -- 题目位置
  bbox_x INTEGER NOT NULL,
  bbox_y INTEGER NOT NULL,
  bbox_width INTEGER NOT NULL,
  bbox_height INTEGER NOT NULL,
  
  -- 批改结果
  score FLOAT NOT NULL,
  max_score FLOAT NOT NULL,
  status VARCHAR(20) NOT NULL,
  feedback TEXT,
  
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

#### 7.1.3 error_annotations表 (新增)

```sql
CREATE TABLE error_annotations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_grading_id UUID NOT NULL REFERENCES question_gradings(id) ON DELETE CASCADE,
  
  -- 错误信息
  error_type VARCHAR(100) NOT NULL,
  description TEXT NOT NULL,
  deduction FLOAT NOT NULL,
  suggestion TEXT,
  related_text TEXT,
  
  -- 位置信息 (Agent 3 输出)
  position_x INTEGER NOT NULL,
  position_y INTEGER NOT NULL,
  position_width INTEGER NOT NULL,
  position_height INTEGER NOT NULL,
  position_type VARCHAR(20) NOT NULL,
  position_confidence FLOAT NOT NULL,
  position_reasoning TEXT,
  
  -- 截图
  cropped_image_url TEXT,
  
  -- 教师调整
  teacher_adjusted BOOLEAN DEFAULT FALSE,
  teacher_position_x INTEGER,
  teacher_position_y INTEGER,
  
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

## 8. API设计

### 8.1 API端点列表

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v2/submissions` | 提交作业 |
| GET | `/api/v2/submissions/{id}` | 获取提交详情 |
| GET | `/api/v2/submissions/{id}/result` | 获取批改结果 |
| GET | `/api/v2/submissions/{id}/status` | 获取批改状态 |
| GET | `/api/v2/submissions` | 获取提交列表 |
| POST | `/api/v2/submissions/{id}/regrade` | 重新批改 |
| POST | `/api/v2/annotations` | 保存教师批注 |
| WS | `/ws/grading/{submissionId}` | WebSocket进度推送 |

### 8.2 API详细设计

#### 8.2.1 提交作业

```typescript
POST /api/v2/submissions
Content-Type: multipart/form-data
Authorization: Bearer {token}

Request:
{
  assignmentId: string;
  files: File[];        // 最多20个文件
  note?: string;        // 可选备注
}

Response: 201 Created
{
  submissionId: string;
  status: "processing";
  message: "作业已提交，正在批改中...";
  estimatedTime: 20;    // 预计时间(秒)
}

Error: 400 Bad Request
{
  error: "INVALID_FILE_FORMAT";
  message: "不支持的文件格式";
}
```

#### 8.2.2 获取批改结果

```typescript
GET /api/v2/submissions/{id}/result
Authorization: Bearer {token}

Response: 200 OK
{
  submissionId: string;
  status: "completed";
  totalScore: 85;
  maxScore: 100;

  // 页面汇总
  pages: [
    {
      pageIndex: 0;
      imageUrl: string;
      status: "perfect" | "warning" | "error";
      questionCount: 3;
      errorCount: 0;
    }
  ],

  // 题目详情
  questions: [
    {
      questionIndex: 0;
      questionNumber: "第1题";
      pageIndex: 0;
      bbox: { x: 0, y: 0, width: 800, height: 400 };
      score: 10;
      maxScore: 10;
      status: "correct";

      // 错误列表
      errors: [
        {
          id: string;
          type: "计算错误";
          description: "第二步计算错误...";
          deduction: 2.0;
          suggestion: "使用代入消元法...";
          position: { x: 150, y: 200, width: 200, height: 50 };
          positionType: "area";
          positionConfidence: 0.95;
          croppedImage: string;
        }
      ],

      // 正确部分
      correctParts: [
        {
          description: "第一步列方程正确";
          position: { x: 150, y: 150, width: 200, height: 40 };
          croppedImage: string;
        }
      ],

      feedback: "整体思路正确...";
    }
  ],

  // 所有错误的扁平列表
  allErrors: [...],

  // 总体反馈
  overallFeedback: "本次作业完成情况良好...",

  // 处理信息
  processingTimeMs: 15000;
  gradedAt: "2025-10-05T10:30:00Z";
}
```

#### 8.2.3 获取批改状态

```typescript
GET /api/v2/submissions/{id}/status
Authorization: Bearer {token}

Response: 200 OK
{
  submissionId: string;
  status: "processing";
  stage: "grading";      // preprocessing/grading/annotating/completed
  progress: 60;          // 0-100
  message: "正在批改第9题...";
  estimatedTimeRemaining: 8;  // 秒
}
```

#### 8.2.4 WebSocket进度推送

```typescript
WS /ws/grading/{submissionId}
Authorization: Bearer {token}

// 客户端连接
ws.connect('/ws/grading/uuid');

// 服务端推送 - 进度事件
{
  type: "grading_progress";
  submissionId: string;
  stage: "preprocessing" | "grading" | "annotating" | "completed";
  progress: 0-100;
  message: string;
  timestamp: string;
  details?: {
    currentQuestion: number;
    totalQuestions: number;
  };
}

// 完成事件
{
  type: "grading_completed";
  submissionId: string;
  totalScore: 85;
  maxScore: 100;
  errorCount: 8;
  timestamp: string;
}

// 错误事件
{
  type: "grading_failed";
  submissionId: string;
  error: string;
  message: string;
  timestamp: string;
}
```

#### 8.2.5 保存教师批注

```typescript
POST /api/v2/annotations
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  submissionId: string;
  annotationType: "drawing" | "text" | "shape";
  annotationData: object;  // Fabric.js JSON
  annotatedImageUrl?: string;
}

Response: 201 Created
{
  annotationId: string;
  message: "批注已保存";
}
```

---

## 9. 前端设计

### 9.1 页面结构

```
frontend/app/(dashboard)/
├── assignments/[id]/submit/page.tsx      # 作业提交
└── submissions/
    ├── page.tsx                          # 历史记录
    └── [id]/
        ├── page.tsx                      # 批改结果
        ├── grading/page.tsx              # 批改进度
        └── annotate/page.tsx             # 教师批注
```

### 9.2 桌面端布局 (三栏)

```
┌─────────────────────────────────────────────────────────────┐
│ 批改结果 | 得分: 85/100 | 错误: 8个 | [✏️ 批注模式]        │
├─────────────────────────────────────────────────────────────┤
│ ┌────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│ │ 📑 目录│  │ 📄 作业图片      │  │ 📝 批改详情      │    │
│ │ (15%)  │  │ (55%)            │  │ (30%)            │    │
│ └────────┘  └──────────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 9.3 移动端布局 (三种视图)

- **图片模式**: 可缩放的原图 + 错误标记
- **卡片模式**: 左右滑动查看每个批改点
- **讲解模式**: 时间轴式逐步讲解

### 9.4 核心组件代码示例

#### 9.4.1 API客户端

```typescript
// lib/api/grading.ts

export const gradingApi = {
  // 提交作业
  submitAssignment: async (data: SubmitData) => {
    const formData = new FormData();
    formData.append('assignmentId', data.assignmentId);
    data.files.forEach(file => formData.append('files', file));
    if (data.note) formData.append('note', data.note);

    const response = await fetch('/api/v2/submissions', {
      method: 'POST',
      body: formData,
    });
    return response.json();
  },

  // 获取批改结果
  getResult: async (submissionId: string) => {
    const response = await fetch(`/api/v2/submissions/${submissionId}/result`);
    return response.json();
  },

  // 获取批改状态
  getStatus: async (submissionId: string) => {
    const response = await fetch(`/api/v2/submissions/${submissionId}/status`);
    return response.json();
  },

  // 获取提交列表
  getSubmissions: async (params?: any) => {
    const query = new URLSearchParams(params);
    const response = await fetch(`/api/v2/submissions?${query}`);
    return response.json();
  },

  // 重新批改
  regrade: async (submissionId: string) => {
    const response = await fetch(`/api/v2/submissions/${submissionId}/regrade`, {
      method: 'POST',
    });
    return response.json();
  },
};
```

#### 9.4.2 React Query Hooks

```typescript
// hooks/useGrading.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { gradingApi } from '@/lib/api/grading';

// 提交作业
export function useSubmitAssignment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: gradingApi.submitAssignment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
    },
  });
}

// 获取批改结果
export function useGradingResult(submissionId: string) {
  return useQuery({
    queryKey: ['grading', submissionId],
    queryFn: () => gradingApi.getResult(submissionId),
    refetchInterval: (data) => {
      // 如果还在处理中，每5秒轮询一次
      return data?.status === 'processing' ? 5000 : false;
    },
  });
}

// 获取批改状态
export function useGradingStatus(submissionId: string) {
  return useQuery({
    queryKey: ['grading-status', submissionId],
    queryFn: () => gradingApi.getStatus(submissionId),
    refetchInterval: 2000, // 每2秒轮询
  });
}
```

#### 9.4.3 WebSocket Hook

```typescript
// hooks/useGradingProgress.ts

import { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';

export function useGradingProgress(submissionId: string) {
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState('');
  const [message, setMessage] = useState('');
  const [isCompleted, setIsCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const socket: Socket = io({
      path: '/ws',
      auth: { token: localStorage.getItem('token') },
    });

    socket.emit('join_grading', submissionId);

    socket.on('grading_progress', (data) => {
      if (data.submissionId === submissionId) {
        setProgress(data.progress || 0);
        setStage(data.stage || '');
        setMessage(data.message || '');
      }
    });

    socket.on('grading_completed', (data) => {
      if (data.submissionId === submissionId) {
        setProgress(100);
        setIsCompleted(true);
      }
    });

    socket.on('grading_failed', (data) => {
      if (data.submissionId === submissionId) {
        setError(data.error || '批改失败');
      }
    });

    return () => {
      socket.emit('leave_grading', submissionId);
      socket.disconnect();
    };
  }, [submissionId]);

  return { progress, stage, message, isCompleted, error };
}
```

#### 9.4.4 桌面端批改结果组件

```typescript
// components/grading/DesktopGradingView.tsx

interface DesktopGradingViewProps {
  submission: Submission;
  gradingResult: GradingResult;
  isTeacher: boolean;
}

export function DesktopGradingView({
  submission,
  gradingResult,
  isTeacher,
}: DesktopGradingViewProps) {
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number | null>(null);

  return (
    <div className="h-screen flex flex-col">
      {/* 顶部工具栏 */}
      <Toolbar
        totalScore={gradingResult.totalScore}
        maxScore={gradingResult.maxScore}
        errorCount={gradingResult.allErrors.length}
        isTeacher={isTeacher}
      />

      {/* 三栏布局 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧: 导航 (15%) */}
        <NavigationSidebar
          gradingResult={gradingResult}
          currentPageIndex={currentPageIndex}
          currentQuestionIndex={currentQuestionIndex}
          onPageChange={setCurrentPageIndex}
          onQuestionChange={setCurrentQuestionIndex}
        />

        {/* 中间: 图片 (55%) */}
        <ImageViewer
          page={gradingResult.pages[currentPageIndex]}
          currentQuestion={getCurrentQuestion()}
          onQuestionClick={setCurrentQuestionIndex}
        />

        {/* 右侧: 详情 (30%) */}
        <GradingDetail
          question={getCurrentQuestion()}
        />
      </div>
    </div>
  );
}
```

---

## 10. 实施计划

### 10.1 时间表

| 阶段 | 时间 | 任务 |
|------|------|------|
| **Week 1** | Day 1-5 | 后端完善 |
| **Week 2** | Day 6-10 | 前端开发 |

### 10.2 详细任务

#### Week 1: 后端完善

**Day 1-2**: Agent系统实现
- [ ] 创建PreprocessAgent
- [ ] 创建LocationAnnotationAgent
- [ ] 更新GradingOrchestrator

**Day 3**: 数据库集成
- [ ] 更新数据库模型
- [ ] 创建数据库迁移
- [ ] 创建数据服务

**Day 4**: WebSocket实时通知
- [ ] 实现WebSocket管理器
- [ ] 定义进度事件
- [ ] 集成到Orchestrator

**Day 5**: API完善与测试
- [ ] 完善API端点
- [ ] 添加错误处理
- [ ] 集成测试

#### Week 2: 前端开发

**Day 6-7**: 前端页面开发
- [ ] 桌面端页面
- [ ] 移动端页面
- [ ] 教师批注页面

**Day 8**: 前端API集成
- [ ] 创建API客户端
- [ ] React Query Hooks
- [ ] WebSocket Hook

**Day 9**: 端到端测试
- [ ] 手动测试
- [ ] 自动化测试
- [ ] 性能测试

**Day 10**: 优化与部署
- [ ] UI/UX优化
- [ ] 性能优化
- [ ] 文档完善

---

## 11. 验收标准

### 11.1 功能验收

| 功能 | 验收标准 | 状态 |
|------|----------|------|
| 作业提交 | 用户可以上传图片并触发批改 | [ ] |
| 题目分段 | 准确度 > 90% | [ ] |
| 批改识别 | 准确度 > 95% | [ ] |
| 位置标注 | 准确度 > 80% | [ ] |
| 实时进度 | WebSocket延迟 < 100ms | [ ] |
| 结果展示 | 多页多题导航流畅 | [ ] |

### 11.2 性能验收

| 指标 | 目标值 | 状态 |
|------|--------|------|
| 批改时间 (15题) | < 20秒 | [ ] |
| API响应时间 | < 500ms | [ ] |
| WebSocket延迟 | < 100ms | [ ] |
| 页面加载时间 | < 2秒 | [ ] |

---

## 12. 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| OCR识别不准确 | 中 | 多引擎投票；手动调整 |
| 位置标注不准确 | 中 | 降低阈值；教师调整 |
| WebSocket不稳定 | 低 | 断线重连；降级轮询 |

---

## 13. 成本分析

### 13.1 单次批改成本 (10页15题)

```
预处理 (OCR):        $0.010
批改 (15题):         $0.000645
位置标注 (15题):     $0.000015
─────────────────────────────
总计:                $0.010660
```

### 13.2 年度成本 (12000次批改)

```
批改成本:            $127.92
云存储:              $27.60
数据库:              $60.00
部署平台:            $60.00
─────────────────────────────
总计:                $275.52/年
```

---

## 14. 总结

### 14.1 Phase 2 核心价值

**让AI批改系统真正可用，提供完整的用户体验**

### 14.2 关键创新

1. **Multi-Agent协作** - 三个Agent分工协作
2. **精确位置标注** - LocationAgent像素级定位
3. **多页多题支持** - 完善的导航系统
4. **教师批注工具** - 手动批注和调整
5. **响应式设计** - 桌面端和移动端不同体验

### 14.3 预期成果

- ✅ 用户可以提交作业并查看批改
- ✅ 支持10页以上、15题以上的作业
- ✅ 位置标注准确度 > 80%
- ✅ 批改时间 < 20秒
- ✅ 年度成本 < $300

---

**需求文档完成时间**: 2025-10-05  
**文档版本**: v2.0  
**状态**: ✅ 完成  
**下一步**: 开始实施 🚀

