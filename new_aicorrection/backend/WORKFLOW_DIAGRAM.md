# LangGraph AI 批改系统工作流程图

## 完整工作流程

```mermaid
graph TD
    Start([开始: 用户上传文件]) --> UploadValidator[节点1: UploadValidator<br/>文件验证和任务初始化]
    
    UploadValidator --> CheckCamScannerKey{检查扫描全能王<br/>API Key}
    
    CheckCamScannerKey -->|有API Key| ImageEnhancer[节点2: ImageEnhancer<br/>图像增强 - 扫描全能王API]
    CheckCamScannerKey -->|无API Key| SkipEnhancer[跳过图像增强]
    
    ImageEnhancer --> RegionLocator[节点3: RegionLocator<br/>定位答题区域/题目位置]
    SkipEnhancer --> RegionLocator
    
    RegionLocator --> DocumentIngestor[节点4: DocumentIngestor<br/>文档结构分析<br/>无OCR]
    
    DocumentIngestor --> RubricInterpreter[节点5: RubricInterpreter<br/>评分标准解析]
    
    RubricInterpreter --> ScoringAgent[节点6: ScoringAgent<br/>AI智能评分<br/>Gemini/GPT/OpenRouter]
    
    ScoringAgent --> ResultAssembler[节点7: ResultAssembler<br/>结果汇总和保存]
    
    ResultAssembler --> End([结束: 返回批改结果])
    
    style Start fill:#e1f5e1
    style End fill:#ffe1e1
    style UploadValidator fill:#bbdefb
    style ImageEnhancer fill:#fff9c4
    style SkipEnhancer fill:#ffccbc
    style RegionLocator fill:#c5e1a5
    style DocumentIngestor fill:#b3e5fc
    style RubricInterpreter fill:#f8bbd0
    style ScoringAgent fill:#ce93d8
    style ResultAssembler fill:#a5d6a7
    style CheckCamScannerKey fill:#ffeb3b
```

## 节点详细说明

### 节点1: UploadValidator (文件验证器)
**职责**:
- 验证上传文件的格式（JPG, PNG, PDF等）
- 检查文件大小（最大50MB）
- 创建数据库记录
- 生成唯一任务ID
- 初始化GraphState

**输入**: 
- 原始文件路径
- 用户信息

**输出**:
- 验证结果
- 任务ID
- 初始化的GraphState

**条件**: 必须执行

---

### 节点2: ImageEnhancer (图像增强器) ⚠️ 可选
**职责**:
- 调用扫描全能王（CamScanner）API进行图像增强
- 文档扫描和边缘检测
- 图像去噪和清晰化
- 保存增强后的图像

**输入**:
- 原始图像文件

**输出**:
- 增强后的图像
- 增强元数据

**条件**: 
- ✅ **如果配置了 `CAMSCANNER_API_KEY`**: 执行图像增强
- ❌ **如果未配置API Key**: 跳过此节点，使用原始图像

**环境变量**:
```bash
CAMSCANNER_API_KEY=your_api_key_here
CAMSCANNER_API_ENDPOINT=https://api.camscanner.com/v1/enhance
```

---

### 节点3: RegionLocator (区域定位器)
**职责**:
- 使用AI视觉模型定位关键区域
- 识别答题区域
- 定位题目位置
- 标记评分区域
- 提取区域坐标（归一化到0-1）

**输入**:
- 增强后的图像（如果有）或原始图像

**输出**:
- 区域列表，每个区域包含：
  - `region_type`: 区域类型（question/answer/grading/other）
  - `coordinates`: 边界框 [x1, y1, x2, y2]
  - `confidence`: 置信度（0-1）
  - `description`: 区域描述

**使用的AI模型**:
- Gemini Vision (优先)
- OpenRouter Vision
- GPT-4 Vision

