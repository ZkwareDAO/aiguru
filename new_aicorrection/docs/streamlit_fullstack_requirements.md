# Streamlit 全栈 AI 批改平台需求文档

> 基于 `new_aicorrection` 前端视觉/交互（如 `HiddenNavigation` *new_aicorrection/frontend/components/hidden-navigation.tsx*, `AssignmentSystem` *new_aicorrection/frontend/components/assignment-system.tsx*, `AIGradingSystem` *new_aicorrection/frontend/components/ai-grading-system.tsx*, `DataManagement` *new_aicorrection/frontend/components/data-management.tsx* 等模块）与 `ai_correction` 的 Streamlit 经验沉淀（核心逻辑集中在 `ai_correction/streamlit_simple.py` 与 `ai_correction/functions/api_correcting/`），结合 `new_aicorrection` 后端 LangChain 能力并升级为 LangGraph 驱动的智能批改流水线。

## 1. 背景与目标
- **统一体验**：在单一 Streamlit 应用内复刻 Next.js 版本的动效、导航和多角色工作流，实现“所见即所得”的轻量部署。
- **LangGraph 驱动的后端**：在 `new_aicorrection/backend` FastAPI 服务上落地 LangGraph 长流程，对接 OpenRouter Gemini 2.5 Flash Lite + LangChain 现有能力，并暴露稳定 API 给 Streamlit。
- **复用存量资产**：沿用 `ai_correction` 里成熟的文件上传、批改配置、错题本与多页面结构，减少重写成本。
- **支撑多角色/多班级业务**：对齐 `new_aicorrection/frontend/app/page.tsx` 中 Teacher/Student/Parent 切换逻辑，保证教师的批改管理、学生的学习轨迹、家长的数据洞察一体化。

## 2. 用户与核心场景
| 角色 | 核心需求 | 现有参考 |
| --- | --- | --- |
| 教师 | 批量布置/批改作业、查看班级洞察、人工干预成绩 | `AssignmentSystem` *new_aicorrection/frontend/components/assignment-system.tsx*、`ClassDashboard` *new_aicorrection/frontend/components/class-dashboard.tsx*、`AIGradingSystem` *new_aicorrection/frontend/components/ai-grading-system.tsx* |
| 学生 | 上传作业、实时查看批改详情、管理错题 | `AIGradingSystem` 结果区、错题本 `error-book.tsx` *new_aicorrection/frontend/components/error-book.tsx* |
| 家长 | 浏览学习轨迹、接收推送、导出报告 | `DataManagement` *new_aicorrection/frontend/components/data-management.tsx*、`LearningReports` *new_aicorrection/frontend/components/learning-reports.tsx* |
| 管理员 | 维护配置、监控任务、管理 API Key | `UserManagement` *new_aicorrection/frontend/components/user-management.tsx*、`DataManagement` *new_aicorrection/frontend/components/data-management.tsx* |

## 3. 体验设计基准（Next.js → Streamlit 映射）
| Next.js 元素 | Streamlit 目标实现 |
| --- | --- |
| **HiddenNavigation** (`hidden-navigation.tsx`)：侧滑式多 Tab 导航 | 使用 `st.sidebar` + `st.navigation`（β）组合，保留图标/颜色体系；移动端用自定义 `st.markdown` + JS 触发器实现抽屉。 |
| **Brand/Launch 动画** (`brand-launch-animation.tsx`) | 启动页使用 `st.empty()` 循环 + `streamlit-extras` 动画，或前置 GIF/MP4，配合 `st.session_state["splash_done"]` 控制只显示一次。 |
| **AssignmentSystem** 多模态卡片/对话框 | 拆分为 `st.tabs` + `st.dataframe` + `st.modal`，复刻卡片信息密度；日期选择使用 `st.date_input`，文件/评分标准用 `st.file_uploader`。 |
| **AIGradingSystem** 三阶段进度条/上传体验 | 在 Streamlit 中以 `st.progress` + `st.status` + `st.file_uploader(accept_multiple_files=True)` 组合实现；Drag & Drop 布局通过 `streamlit-drag-and-drop` 或前端组件嵌入。 |
| **Coordinate/Cropped 视图** (`coordinate-grading-view.tsx`, `cropped-region-grading-view.tsx`) | 通过 `st.canvas`（Streamlit Elements/Captured JS）展示标注，并在右侧 `st.expander` 显示错误详情、知识点链接；提供“查看原图/局部卡片”切换按钮。 |
| **DataManagement** 图表工坊 | 借助 `plotly`, `pyrecharts` 或 `altair`，使用 `st.tabs` + `st.data_editor` 支持自定义 chart config，保留导入导出流程。 |
| **UserManagement** 角色切换 | `st.selectbox` + `st.radio` 控制 `session_state["role"]`，UI 通过 `st.columns` + CSS 自定义实现徽章与头像。 |

