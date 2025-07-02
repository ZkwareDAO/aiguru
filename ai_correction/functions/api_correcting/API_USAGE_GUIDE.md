# AI批改系统 API 使用指南

## 概述

本系统提供了简化的两种批改模式：
1. **有批改标准模式**：用户提供批改标准，系统根据标准进行批改
2. **无批改标准模式**：系统自动生成批改标准，然后进行批改

## 核心函数

### 1. batch_correction_with_standard
**有批改标准的批量批改**

```python
from functions.api_correcting import batch_correction_with_standard

# 批改多个学生的答案
result = batch_correction_with_standard(
    marking_scheme_files=['标准答案1.pdf', '标准答案2.jpg'],
    student_answer_files=['学生1答案.pdf', '学生2答案.jpg'],
    strictness_level="中等"  # 可选：严格/中等/宽松
)
print(result)
```

### 2. batch_correction_without_standard
**无批改标准的批量批改（自动生成标准）**

```python
from functions.api_correcting import batch_correction_without_standard

# 系统会先根据题目生成批改标准，然后批改
result = batch_correction_without_standard(
    question_files=['数学题目.pdf'],  # 题目文件
    student_answer_files=['学生1答案.pdf', '学生2答案.jpg'],
    strictness_level="中等"
)
print(result)
```

### 3. intelligent_correction_with_files
**智能批改（自动选择模式）**

```python
from functions.api_correcting import intelligent_correction_with_files

# 系统会根据提供的文件类型自动选择批改模式
result = intelligent_correction_with_files(
    question_files=['题目.pdf'],  # 可选
    answer_files=['学生答案.pdf'],  # 必需
    marking_scheme_files=['标准答案.pdf'],  # 可选
    strictness_level="中等"
)
print(result)
```

## 批改严格程度说明

### 严格
- 适用于正式考试、期末测评
- 完全按照标准答案评分
- 步骤缺失或方法不同会扣分
- 计算错误立即扣除相应答案分

### 中等（默认）
- 适用于单元测试、阶段性评估
- 允许步骤简化
- 只要思路和结果正确即可得分
- 小计算错误但不影响主要概念理解可获部分分

### 宽松
- 适用于平时作业、练习
- 重点关注核心概念理解
- 允许有小错误
- 创新解法得到鼓励，可获额外加分

## 输出格式示例

### 有批改标准模式输出
```
=== 学生1批改结果 ===

### 题目1
**满分**：10分
**得分**：8分
**批改详情**：
- 步骤1：正确建立方程 ✓ 2M 
- 步骤2：代数变形有小错误 ✓- 1M
- 步骤3：最终答案正确 ✓ 2A
**失分点**：代数变形时符号错误

**总评**：
- 总分：8/10
- 优势：解题思路清晰，最终答案正确
- 建议：注意运算过程中的符号处理

=== 班级整体分析 ===
1. 平均分：7.5分
2. 易错题分析：第1题的代数变形步骤普遍存在问题
3. 教学建议：加强代数运算规则的练习
```

### 无批改标准模式输出
```
【自动生成的评分标准】
## 题目1：解方程 2x² - 5x + 3 = 0
**总分值**：10分

### 评分点：
1. 选择正确的求解方法 (2M)
   - 正确标准：选择公式法或因式分解法
   - 部分得分情况：方法选择合理但执行有误可得1分

2. 计算过程 (5M)
   - 正确标准：步骤完整，计算准确
   - 部分得分情况：过程正确但计算有误可得3分

3. 最终答案 (3A)
   - 正确标准：x₁ = 1.5, x₂ = 1
   - 部分得分情况：只求出一个根可得1.5分

=== 学生1批改结果 ===
[批改内容同上]
```

## Web API 接口

### 1. 有批改标准的批改
```python
from functions.api_correcting import web_correction_with_scheme

result = web_correction_with_scheme(
    marking_scheme_files=['标准.pdf'],
    student_answer_files=['答案.pdf'],
    strictness_level="中等"
)
# 返回 GradingResult 对象
```

### 2. 无批改标准的批改
```python
from functions.api_correcting import web_correction_without_scheme

result = web_correction_without_scheme(
    student_answer_files=['包含题目和答案的文件.pdf'],
    strictness_level="中等"
)
# 返回 GradingResult 对象
```

## 支持的文件格式

- 图片：JPG, JPEG, PNG, GIF, BMP, TIFF, WEBP
- PDF文档
- Word文档：DOC, DOCX
- 文本文件：TXT, MD, RTF

## 注意事项

1. **文件大小限制**：单个文件建议不超过 50MB
2. **批量处理**：建议每批次不超过 5 份试卷，以确保批改质量
3. **API密钥配置**：请在环境变量或 .env 文件中设置 OPENROUTER_API_KEY
4. **数学符号**：系统使用标准 Unicode 数学符号，不使用 LaTeX 格式

## 错误处理

所有函数都包含错误处理机制，返回的 `GradingResult` 对象包含：
- `success`: 是否成功
- `data`: 批改结果数据
- `error_message`: 错误信息（如果失败）
- `processing_time`: 处理时间

```python
if result.success:
    print(result.data)
else:
    print(f"批改失败：{result.error_message}") 