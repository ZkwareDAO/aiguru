# LangGraph AI 批改系统集成指南

## 🎯 概述

本文档介绍如何在现有的 AI 批改系统中集成 LangGraph 智能批改功能。LangGraph 提供了多 Agent 协作的高级批改能力，包括坐标标注、知识点挖掘、错题分析等功能。

## 📋 功能特性

### 🧠 核心 Agent 架构

| Agent | 功能 | 输出 |
|-------|------|------|
| **UploadValidator** | 文件验证和预处理 | 验证结果、文件元数据 |
| **OCRVisionAgent** | OCR识别和图像分析 | 文本内容、图像区域 |
| **RubricInterpreter** | 评分标准解析 | 结构化评分规则 |
| **ScoringAgent** | AI智能评分 | 分数、等级、反馈 |
| **AnnotationBuilder** | 坐标标注生成 | 坐标标注、裁剪区域 |
| **KnowledgeMiner** | 知识点挖掘 | 知识点、学习建议 |
| **ResultAssembler** | 结果汇总 | 最终报告、导出数据 |

### 🎯 核心优势

- **🎯 坐标标注**: 在原图上精确标记错误位置
- **🖼️ 局部图卡片**: 裁剪错误区域，便于查看
- **🧠 知识点挖掘**: 自动识别涉及的知识点和掌握程度
- **📊 错题分析**: 深度分析错误原因和改进建议
- **📈 可视化报告**: 丰富的图表和数据展示
- **🔄 工作流编排**: 使用 LangGraph 管理复杂的多步骤流程

## 🚀 快速开始

### 1. 安装依赖

```bash
# 运行自动安装脚本
python install_langgraph.py

# 或手动安装
pip install langgraph>=0.0.40 langchain-core>=0.1.0 Pillow opencv-python
```

### 2. 测试安装

```bash
# 运行测试脚本
python test_langgraph.py
```

### 3. 启动应用

```bash
# 启动 Streamlit 应用
streamlit run streamlit_simple.py
```

### 4. 使用 LangGraph 批改

1. 在批改模式中选择 **"🧠 LangGraph智能批改"**
2. 上传题目、答案、评分标准文件
3. 点击 **"🚀 开始AI批改"**
4. 查看增强的批改结果

## 📁 文件结构

```
ai_correction/
├── functions/
│   ├── langgraph/                    # LangGraph 核心模块
│   │   ├── __init__.py
│   │   ├── state.py                  # 状态定义
│   │   ├── workflow.py               # 工作流编排
│   │   └── agents/                   # Agent 实现
│   │       ├── __init__.py
│   │       ├── upload_validator.py   # 文件验证
│   │       ├── ocr_vision_agent.py   # OCR和视觉分析
│   │       ├── rubric_interpreter.py # 评分标准解析
│   │       ├── scoring_agent.py      # AI评分
│   │       ├── annotation_builder.py # 坐标标注生成
│   │       ├── knowledge_miner.py    # 知识点挖掘
│   │       └── result_assembler.py   # 结果汇总
│   ├── langgraph_integration.py      # Streamlit 集成
│   └── api_correcting/               # 现有API模块
├── streamlit_simple.py               # 主应用（已集成LangGraph）
├── install_langgraph.py              # 依赖安装脚本
├── test_langgraph.py                 # 测试脚本
└── LANGGRAPH_INTEGRATION_GUIDE.md    # 本文档
```

## 🔧 配置说明

### 环境变量

```bash
# OpenAI API Key (用于AI评分)
export OPENAI_API_KEY="your_openai_api_key"

# OCR.space API Key (用于OCR识别)
export OCR_SPACE_API_KEY="your_ocr_space_api_key"
```

### 配置文件

在 `ai_correction/config/` 目录下创建配置文件：

```python
# config/langgraph_config.py
LANGGRAPH_CONFIG = {
    'ocr_api_key': 'K81037081488957',  # 默认OCR.space API Key
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'supported_formats': ['.jpg', '.jpeg', '.png', '.pdf', '.txt'],
    'default_language': 'zh',
    'default_strictness': '中等'
}
```

## 📊 使用示例

### 基本使用