**示例输出**:
```json
{
  "regions": [
    {
      "region_type": "answer",
      "coordinates": [0.1, 0.2, 0.9, 0.8],
      "confidence": 0.95,
      "description": "学生答题区域"
    },
    {
      "region_type": "question",
      "coordinates": [0.1, 0.05, 0.9, 0.15],
      "confidence": 0.92,
      "description": "题目区域"
    }
  ]
}
```

---

### 节点4: DocumentIngestor (文档摄取器)
**职责**:
- 图像预处理（调整大小、格式转换）
- 文档结构分析
- 元数据提取
- 文件组织

**重要变更**: 
- ❌ **已移除OCR功能**
- ✅ 图像增强由 ImageEnhancer 节点处理
- ✅ 文本提取由 AI 视觉模型在 ScoringAgent 中完成

**输入**:
- 增强后的图像
- 区域定位信息

**输出**:
- 预处理后的图像元数据
- 文档结构信息
- 页面布局分析

---

### 节点5: RubricInterpreter (评分标准解释器)
**职责**:
- 解析评分标准文件
- 使用AI将文本评分标准转换为结构化数据
- 生成默认评分标准（如果未提供）
- 构建评分规则schema

**输入**:
- 评分标准文件（可选）
- 题目信息

**输出**:
```json
{
  "criteria": [
    {
      "criterion_id": "1",
      "description": "计算正确性",
      "max_points": 50,
      "grading_levels": [
        {"level": "完全正确", "points": 50},
        {"level": "部分正确", "points": 25},
        {"level": "错误", "points": 0}
      ]
    }
  ],
  "total_points": 100,
  "grading_guidelines": "..."
}
```

---

### 节点6: ScoringAgent (评分代理)
**职责**:
- 调用大语言模型进行智能评分
- 应用评分标准
- 生成详细反馈
- 计算分数和等级

**支持的AI模型**:
- Google Gemini (推荐)
- OpenRouter (多模型支持)
- OpenAI GPT-4

**输入**:
- 学生答案图像
- 题目图像
- 评分标准
- 区域定位信息

**输出**:
```json
{
  "total_score": 85,
  "max_score": 100,
  "percentage": 85.0,
  "grade_level": "B",
  "detailed_feedback": "...",
  "criterion_scores": [
    {
      "criterion_id": "1",
      "score": 45,
      "max_score": 50,
      "feedback": "计算过程正确，但最后一步有小错误"
    }
  ],
  "strengths": ["步骤清晰", "思路正确"],
  "suggestions": ["注意计算精度", "检查最终答案"]
}
```

**严格程度配置**:
- `宽松`: 更宽容的评分
- `中等`: 标准评分（默认）
- `严格`: 更严格的评分

---

### 节点7: ResultAssembler (结果汇总器)
**职责**:
- 汇总所有批改数据
- 保存结果到数据库
- 生成完整结果JSON
- 更新任务状态

**输入**:
- 评分结果
- 所有中间数据

**输出**:
- 完整的批改结果
- 数据库记录ID
- 结果URL

**数据库操作**:
- 更新 `GradingTask` 状态为 `COMPLETED`
- 保存完整结果到 `grading_results` 表

---

## 条件执行逻辑

### ImageEnhancer 节点的条件执行

```python
# 伪代码
if os.getenv("CAMSCANNER_API_KEY"):
    # 执行图像增强
    enhanced_images = await image_enhancer(state)
    state["enhanced_images"] = enhanced_images
else:
    # 跳过图像增强
    logger.info("Skipping image enhancement - API key not configured")
    state["enhanced_images"] = None
```

### 其他可选节点

未来可以添加更多条件节点：
- **OCR节点**: 如果配置了OCR API key
- **翻译节点**: 如果需要多语言支持
- **知识点提取**: 如果配置了知识图谱API

---

## API Key 配置总结

### 必需的API Key (至少一个)
- `OPENAI_API_KEY` - OpenAI GPT模型
- `GEMINI_API_KEY` - Google Gemini模型 (推荐)
- `OPENROUTER_API_KEY` - OpenRouter多模型支持

