# 📖 Phase 2 快速参考

**快速查找Phase 2关键信息**

---

## 🎯 核心目标

**让AI批改系统真正可用，提供完整的用户体验**

- ✅ 用户可以提交作业并查看批改
- ✅ 支持10页以上、15题以上的作业
- ✅ 位置标注准确度 > 80%
- ✅ 批改时间 < 20秒
- ✅ 年度成本 < $300

---

## 🏗️ 架构概览

```
前端 (Next.js + React Query + WebSocket)
    ↕
API (FastAPI + WebSocket)
    ↕
Agent系统 (LangGraph)
    ├─ PreprocessAgent (题目分段)
    ├─ GradingAgent (批改识别)
    └─ LocationAgent (位置标注) ⭐ 新增
    ↕
数据库 (PostgreSQL + Redis)
```

---

## 🤖 三个Agent

### 1. PreprocessAgent - 题目分段

**输入**: 作业图片  
**输出**: 题目列表 + 边界框  
**技术**: Tesseract OCR  
**成本**: $0.001/页 (或免费)

### 2. GradingAgent - 批改识别

**输入**: 题目截图  
**输出**: 分数 + 错误 + 反馈  
**技术**: Gemini 2.5 Flash Lite  
**成本**: $0.000043/题

### 3. LocationAgent - 位置标注 ⭐ 新增

**输入**: 题目图片 + 错误描述  
**输出**: 精确像素坐标 + 置信度  
**技术**: Gemini 2.5 Flash Lite  
**成本**: $0.000001/题

---

## 📊 数据库表

### 核心表

1. **submissions** - 提交记录
2. **question_gradings** - 题目批改 ⭐ 新增
3. **error_annotations** - 错误标注 ⭐ 新增
4. **correct_annotations** - 正确标注 ⭐ 新增
5. **teacher_annotations** - 教师批注 ⭐ 新增

---

## 🔌 API端点

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v2/submissions` | 提交作业 |
| GET | `/api/v2/submissions/{id}/result` | 获取批改结果 |
| GET | `/api/v2/submissions/{id}/status` | 获取批改状态 |
| GET | `/api/v2/submissions` | 获取提交列表 |
| POST | `/api/v2/submissions/{id}/regrade` | 重新批改 |
| POST | `/api/v2/annotations` | 保存教师批注 |
| WS | `/ws/grading/{submissionId}` | WebSocket进度 |

---

## 🖥️ 前端页面

### 页面结构

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

### 桌面端布局

```
┌─────────────────────────────────────────┐
│ 📑 目录 │ 📄 作业图片 │ 📝 批改详情 │
│ (15%)   │ (55%)       │ (30%)       │
└─────────────────────────────────────────┘
```

### 移动端视图

1. **图片模式** - 可缩放原图 + 标记
2. **卡片模式** - 左右滑动查看
3. **讲解模式** - 时间轴讲解

---

## 📅 实施时间表

| 阶段 | 时间 | 任务 |
|------|------|------|
| Week 1 | Day 1-5 | 后端完善 |
| Week 2 | Day 6-10 | 前端开发 |

### Week 1 详细

- **Day 1-2**: Agent系统 (Preprocess + Location)
- **Day 3**: 数据库集成
- **Day 4**: WebSocket实时通知
- **Day 5**: API完善与测试

### Week 2 详细

- **Day 6-7**: 前端页面开发
- **Day 8**: 前端API集成
- **Day 9**: 端到端测试
- **Day 10**: 优化与部署

---

## ✅ 验收标准

### 功能验收

- [ ] 作业提交功能正常
- [ ] 题目分段准确度 > 90%
- [ ] 批改准确度 > 95%
- [ ] 位置标注准确度 > 80%
- [ ] 实时进度推送正常
- [ ] 多页多题导航流畅

### 性能验收

- [ ] 批改时间 < 20秒 (15题)
- [ ] API响应时间 < 500ms
- [ ] WebSocket延迟 < 100ms
- [ ] 页面加载时间 < 2秒

---

## 💰 成本分析

### 单次批改 (10页15题)

```
预处理:      $0.010
批改:        $0.000645
位置标注:    $0.000015
─────────────────────
总计:        $0.010660
```

### 年度成本 (12000次)

```
批改:        $127.92
云存储:      $27.60
数据库:      $60.00
部署:        $60.00
─────────────────────
总计:        $275.52/年
```

---

## 🔧 关键技术

### 后端

- **Python 3.13+**
- **FastAPI** - Web框架
- **LangChain + LangGraph** - Agent编排
- **SQLAlchemy** - ORM
- **PostgreSQL** - 数据库
- **Redis** - 缓存
- **Tesseract** - OCR

### 前端

- **Next.js 14** - React框架
- **TypeScript** - 类型安全
- **TanStack Query** - 数据获取
- **Socket.io** - WebSocket
- **Tailwind CSS** - 样式
- **shadcn/ui** - UI组件
- **Fabric.js** - 画布绘制

---

## 📝 关键文件

### 后端新增文件

```
backend/app/agents/
├── preprocess_agent.py          ⭐ 题目分段
├── location_annotation_agent.py ⭐ 位置标注
└── grading_orchestrator.py      📝 更新

