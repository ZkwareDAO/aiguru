# Backend AI 系统迁移与 LangGraph 增强需求文档

> 目标：将 `ai_correction` 中成熟的批改/作业处理链路迁移至 `new_aicorrection/backend` FastAPI 服务，并在此基础上引入 LangGraph 以强化多 Agent 协作、可观测性与并发弹性，从而支撑 Streamlit 全栈项目。

## 1. 背景
- **现有形态**
  - `ai_correction/streamlit_simple.py` 直接在 Streamlit 里编排批改逻辑，AI 能力散落在 `ai_correction/functions/api_correcting/*.py` 与本地数据库/文件系统。
  - `new_aicorrection/backend/app/services` 已有面向 API 的 `GradingService`, `AnalyticsService`, `AIAgentService`（LangChain 版）。
- **痛点**
  - 逻辑两套、难以维护；缺少统一任务编排与可观测性。
  - 现有 LangChain Agent 单体难以并行协作，缺乏节点级伸缩与隔离。
  - 多用户并发时，Streamlit 与后台耦合易阻塞或超时，缺乏队列/限流。

## 2. 迁移目标
1. **统一后端**：所有 AI 批改、作业、分析、对话能力收敛到 `new_aicorrection/backend`，暴露 REST/WebSocket API 给 Streamlit。
2. **LangGraph 编排**：以 LangGraph 管理长流程（上传→OCR→评分→可视化→总结→通知），可视化依赖 `coordinate-grading-view.tsx`、`cropped-region-grading-view.tsx` 所需数据。
3. **Agent 协作**：拆分领域 Agent，互相通过 LangGraph/事件存储共享上下文，支持任务级重试、节点热插拔。
4. **高并发韧性**：十数个班级/老师并发批改时保持 <5% 失败率，任务可排队、限速、横向扩容。

## 3. 参考基线
| 模块 | 现有文件 | 迁移策略 |
| --- | --- | --- |
| 任务/作业 API | `ai_correction/database.py`, `class_files/*` | 映射至 PostgreSQL 模型（`new_aicorrection/backend/app/models`），保留字段并补齐多租户、状态机。 |
| AI 批改核心 | `ai_correction/functions/api_correcting/*.py` | 拆成 LangGraph 节点：OCR、LLM评分、知识点提取、图像标注等，依赖 `app/services/grading_service.py`。 |
| AI 助手 | `new_aicorrection/backend/app/services/ai_agent_service.py` | 重构为 LangGraph 子图，供聊天/学习分析复用。 |
| 数据分析 | `ai_correction/demo_detailed_analysis.py`、`test_detailed_analysis.py` | 合入 `AnalyticsService` 并暴露 `/analytics/*` API。 |

## 4. 功能范围
1. **文件/作业管理**：题目、评分标准、学生答案上传校验；任务状态跟踪（`pending → ingesting → grading → summarizing → delivered`）。
2. **AI 批改流水线**：OCR、Rubric 解析、LLM 评分、坐标/局部标注生成、知识点/建议输出。
3. **学习分析 & AI 助手**：复用 `AIAgentService` 生成学习分析、个性化计划，与批改结果联动。
4. **通知/分发**：任务完成后向教师/学生推送（WebSocket + 邮件/消息）。
5. **多用户并发保护**：任务队列、限流、资源隔离、健康监控。

## 5. LangGraph Agent 协作设计
| Agent/节点 | 职责 | 依赖服务/工具 |
| --- | --- | --- |
| **Upload Intake Agent** | 校验三件套文件、写入任务队列、生成 metadata | `FileService`, MinIO/S3, Redis |
| **OCR & Vision Agent** | 图像预处理、OCR、区域检测 | OCR 模型（如 PaddleOCR）、`ai_recognition.py` 逻辑 |
| **Rubric Interpreter Agent** | 将标准答案/评分表解析为结构化评分规则 | `GradingService`, LangChain Parser |
| **Scoring Agent** | 基于 LangGraph ChildGraph 调用 Gemini 2.5 / GPT，逐题评分输出 JSON | `openrouter_service.py`, Prompt 模板 |
| **Visual Annotation Agent** | 生成坐标/裁剪信息，供前端 `coordinate-grading-view.tsx` / `cropped-region-grading-view.tsx` 使用 | CV 模块、Pillow |
| **Feedback & Knowledge Agent** | 汇总错题原因、知识点、建议 | `AnalyticsService`, AI Agent 子图 |
| **Report Assembler Agent** | 组装最终结果、写数据库、生成导出数据 | `grading_result_processor.py` |
| **Notification Agent** | 推送状态/结果到 WebSocket & 邮件 | `NotificationService`, `websocket_manager.py` |