### 可选的API Key
- `CAMSCANNER_API_KEY` - 扫描全能王图像增强 (可选)
- `OCR_SPACE_API_KEY` - OCR.space文字识别 (已弃用)

### 配置示例

```bash
# .env 文件

# AI模型 (必需，至少一个)
GEMINI_API_KEY=your_gemini_key_here
OPENROUTER_API_KEY=your_openrouter_key_here

# 图像增强 (可选)
CAMSCANNER_API_KEY=your_camscanner_key_here
CAMSCANNER_API_ENDPOINT=https://api.camscanner.com/v1/enhance

# 数据库
DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# Firebase认证
FIREBASE_PROJECT_ID=your_project_id
```

---

## 数据流示例

### 完整流程数据流

```
1. 用户上传
   ├─ question.jpg
   ├─ answer.jpg
   └─ rubric.pdf

2. UploadValidator
   └─ task_id: "550e8400-e29b-41d4-a716-446655440000"

3. ImageEnhancer (如果有API key)
   ├─ enhanced_answer.jpg
   └─ enhancement_metadata

4. RegionLocator
   └─ detected_regions: [
        {region_type: "answer", coordinates: [0.1, 0.2, 0.9, 0.8]},
        {region_type: "question", coordinates: [0.1, 0.05, 0.9, 0.15]}
      ]

5. DocumentIngestor
   └─ document_structure: {
        total_pages: 2,
        document_type: "answer_sheet"
      }

6. RubricInterpreter
   └─ rubric: {
        criteria: [...],
        total_points: 100
      }

7. ScoringAgent
   └─ scores: {
        total_score: 85,
        detailed_feedback: "..."
      }

8. ResultAssembler
   └─ result: {
        task_id: "...",
        score: 85,
        feedback: "...",
        timestamp: "2025-11-08T10:30:00Z"
      }
```

---

## 错误处理

每个节点都有完善的错误处理机制：

1. **可恢复错误**: 节点失败但工作流继续
   - ImageEnhancer 失败 → 使用原始图像
   - RegionLocator 失败 → 使用整个图像

2. **不可恢复错误**: 节点失败导致工作流终止
   - UploadValidator 失败 → 立即返回错误
   - ScoringAgent 失败 → 返回错误（无法完成批改）

3. **错误状态记录**:
   - 所有错误都记录在 `state["events"]` 中
   - 错误信息保存到数据库
   - 用户可以查询错误详情

---

## 性能指标

### 预期处理时间

| 节点 | 平均时间 | 备注 |
|------|---------|------|
| UploadValidator | 0.5s | 文件验证 |
| ImageEnhancer | 2-5s | 取决于API响应 |
| RegionLocator | 3-8s | AI视觉分析 |
| DocumentIngestor | 1-2s | 图像处理 |
| RubricInterpreter | 2-5s | AI解析 |
| ScoringAgent | 5-15s | AI评分（最耗时） |
| ResultAssembler | 0.5-1s | 数据保存 |
| **总计** | **15-37s** | 完整流程 |

### 优化建议

1. **并行处理**: ImageEnhancer 和 RegionLocator 可以并行
2. **缓存**: 缓存评分标准解析结果
3. **批量处理**: 多个学生答案批量评分
4. **GPU加速**: 使用GPU加速AI推理

---

## 总结

这个工作流程设计具有以下特点：

✅ **模块化**: 每个节点职责清晰，易于维护  
✅ **灵活性**: 支持条件执行，可选节点  
✅ **可扩展**: 易于添加新节点  
✅ **容错性**: 完善的错误处理机制  
✅ **高性能**: 异步处理，支持并行  
✅ **可观测**: 完整的进度追踪和日志  

关键创新：
- 🔑 **条件执行**: 根据API key配置自动跳过可选节点
- 🚫 **移除OCR**: 简化流程，依赖AI视觉模型
- 📍 **区域定位**: 精确定位答题区域，提高评分准确性
- 🎨 **图像增强**: 可选的专业图像处理

