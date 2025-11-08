# 📅 Phase 2 实施计划

**项目**: AI作业批改系统 - Phase 2  
**工期**: 10个工作日 (2周)  
**开始日期**: 2025-10-05  
**预计完成**: 2025-10-18  

---

## 📊 进度总览

```
Week 1: 后端完善 ████████████████████░░░░░░░░░░ 50%
Week 2: 前端开发 ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0%
─────────────────────────────────────────────────
总进度:          ███████████████░░░░░░░░░░░░░░░ 25%
```

---

## 🗓️ Week 1: 后端完善 (Day 1-5)

### Day 1-2: Agent系统实现 ⭐ 核心任务

#### 任务清单

**Day 1: PreprocessAgent**
- [ ] 创建 `backend/app/agents/preprocess_agent.py`
  - [ ] 实现OCR题目分段 (Tesseract.js)
  - [ ] 实现题号识别 (正则表达式)
  - [ ] 实现题目边界框计算
  - [ ] 实现题目截图功能
- [ ] 创建 `backend/tests/test_preprocess_agent.py`
  - [ ] 测试题号识别准确度
  - [ ] 测试边界框计算
  - [ ] 测试多页多题场景
- [ ] 验收标准: 题目分段准确度 > 90%

**Day 2: LocationAnnotationAgent**
- [ ] 创建 `backend/app/agents/location_annotation_agent.py`
  - [ ] 实现Prompt设计
  - [ ] 实现位置标注逻辑
  - [ ] 实现置信度评估
  - [ ] 实现兜底方案 (低置信度时返回题目中心)
- [ ] 创建 `backend/tests/test_location_agent.py`
  - [ ] 测试位置标注准确度
  - [ ] 测试置信度评分
  - [ ] 测试兜底方案
- [ ] 更新 `backend/app/agents/grading_orchestrator.py`
  - [ ] 集成PreprocessAgent
  - [ ] 集成LocationAnnotationAgent
  - [ ] 实现LangGraph工作流
  - [ ] 添加进度回调
- [ ] 验收标准: 位置标注准确度 > 80%

#### 产出文件
```
backend/app/agents/
├── preprocess_agent.py          ⭐ 新增
├── location_annotation_agent.py ⭐ 新增
└── grading_orchestrator.py      📝 更新

backend/tests/
├── test_preprocess_agent.py     ⭐ 新增
└── test_location_agent.py       ⭐ 新增
```

#### 关键代码结构

**PreprocessAgent**:
```python
class PreprocessAgent:
    def __init__(self):
        self.ocr_engine = TesseractOCR()
    
    async def segment_questions(self, images: List[str]) -> List[QuestionSegment]:
        """题目分段识别"""
        segments = []
        for page_idx, image_url in enumerate(images):
            # 1. OCR识别
            ocr_result = await self.ocr_engine.recognize(image_url)
            
            # 2. 识别题号
            question_markers = self._detect_question_markers(ocr_result)
            
            # 3. 计算边界框
            for marker in question_markers:
                bbox = self._calculate_bbox(marker, ocr_result)
                cropped_image = self._crop_image(image_url, bbox)
                segments.append(QuestionSegment(
                    questionNumber=marker.text,
                    pageIndex=page_idx,
                    bbox=bbox,
                    croppedImage=cropped_image,
                    ocrText=self._extract_text_in_bbox(ocr_result, bbox)
                ))
        
        return segments
```

**LocationAnnotationAgent**:
```python
class LocationAnnotationAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="google/gemini-2.5-flash-lite",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.1
        )
    
    async def annotate(self, input: LocationInput) -> LocationOutput:
        """精确位置标注"""
        prompt = self._build_prompt(input)
        
        response = await self.llm.ainvoke([
            HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": input.imageUrl}}
            ])
        ])
        
        result = self._parse_response(response.content)
        
        # 验证和兜底
        if result.confidence < 0.5:
            result.bbox = self._get_fallback_location(input.questionBbox)
        
        return result
```

