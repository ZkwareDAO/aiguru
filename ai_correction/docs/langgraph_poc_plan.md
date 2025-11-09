# LangGraph POC 实施方案

## 1. 目标与范围
- **目的**：验证在 `new_aicorrection/backend` FastAPI 服务上，以 LangGraph 编排 AI 批改链路的可行性，确保前端（Streamlit/Next）可通过统一 API 获取实时进度与结果。
- **范围**：聚焦单次批改任务（题目/标准/学生答案三件套），覆盖上传验证、OCR、评分、可视化数据生成、报告汇总、通知推送等关键节点；同时验证多 Agent 并发与可观测性。
- **不在 POC 范围**：完整班级管理、家长端通知、多租户收费逻辑等暂不纳入，但需要为后续扩展预留接口。

## 2. LangGraph 节点拆分
| 节点 | 职责 | 依赖模块/文件 | 产出 |
| --- | --- | --- | --- |
| `UploadValidator` | 校验文件三件套、生成 `task_id`、落库初始状态 | `app/services/file_service.py`, `app/models/grading_task.py`（需新增） | `GraphState` 基础信息、存储句柄 |
| `DocumentIngestor` | 图像预处理、OCR、区域检测 | `ai_correction/functions/ai_recognition.py`、PaddleOCR | 结构化文本、坐标候选 |
| `RubricInterpreter` | 解析评分标准、构建 rubric schema | `app/services/grading_service.py`, `app/core/grading_prompts.py` | 评分规则 JSON |
| `ScoringAgent` | 逐题调用 Gemini/GPT 评分，输出得分+解释 | `app/services/openrouter_service.py`, LangChain `AIAgentService` | per-question score, feedback |
| `AnnotationBuilder` | 生成坐标/局部卡片数据 | Pillow/NumPy 工具、`coordinate-grading-view.tsx` 需求 | 坐标数组、裁剪图 URL |
| `KnowledgeMiner` | 知识点提取、错题建议 | `app/services/analytics_service.py`, LangChain | 知识点列表、建议 |
| `ResultAssembler` | 写入 `grading_results` 表/对象存储，供 API 获取 | `app/services/grading_result_processor.py` | 完整结果 JSON |
| `Notifier` | 推送状态更新（WebSocket/邮件） | `app/services/websocket_manager.py`, `notification_service.py` | 事件消息 |

- 节点通过 `LangGraph StateGraph` 串联，`GraphState` 包含 `task_id`, `files`, `rubric`, `ocr_output`, `scores`, `annotations`, `knowledge`, `result_uri` 等键。
- 针对作文/客观题等不同类型，可在入口处根据 `task_type` 决定是否跳过 `AnnotationBuilder` 等节点。

## 3. 数据流与集成
1. `POST /api/v1/grading/tasks` → `UploadValidator` 入队，并返回 `task_id`。
2. Worker 监听 Redis Stream（或 Celery 队列）触发 LangGraph 执行。
3. 每个节点完成后发送 `graph.stream_events()` 到 Redis Pub/Sub；WebSocket 层订阅并推送前端。
4. `ResultAssembler` 将最终 JSON/图像写对象存储（MinIO/S3）并更新 PostgreSQL。
5. 前端通过 `GET /grading/results/{task_id}` 获取结果；`Notifier` 确保任务完成事件送达。

## 4. 部署拓扑
```
┌─────────────────────┐      enqueue       ┌─────────────────────┐
│ FastAPI (uvicorn)   │ ───────────────▶   │ Redis Stream / MQ   │
│  /api/v1/grading    │                   │ (tasks + events)     │
└─────────────────────┘                     └─────────────────────┘
           ▲                                         ▲
           │ REST/WS                                 │ stream_events
           │                                         │
┌─────────────────────┐   consume & run   ┌─────────────────────┐
│ LangGraph Worker(s) │ ◀──────────────── │ Redis / Postgres /  │
│ (Upload/OCR/etc.)   │ ── checkpoints ─▶ │ MinIO (state store) │
└─────────────────────┘                   └─────────────────────┘
```
- **进程划分**：至少三个独立 worker 进程（`vision-worker`, `llm-worker`, `result-worker`），通过队列分发任务，必要时部署在不同机器/容器。
- **存储**：PostgreSQL 保存任务/结果；Redis Stream 用作任务触发与事件广播；MinIO/S3 存储原始文件与裁剪图。
- **监控**：在每个 worker 上启用 OpenTelemetry 导出 + Prometheus 指标（节点耗时、错误率、队列长度）。

## 5. 压测计划
| 目标 | 详情 |
| --- | --- |
| **吞吐** | 并发 20/50/100 个批改任务，观测任务完成率、P95 处理时间；必要时模拟不同文件大小、题目数量。 |
| **资源占用** | 记录 CPU/GPU/内存使用，验证 OCR/LLM 节点不会互相阻塞；通过 `docker stats`/Prometheus 收集。 |
| **可靠性** | 注入上游失败（OpenRouter 429、OCR 超时等），确认节点重试与任务回滚逻辑生效。 |
| **事件流** | 使用 WebSocket 客户端订阅 100 个任务，确保 event 延迟 < 2s，丢包率 0。 |
| **持久化** | 强制终止 worker 进程，验证 `GraphState` checkpoint + 任务重跑机制确保数据一致性。 |

### 压测工具与脚本
- `locust` 或 `k6`：模拟 REST 调用创建任务、订阅结果。
- 自建 `stress_runner.py`：批量上传真实作业文件到 `/grading/tasks`。
- `pytest` + `pytest-asyncio`: 针对 LangGraph 节点编写单元+集成测试。

## 6. 里程碑（POC）
1. **Week 1**：完成 `UploadValidator`、`DocumentIngestor`、`ScoringAgent` 节点 POC，跑通单任务。
2. **Week 2**：补齐 `AnnotationBuilder`、`KnowledgeMiner`、`ResultAssembler`，实现事件流与 WebSocket 推送。
3. **Week 3**：部署多 worker 拓扑，完成压测脚本与主要场景压测，输出性能报告。
4. **Week 4**：梳理问题列表、改进建议，形成正式技术评审材料，为全面迁移做准备。

## 7. 验收标准
- POC 可在开发环境一次性完成 ≥20 个任务并输出完整坐标/错题结果。
- 监控面板可展示节点耗时、错误率、队列长度。
- 出具压测数据：P95 总耗时、失败率、资源使用，并明确扩容策略。
- 形成复用的 LangGraph 模板/代码骨架，可直接接入生产化改造。