## 4. 功能需求

### 4.1 认证与会话
- 支持邮箱/手机号 + OTP、第三方（学校 SSO）登录。
- JWT/Session 双轨：Streamlit 通过 FastAPI `/auth/*` 接口获取 token 并存储在 `st.session_state`.
- 角色切换需实时刷新权限、菜单与默认数据源。

### 4.2 班级与用户管理
- 班级 CRUD、邀请码加入、角色分配，参考 `ClassDashboard` 与 `ClassManagement`.
- 班级看板展示人数、提交率、均分、Top 学生卡片（进度条 +趋势）。
- 家长/学生绑定关系维护，支持多孩子视角。

### 4.3 作业生命周期
- 作业创建：题目信息、学科、Rubric、AI 指令、多附件上传（题目/标准/样板）。
- 发布/关闭/复制/导出作业，支持班级过滤、搜索与状态筛选。
- 提交管理：学生提交时间线、附件预览、AI 分析摘要（优劣势/知识点）。

### 4.4 AI 批改流程（LangGraph）
- 支持批量任务、异步排队、断点续批。
- 任务状态：`pending → ingesting → grading → annotating → summarizing → distributing`.
- 校验题目-标准-答案 三件套完整性；允许教师自定义扣分项/权重。
- 教师人工干预：调整得分、添加评语、重新触发某题批改。

### 4.5 可视化批改
- 坐标标注模式：原图缩放、拖拽、点击弹出错误详情 + 知识点链接（Canvas + Popover）。
- 局部卡片模式：裁剪图 + 错误类别 + 一键定位原图 + 相关练习。
- 错题本：分类（知识点/错误类型/严重度），支持导出和推送练习。

### 4.6 数据管理与分析
- 数据导入（Excel/CSV/School MIS API）并映射至班级/学生。
- 自定义图表：折线/柱状/饼/雷达/散点，支持保存模板与权限控制。
- 学习报告：个人轨迹、班级对比、知识点热力、提升建议。
- 支撑导出 PDF/Excel、分享到家长/学生。

### 4.7 AI 助手 & 对话
- 复用 `AIAgentService` 能力：学习分析、个性化计划、资源推荐。
- Streamlit 内嵌聊天框：支持上下文、历史回放、引用数据（以 citations 呈现）。
- LangGraph 中独立节点处理 AI 助手请求，复用同一 LLM/缓存。

### 4.8 通知与结果分发
- 任务完成推送（站内、邮件、可扩展到微信企业号）。
- 学生/家长接收批改结果链接，权限校验 + 临时 token。
- 批改结果归档（版本化），可回滚/对比。

### 4.9 系统配置与权限
- API Key、模型参数、并发度、LangGraph 节点开关。
- 数据保留策略、日志级别、审计追踪。
- 多租户/学校隔离预留（通过 org_id）。

## 5. LangGraph 后端设计要点
1. **编排图谱**  
   - 节点：`UploadValidator` → `DocumentSegmenter` → `RubricInterpreter` → `LLMScoring` → `VisualAnnotator` → `KnowledgeExtractor` → `ResultAssembler` → `Notifier`.  
   - 每个节点沿用原 `services` 中逻辑：如 `FileService`, `GradingService`, `AnalyticsService`, `NotificationService`.
2. **状态管理**  
   - `GraphState` 存储任务元信息、文件句柄、评分上下文、LangChain 记忆引用。  
   - Redis 作为 `checkpoints`/`streams`，PostgreSQL 落地最终结果。
3. **回调与可观测性**  
   - LangGraph `graph.stream_events()` 输出写入 Redis Pub/Sub，供 Streamlit `st.experimental_connection`/WebSocket 订阅更新进度条。  
   - 统一 tracing（OpenTelemetry）和结构化日志。