---

### Day 3: 数据库集成

#### 任务清单

- [ ] 更新数据库模型
  - [ ] 更新 `backend/app/models/submission.py`
    - [ ] 添加agent_grading_status字段
    - [ ] 添加agent_total_score字段
    - [ ] 添加agent_error_count字段
  - [ ] 创建 `backend/app/models/question_grading.py`
  - [ ] 创建 `backend/app/models/error_annotation.py`
  - [ ] 创建 `backend/app/models/correct_annotation.py`
  - [ ] 创建 `backend/app/models/teacher_annotation.py`

- [ ] 创建数据库迁移
  - [ ] 生成迁移文件: `alembic revision --autogenerate -m "Add agent grading tables"`
  - [ ] 测试迁移: `alembic upgrade head`
  - [ ] 验证表结构

- [ ] 创建数据服务
  - [ ] 创建 `backend/app/services/grading_result_service.py`
    - [ ] save_grading_result() - 保存批改结果
    - [ ] get_grading_result() - 获取批改结果
    - [ ] update_grading_result() - 更新批改结果
  - [ ] 创建 `backend/app/services/annotation_service.py`
    - [ ] save_annotation() - 保存标注
    - [ ] get_annotations() - 获取标注
    - [ ] update_annotation() - 更新标注

- [ ] 单元测试
  - [ ] 测试模型关系
  - [ ] 测试数据服务

#### 产出文件
```
backend/app/models/
├── submission.py              📝 更新
├── question_grading.py        ⭐ 新增
├── error_annotation.py        ⭐ 新增
├── correct_annotation.py      ⭐ 新增
└── teacher_annotation.py      ⭐ 新增

backend/app/services/
├── grading_result_service.py  ⭐ 新增
└── annotation_service.py      ⭐ 新增

backend/alembic/versions/
└── xxx_add_agent_grading_tables.py ⭐ 新增
```

#### 验收标准
- [ ] 数据库迁移成功执行
- [ ] 所有模型关系正确
- [ ] 数据服务能正确保存和查询
- [ ] 所有单元测试通过

---

### Day 4: WebSocket实时通知

#### 任务清单

- [ ] 实现WebSocket管理器
  - [ ] 创建 `backend/app/websocket/manager.py`
    - [ ] ConnectionManager类
    - [ ] connect() - 连接管理
    - [ ] disconnect() - 断开连接
    - [ ] join_room() - 加入房间
    - [ ] leave_room() - 离开房间
    - [ ] broadcast() - 广播消息

- [ ] 定义进度事件
  - [ ] 创建 `backend/app/websocket/events.py`
    - [ ] GradingProgressEvent
    - [ ] GradingCompletedEvent
    - [ ] GradingFailedEvent

- [ ] 集成到Orchestrator
  - [ ] 更新 `backend/app/agents/grading_orchestrator.py`
    - [ ] 添加progress_callback参数
    - [ ] 在每个阶段推送进度
    - [ ] 错误处理和推送

- [ ] 创建WebSocket端点
  - [ ] 更新 `backend/app/main.py`
    - [ ] 添加WebSocket路由
    - [ ] 集成ConnectionManager

- [ ] 测试WebSocket
  - [ ] 创建 `backend/tests/test_websocket.py`
    - [ ] 测试连接
    - [ ] 测试消息推送
    - [ ] 测试断线重连

#### 产出文件
```
backend/app/websocket/
├── manager.py                 ⭐ 新增
└── events.py                  ⭐ 新增

backend/app/
├── main.py                    📝 更新
└── agents/grading_orchestrator.py 📝 更新

backend/tests/
└── test_websocket.py          ⭐ 新增
```

#### 验收标准
- [ ] WebSocket连接稳定
- [ ] 进度推送实时 (延迟 < 100ms)
- [ ] 支持断线重连
- [ ] 所有测试通过

