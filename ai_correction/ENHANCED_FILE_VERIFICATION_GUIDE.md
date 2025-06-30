# 增强的文件验证系统指南

## 更新日期：2024-12-30

## 概述

基于最新的提示词工程最佳实践，我们开发了一个更智能、更灵活的文件验证系统。该系统能够：
- 自动收集文件的详细信息
- 基于上传区域进行智能分类
- 提供结构化的验证提示词
- 防止文件类型混淆和错误分类

## 核心特性

### 1. 详细的文件信息收集

系统会自动收集每个上传文件的以下信息：
```python
{
    'filename': 'xxx.pdf',           # 文件名
    'upload_area': '题目',           # 上传区域
    'file_type': 'pdf',              # 文件类型
    'has_handwriting': True,         # 是否包含手写
    'preview': '前100字符预览...'    # 内容预览（文本文件）
}
```

### 2. 智能的文件验证提示词

系统会生成结构化的验证提示词，包含：
- 文件清单（按上传区域分组）
- 验证检查表
- 特征识别指南
- 异常检测规则

### 3. 文件内容特征模板

为每种文件类型定义了详细的特征模板：

#### 题目文件特征
- **必须有**：题号标识、分值标注、题目描述
- **不应有**：解题步骤、答案、M/A标注
- **示例格式**：`Question 1 (5 marks)`

#### 学生答案特征
- **必须有**：解题步骤、计算过程
- **可能有**：手写内容、涂改痕迹、草稿
- **不应有**：M/A评分标注、标准答案格式

#### 批改方案特征
- **必须有**：标准答案、M/A评分标注
- **可能有**：另类做法（黑框）、评分说明
- **不应有**：手写痕迹、涂改

## 使用方法

### 1. 基础使用

```python
from functions.api_correcting.prompts_simplified import get_complete_grading_prompt

# 准备文件信息
file_info_list = [
    {
        'filename': 'question.pdf',
        'upload_area': '题目',
        'file_type': 'pdf',
        'has_handwriting': False
    },
    {
        'filename': 'answer.jpg',
        'upload_area': '学生答案',
        'file_type': 'image',
        'has_handwriting': True
    }
]

# 生成带验证的提示词
prompt = get_complete_grading_prompt(
    file_labels={'question.pdf': '题目文件', 'answer.jpg': '学生答案'},
    file_info_list=file_info_list
)
```

### 2. 高级功能

#### 增强的文件验证函数
```python
from functions.api_correcting.prompts_simplified import get_enhanced_file_verification

# 生成详细的文件验证提示词
verification_prompt = get_enhanced_file_verification(file_info_list)
```

#### 智能文件验证提示词
```python
from functions.api_correcting.prompts_simplified import create_smart_file_verification_prompt

# 创建智能验证提示词
files_data = {
    'question': [{'name': 'q1.pdf', 'type': 'pdf'}],
    'answer': [{'name': 'a1.jpg', 'type': 'image'}],
    'marking': []  # 空表示将自动生成评分标准
}

smart_prompt = create_smart_file_verification_prompt(files_data)
```

## 验证输出格式

系统会生成以下格式的验证结果：

```
🔍 文件验证与分类系统

【已上传文件详细信息】

📋 题目文件区域（预期：只有题目描述）
文件1：question.pdf
├─ 格式：pdf
├─ 页数：2页
├─ 手写：否
├─ 预览："Question 1 (5 marks)..."
└─ 验证要点：确认只有题目，无解答过程

✏️ 学生答案区域（预期：包含解题过程）
文件1：answer.jpg
├─ 格式：image
├─ 页数：1页
├─ 手写：是
└─ 验证要点：确认有学生的解题步骤

【验证结果】
✅ 文件验证通过：question.pdf - 题目文件
✅ 文件验证通过：answer.jpg - 学生答案
```

## 错误处理

### 常见错误及解决方案

1. **文件类型不匹配**
   ```
   ❌ 文件验证失败：answer.pdf - 发现M/A标注，疑似批改方案
   建议：请将此文件上传到批改方案区域
   ```

2. **缺少必要文件**
   ```
   ⚠️ 缺少题目文件
   无法进行批改，请先上传题目文件
   ```

3. **文件内容混淆**
   ```
   ⚠️ 需要注意：marking.pdf包含手写内容，请确认是否为批改方案
   ```

## 最佳实践

### 1. 文件上传前的准备
- 确保文件上传到正确的区域
- 题目文件应该是清晰的、无答案的
- 学生答案可以是手写或打字的
- 批改方案必须包含M/A标注

### 2. 文件命名建议
- 使用描述性的文件名：`题目1.pdf`、`学生张三答案.jpg`
- 避免使用特殊字符
- 保持文件名简洁明了

### 3. 批量处理
- 可以同时上传多个文件
- 系统会自动按类型分组
- 验证结果会分别显示

## 技术细节

### 提示词工程原则
1. **明确的角色定义**：告诉AI它是文件验证专家
2. **结构化信息**：使用树状结构展示文件信息
3. **具体的特征描述**：提供每种文件类型的特征
4. **清晰的输出格式**：定义验证结果的格式

### 灵活性设计
- 支持动态文件数量
- 可扩展的文件类型
- 自定义验证规则
- 多语言支持

## 未来改进方向

1. **OCR集成**：自动识别PDF和图片中的文字
2. **机器学习**：基于历史数据优化分类
3. **实时反馈**：上传时即时验证
4. **批量验证**：支持文件夹级别的验证

## 总结

这个增强的文件验证系统通过：
- 详细的文件信息收集
- 智能的提示词生成
- 结构化的验证流程
- 清晰的错误提示

确保了AI能够准确识别和分类每个上传的文件，大大提高了批改的准确性和效率。 