4. **API 层**  
   - FastAPI 提供 REST + WebSocket：`POST /grading/tasks`, `GET /grading/tasks/{id}`, `WS /grading/stream/{task_id}`。  
   - AI 助手、数据分析沿用 `/ai-agent/*`、`/analytics/*` 路由。

## 6. Streamlit 前后端一体化架构
- **多页结构**：利用 `st.navigation`（或 `multipage app`）实现 `首页/作业/班级/批改/分析/设置`，对应 Next.js `page.tsx` 中的 `currentPage` 切换。
- **状态管理**：所有关键数据写入 `st.session_state`（role、selected_class、upload_buffer、task_id_list）；结合 `st.cache_data`/`st.cache_resource` 缓存班级/作业列表。
- **组件封装**：将高复用区块（统计卡片、任务进度、错题表）封装成 Python 类/函数，命名与 Next 组件一致，方便样式映射。
- **异步体验**：使用 `asyncio` + `httpx`/`aiohttp` 调用 FastAPI；进度监听通过 `st.websocket_connection` 或轮询 `st.empty()`。
- **富交互嵌入**：对 Canvas、动画、拖拽上传等使用 `streamlit-components`（如 `streamlit-dragndrop`, `streamlit-echarts`）或自定义 React 组件。

## 7. 数据流与 API 对接
1. **上传 → 批改**  
   Streamlit 上传文件 → `POST /files`（返回 file_id） → `POST /grading/tasks`（question/standard/answers + metadata） → LangGraph 执行 → WebSocket 推进度 → `GET /grading/results/{task_id}` 供 UI 渲染。
2. **作业与班级**  
   `GET /classes`, `GET /assignments?class_id=`, `POST /assignments`, `POST /submissions` 等接口对齐 `AssignmentSystem` 行为。
3. **数据分析**  
   `GET /analytics/dashboards`, `POST /analytics/charts`（保存配置），`POST /data/import`, `GET /data/export`.
4. **AI 助手**  
   `POST /ai-agent/chat`, `GET /ai-agent/resources/{topic}`, `POST /ai-agent/analyze/learning`。

## 8. 非功能与运维要求
- **性能**：单任务 < 3s 创建、30 份批改在 2min 内完成；LangGraph 节点可水平扩展。
- **可用性**：任务失败可重试，节点级熔断；Streamlit 显示友好降级信息。
- **安全**：细粒度角色权限、签名下载链接、审计日志。
- **DevOps**：使用 `docker compose` 启动（redis + postgres + FastAPI + Streamlit），CI 覆盖测试 + lint；监控（Prometheus + Grafana 或 Railway 自带）。

## 9. 实施路线（建议）
1. **M1 - 运行底座**（~1 周）  
   - 容器化 Redis/Postgres/FastAPI。  
   - 整理 `.env`、密钥、对象存储。  
   - 完成 LangGraph POC（单题批改链路）。
2. **M2 - LangGraph 核心能力**（~2 周）  
   - 将现有 `GradingService`, `AnalyticsService`, `AIAgentService` 装配成 Graph 节点。  
   - 打通任务创建/查询/流式事件，编写 API 文档与测试。
3. **M3 - Streamlit UI 复刻**（~2 周）  
   - 完成首页/作业/班级/批改/分析/设置页面。  
   - 集成上传、进度条、Canvas/卡片、AI 助手对话。  
   - 与 backend API 对接并打通主流程。
4. **M4 - 硬化与交付**（~1 周）  
   - 压测、观察性、告警。  
   - 灰度发布 + 文档（部署/运维/使用指南）。  
   - 回收遗留 Next.js 代码或保留为设计稿。

## 10. 风险与待确认
- LangGraph 与现有 LangChain 代码共存策略（是重写节点还是包裹现有 service）。
- Streamlit 中的复杂动画/拖拽体验实现成本（可能需自研组件）。
- 文件与图像存储（对象存储、签名 URL）尚未确定。
- 模型/接口配额与费用（OpenRouter + 其他模型）需要预算。
- 多租户 & 家长端权限是否立即支持。

---

此文档作为后续需求细化、架构评审与迭代排期的基线，可在实施过程中补充接口定义、数据字典与测试用例。***