---

### Day 5: API完善与测试

#### 任务清单

- [ ] 完善API端点
  - [ ] 更新 `backend/app/api/v1/grading_v2.py`
    - [ ] POST /api/v2/submissions - 提交作业
    - [ ] GET /api/v2/submissions/{id}/result - 获取批改结果
    - [ ] GET /api/v2/submissions/{id}/status - 获取批改状态
    - [ ] GET /api/v2/submissions - 获取提交列表
    - [ ] POST /api/v2/submissions/{id}/regrade - 重新批改
  - [ ] 创建 `backend/app/api/v1/annotations.py`
    - [ ] POST /api/v2/annotations - 保存教师批注
    - [ ] GET /api/v2/annotations/{submissionId} - 获取教师批注

- [ ] 添加错误处理
  - [ ] 文件验证 (格式、大小)
  - [ ] 权限验证
  - [ ] 异常处理
  - [ ] 错误响应

- [ ] 生成API文档
  - [ ] 更新OpenAPI规范
  - [ ] 生成Swagger UI

- [ ] 集成测试
  - [ ] 创建 `backend/tests/test_api_integration.py`
    - [ ] 测试完整批改流程
    - [ ] 测试并发请求
    - [ ] 测试性能

#### 产出文件
```
backend/app/api/v1/
├── grading_v2.py              📝 更新
└── annotations.py             ⭐ 新增

backend/docs/
└── api.yaml                   📝 更新

backend/tests/
└── test_api_integration.py    ⭐ 新增
```

#### 验收标准
- [ ] 所有API端点正常工作
- [ ] API响应时间 < 500ms
- [ ] 错误处理完善
- [ ] API文档完整
- [ ] 所有集成测试通过

---

## 🗓️ Week 2: 前端开发 (Day 6-10)

### Day 6-7: 前端页面开发

#### Day 6: 桌面端页面

**任务清单**:
- [ ] 作业提交页面
  - [ ] 创建 `frontend/app/(dashboard)/assignments/[id]/submit/page.tsx`
  - [ ] 文件上传组件
  - [ ] 表单验证
  - [ ] 上传进度

- [ ] 批改进度页面
  - [ ] 创建 `frontend/app/(dashboard)/submissions/[id]/grading/page.tsx`
  - [ ] 进度条组件
  - [ ] 阶段显示
  - [ ] WebSocket集成

- [ ] 批改结果页面 (桌面端)
  - [ ] 创建 `frontend/app/(dashboard)/submissions/[id]/page.tsx`
  - [ ] 三栏布局
  - [ ] 导航侧边栏组件
  - [ ] 图片查看器组件
  - [ ] 批改详情面板组件

#### Day 7: 移动端和其他页面

**任务清单**:
- [ ] 批改结果页面 (移动端适配)
  - [ ] 三种视图模式
  - [ ] 图片模式组件
  - [ ] 卡片模式组件
  - [ ] 讲解模式组件

- [ ] 历史记录页面
  - [ ] 创建 `frontend/app/(dashboard)/submissions/page.tsx`
  - [ ] 列表展示
  - [ ] 筛选功能
  - [ ] 分页

- [ ] 教师批注页面
  - [ ] 创建 `frontend/app/(dashboard)/submissions/[id]/annotate/page.tsx`
  - [ ] 批注工具栏
  - [ ] Fabric.js画布
  - [ ] 保存功能

#### 验收标准
- [ ] 所有页面UI完整
- [ ] 桌面端和移动端适配良好
- [ ] 交互流畅，无卡顿
- [ ] 符合设计规范

---

### Day 8: 前端API集成

#### 任务清单

- [ ] 创建API客户端
  - [ ] 创建 `frontend/lib/api/grading.ts`
  - [ ] 实现所有API调用
  - [ ] 错误处理
  - [ ] 请求拦截器