```python
from functions.langgraph.workflow import run_ai_grading

# 运行LangGraph批改
result = await run_ai_grading(
    task_id="task_001",
    user_id="user_123",
    question_files=["question.jpg"],
    answer_files=["answer.jpg"],
    marking_files=["marking.txt"],
    mode="auto",
    strictness_level="中等",
    language="zh"
)

print(f"得分: {result['final_score']}")
print(f"等级: {result['grade_level']}")
```

### 兼容性使用

```python
from functions.langgraph_integration import intelligent_correction_with_files_langgraph

# 与现有接口兼容的使用方式
result_text = intelligent_correction_with_files_langgraph(
    question_files=["question.jpg"],
    answer_files=["answer.jpg"],
    marking_scheme_files=["marking.txt"]
)

print(result_text)
```

### 进度监控

```python
from functions.langgraph.workflow import get_grading_progress

# 获取批改进度
progress = await get_grading_progress("task_001")
print(f"当前步骤: {progress['current_step']}")
print(f"进度: {progress['progress_percentage']}%")
```

## 🎨 结果展示

### 坐标标注

LangGraph 会生成精确的坐标标注：

```json
{
  "coordinate_annotations": [
    {
      "region_id": "error_1",
      "coordinates": {"x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.4},
      "annotation_type": "error",
      "content": "计算错误",
      "confidence": 0.95
    }
  ]
}
```

### 知识点分析

```json
{
  "knowledge_points": [
    {
      "point_id": "math_algebra_equation",
      "subject": "数学",
      "topic": "方程",
      "mastery_status": "weak",
      "improvement_suggestions": ["加强基础运算练习"]
    }
  ]
}
```

### 学习建议

```json
{
  "learning_suggestions": [
    "需要加强基础计算能力",
    "建议复习一元一次方程的解法",
    "多做类似题型的练习"
  ]
}
```

## 🔍 故障排除

### 常见问题

1. **导入错误**
   ```
   ImportError: No module named 'langgraph'
   ```
   **解决**: 运行 `python install_langgraph.py` 安装依赖

2. **OCR识别失败**
   ```
   OCR API调用失败
   ```
   **解决**: 检查网络连接和API Key配置

3. **内存不足**
   ```
   MemoryError: Unable to allocate array
   ```
   **解决**: 减小图像尺寸或增加系统内存

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 性能优化

1. **图像预处理**: 压缩大图像以提高处理速度
2. **并发处理**: 使用异步处理多个文件
3. **缓存机制**: 缓存OCR结果避免重复处理

## 🚀 部署到 Railway

### 1. 准备部署文件

创建 `railway.toml`:

```toml
[build]
builder = "NIXPACKS"

[deploy]
healthcheckPath = "/"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"

[env]
PYTHONPATH = "/app"
```

### 2. 更新 requirements.txt

```txt
streamlit>=1.28.0
langgraph>=0.0.40
langchain-core>=0.1.0
Pillow>=9.0.0
opencv-python>=4.5.0
numpy>=1.21.0
requests>=2.25.0
```

### 3. 部署命令

```bash
# 安装 Railway CLI
npm install -g @railway/cli

# 登录 Railway
railway login

# 部署项目
railway up
```

## 📈 监控和分析

### 性能指标

- **处理时间**: 每个Agent的执行时间
- **成功率**: 批改成功的比例
- **错误率**: 各类错误的发生频率
- **用户满意度**: 基于反馈的评分

### 日志分析

LangGraph 提供详细的执行日志：

```python
# 查看工作流执行日志
workflow = get_workflow()
logs = workflow.get_execution_logs(task_id)
```

## 🔮 未来规划

### 即将推出的功能

- **🎯 更精确的坐标标注**: 基于深度学习的区域检测
- **🧠 更智能的知识点挖掘**: 集成知识图谱
- **📊 更丰富的可视化**: 交互式图表和报告
- **🔄 更灵活的工作流**: 支持自定义Agent组合
- **🌐 多语言支持**: 支持更多语言的批改

### 贡献指南

欢迎贡献代码和建议：

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 📞 支持和帮助

- **文档**: 查看 `functions/langgraph/` 目录下的详细文档
- **示例**: 运行 `test_langgraph.py` 查看使用示例
- **问题反馈**: 通过 GitHub Issues 报告问题

---

**🎉 恭喜！您已成功集成 LangGraph AI 批改系统！**

现在可以享受更智能、更精确的AI批改体验了。