backend/app/models/
├── question_grading.py          ⭐ 题目批改
├── error_annotation.py          ⭐ 错误标注
└── teacher_annotation.py        ⭐ 教师批注

backend/app/websocket/
├── manager.py                   ⭐ WebSocket管理
└── events.py                    ⭐ 事件定义

backend/app/services/
├── grading_result_service.py    ⭐ 批改结果服务
└── annotation_service.py        ⭐ 标注服务
```

### 前端新增文件

```
frontend/app/(dashboard)/
├── assignments/[id]/submit/page.tsx
└── submissions/
    ├── page.tsx
    └── [id]/
        ├── page.tsx
        ├── grading/page.tsx
        └── annotate/page.tsx

frontend/components/grading/
├── DesktopGradingView.tsx
├── MobileGradingView.tsx
├── NavigationSidebar.tsx
├── ImageViewer.tsx
└── GradingDetail.tsx

frontend/hooks/
├── useGrading.ts
└── useGradingProgress.ts

frontend/lib/api/
└── grading.ts
```

---

## 🚀 快速开始

### 1. 创建Agent文件

```bash
cd backend
touch app/agents/preprocess_agent.py
touch app/agents/location_annotation_agent.py
touch tests/test_preprocess_agent.py
touch tests/test_location_agent.py
```

### 2. 创建数据库模型

```bash
touch app/models/question_grading.py
touch app/models/error_annotation.py
touch app/models/correct_annotation.py
touch app/models/teacher_annotation.py
```

### 3. 运行数据库迁移

```bash
cd backend
alembic revision --autogenerate -m "Add agent grading tables"
alembic upgrade head
```

### 4. 创建前端页面

```bash
cd frontend
mkdir -p app/\(dashboard\)/assignments/[id]/submit
mkdir -p app/\(dashboard\)/submissions/[id]/grading
mkdir -p app/\(dashboard\)/submissions/[id]/annotate
mkdir -p components/grading
mkdir -p hooks
```

### 5. 运行测试

```bash
# 后端测试
cd backend
pytest tests/test_preprocess_agent.py
pytest tests/test_location_agent.py

# 前端测试
cd frontend
npm run test:e2e
```

---

## 📚 相关文档

- [完整需求文档](./PHASE2_REQUIREMENTS.md) - 详细需求说明
- [实施计划](./PHASE2_IMPLEMENTATION_PLAN.md) - 详细任务分解
- [API文档](./API_DOCUMENTATION.md) - API接口说明
- [Phase 1总结](./PHASE1_SUMMARY.md) - Phase 1回顾

---

## 🆘 常见问题

### Q1: OCR识别不准确怎么办？

**A**: 
1. 使用多个OCR引擎投票
2. 提供手动调整功能
3. 优化图片预处理

### Q2: 位置标注不准确怎么办？

**A**:
1. 降低置信度阈值
2. 使用兜底方案（题目中心）
3. 教师可手动调整

### Q3: WebSocket连接不稳定怎么办？

**A**:
1. 实现断线重连机制
2. 降级为HTTP轮询
3. 增加心跳检测

### Q4: 批改速度太慢怎么办？

**A**:
1. 使用后台任务队列
2. 并行处理多个题目
3. 优化Prompt减少token

---

## 📞 联系方式

- **项目负责人**: [Your Name]
- **技术支持**: [Support Email]
- **文档更新**: 2025-10-05

---

**快速参考版本**: v1.0  
**最后更新**: 2025-10-05  
**状态**: ✅ 完成