- [ ] 创建React Query Hooks
  - [ ] 创建 `frontend/hooks/useGrading.ts`
  - [ ] useSubmitAssignment
  - [ ] useGradingResult
  - [ ] useGradingStatus
  - [ ] useSubmissions
  - [ ] useRegrade

- [ ] 创建WebSocket Hook
  - [ ] 创建 `frontend/hooks/useGradingProgress.ts`
  - [ ] 连接管理
  - [ ] 事件监听
  - [ ] 断线重连

- [ ] 集成到页面
  - [ ] 提交页面集成
  - [ ] 进度页面集成
  - [ ] 结果页面集成
  - [ ] 历史页面集成

#### 验收标准
- [ ] API调用正常
- [ ] 数据获取正确
- [ ] WebSocket连接稳定
- [ ] 错误处理完善
- [ ] 加载状态显示

---

### Day 9: 端到端测试

#### 任务清单

- [ ] 手动测试
  - [ ] 完整批改流程测试
  - [ ] 多页多题测试 (10页15题)
  - [ ] 位置标注测试
  - [ ] 教师批注测试
  - [ ] 移动端测试

- [ ] 自动化测试
  - [ ] 创建 `frontend/tests/e2e/grading.spec.ts`
  - [ ] E2E测试 (Playwright)
  - [ ] 组件测试
  - [ ] API测试

- [ ] 性能测试
  - [ ] 页面加载时间测试
  - [ ] API响应时间测试
  - [ ] WebSocket延迟测试
  - [ ] 并发测试 (10个请求)

- [ ] Bug修复
  - [ ] 记录Bug到 `docs/BUG_LIST.md`
  - [ ] 修复Bug
  - [ ] 回归测试

#### 验收标准
- [ ] 完整流程测试通过
- [ ] 所有E2E测试通过
- [ ] 性能指标达标
- [ ] 所有已知Bug已修复

---

### Day 10: 优化与部署准备

#### 任务清单

- [ ] UI/UX优化
  - [ ] 样式调整
  - [ ] 动画优化
  - [ ] 响应式优化
  - [ ] 无障碍优化

- [ ] 性能优化
  - [ ] 代码分割
  - [ ] 懒加载
  - [ ] 图片优化
  - [ ] 缓存优化

- [ ] 文档完善
  - [ ] 创建 `docs/USER_MANUAL.md` - 用户手册
  - [ ] 创建 `docs/DEVELOPER_GUIDE.md` - 开发文档
  - [ ] 更新 `docs/API_DOCUMENTATION.md` - API文档
  - [ ] 创建 `docs/DEPLOYMENT.md` - 部署文档

- [ ] 部署准备
  - [ ] 环境变量配置
  - [ ] 数据库迁移脚本
  - [ ] 创建 `scripts/deploy.sh`
  - [ ] 监控配置

#### 验收标准
- [ ] UI/UX优化完成
- [ ] 性能优化完成
- [ ] 文档完整
- [ ] 部署脚本可用

---

## 📈 里程碑

| 里程碑 | 日期 | 状态 |
|--------|------|------|
| M1: Agent系统完成 | Day 2 | ⏳ 进行中 |
| M2: 数据库集成完成 | Day 3 | ⏳ 待开始 |
| M3: 后端完成 | Day 5 | ⏳ 待开始 |
| M4: 前端页面完成 | Day 7 | ⏳ 待开始 |
| M5: 前端集成完成 | Day 8 | ⏳ 待开始 |
| M6: 测试完成 | Day 9 | ⏳ 待开始 |
| M7: Phase 2完成 | Day 10 | ⏳ 待开始 |

---

## 🎯 下一步行动

**立即开始**: Day 1 - PreprocessAgent实现

**命令**:
```bash
cd backend
touch app/agents/preprocess_agent.py
touch tests/test_preprocess_agent.py
```

---

**文档版本**: v1.0  
**最后更新**: 2025-10-05  
**状态**: ✅ 计划完成，准备实施