### 协作要点
- **LangGraph 编排**：使用 `StateGraph`，`GraphState` 存储任务 ID、文件句柄、评分规则、部分结果。节点间通过 `add_edges` 串联，可根据任务类型（作文/理科）动态调整路径。
- **回调 & 可观测性**：启用 LangGraph `stream_events()`，将事件写入 Redis Pub/Sub，供 Streamlit 订阅实时进度；同时接入 OpenTelemetry + 结构化日志 (`app/core/logging.py`)。
- **重试策略**：针对 LLM/OCR/存储节点设置自定义 `retry`（如 3 次指数退避），失败则写 `task_failures` 表并触发告警。

## 6. 并发与稳定性方案
1. **任务排队**：使用 Redis Stream / BullMQ 或 Celery (Redis broker) 承载 LangGraph 触发器，FastAPI 接口仅写入队列立即返回 `task_id`。
2. **资源隔离**：不同 Agent 运行在独立 Worker（如 `scoring-worker`, `vision-worker`），可按 CPU/GPU 维度扩容；通过 Kubernetes/PM2 Supervisor 控制并发。
3. **限流/熔断**：
   - FastAPI 层使用 `slowapi` 或自定义中间件对用户/IP 限流。
   - 对上游模型（OpenRouter/Gemini）加令牌桶；超阈值时回退到次级模型或排队。
4. **状态持久化**：任务状态写 PostgreSQL（`grading_tasks`, `grading_results`），中间产物存对象存储/Redis；即使 Worker 崩溃也可恢复。
5. **并发读写**：所有 API/Worker 采用 `AsyncSession` + 连接池；使用 `asyncio` + `httpx` 对外调用，避免同步阻塞。
6. **健康监控**：`/health`、`/metrics` 暴露 Prometheus 指标（队列长度、节点耗时、错误率），结合告警策略保证高可用。

## 7. API 形态
| Endpoint | 描述 |
| --- | --- |
| `POST /api/v1/grading/tasks` | 创建任务（文件 ID / 描述 / 班级 / 模型参数），返回 `task_id` |
| `GET /api/v1/grading/tasks/{task_id}` | 查询任务状态及阶段进度 |
| `WS /api/v1/grading/tasks/{task_id}/stream` | LangGraph 事件流推送 |
| `GET /api/v1/grading/results/{task_id}` | 获取完整批改结果（坐标/局部卡片/知识点等） |
| `POST /api/v1/ai-agent/chat` | AI 助手对话 |
| `POST /api/v1/analytics/reports` | 生成学习报告 |

## 8. 实施步骤（建议 4 Sprint）
1. **Sprint 1 – 基础设施与数据模型**
   - 迁移 `ai_correction` 任务/作业数据结构到 PostgreSQL。
   - 完成文件存储/上传 API、任务表/状态机。
2. **Sprint 2 – LangGraph 核心链路**
   - 构建基础 Graph（Upload → OCR → Scoring → Report），接入 OpenRouter。
   - 打通 REST + WebSocket，前端可拿到实时进度。
3. **Sprint 3 – Agent 扩展与 AI 助手整合**
   - 引入视觉标注、知识点提取、学习分析节点。
   - 将 `AIAgentService` 重构为 LangGraph 子图，统一管理会话/记忆。
4. **Sprint 4 – 并发优化与运维**
   - 加入队列、限流、监控、告警；压测并调优。
   - 编写迁移/运维文档，完成回归测试。

## 9. 验收标准
- 迁移后 Streamlit 前端仅通过 FastAPI/LangGraph API 完成完整批改流程。
- LangGraph Agent 可单独扩容、故障不影响整个系统。
- 并发 50 个中型任务，成功率 ≥95%，P95 延迟 ≤2 分钟。
- 监控面板可实时看到任务状态和各节点耗时。

## 10. 待决事项
- OCR/图像存储使用何种第三方服务（需确认成本/合规）。
- 是否接入学校 SSO、家长通知渠道（钉钉/企业微信/短信）。
- LangGraph 执行环境（本地进程 vs. Kubernetes 作业）及成本预算。

---
此文档将作为后端 AI 系统迁移与 LangGraph 增强的需求基线，后续可根据实施细节补充接口契约、数据字典、测试计划。***
