# AI批改系统 API 更新总结

## 更新日期
2024年1月

## 主要变更

### 1. 简化批改模式
将原有的多种批改模式简化为两种：
- **有批改标准模式**：用户提供批改标准，系统根据标准进行批改
- **无批改标准模式**：系统自动生成批改标准，然后进行批改

### 2. 新的提示词系统
根据用户提供的新提示词文档，更新了：
- `marking_scheme_prompt`：使用数学试卷批改标准生成提示词
- `correction_with_standard_prompt`：有标准答案的批量批改提示词
- `correction_without_standard_prompt`：无标准答案的批量批改提示词

### 3. 新增核心函数
- `batch_correction_with_standard()`：有批改标准的批量批改
- `batch_correction_without_standard()`：无批改标准的批量批改（自动生成标准）
- `format_correction_prompt()`：根据模式生成相应的提示词

### 4. 改进的批改流程

#### 有批改标准模式流程：
1. 接收批改标准文件和学生答案文件
2. 使用 `correction_with_standard_prompt` 构建提示词
3. 调用API进行批改
4. 返回批改结果

#### 无批改标准模式流程：
1. 接收题目文件和学生答案文件
2. 使用 `marking_scheme_prompt` 生成批改标准
3. 使用 `correction_without_standard_prompt` 构建提示词
4. 调用API进行批改
5. 返回批改结果

### 5. 输出格式优化
新的输出格式更加规范化，包含：
- 学生个人批改结果（每题详细批改）
- 总评（总分、优势、建议）
- 班级整体分析（平均分、易错题分析、教学建议）

## 向后兼容性

为确保现有代码不受影响，保留了以下函数：
- `correction_with_marking_scheme()`
- `correction_without_marking_scheme()`
- `generate_marking_scheme()`
- `efficient_correction_single()`
- `batch_efficient_correction()`

这些函数内部已更新为调用新的批改函数。

## 使用建议

### 新项目
建议使用新的简化函数：
```python
# 有批改标准
batch_correction_with_standard(marking_files, answer_files)

# 无批改标准
batch_correction_without_standard(question_files, answer_files)
```

### 现有项目
可以继续使用旧函数名，功能保持不变。

## 文件变更列表

1. **prompts.py**
   - 更新了所有提示词
   - 新增 `format_correction_prompt()` 函数
   - 简化了严格程度描述

2. **calling_api.py**
   - 新增 `batch_correction_with_standard()`
   - 新增 `batch_correction_without_standard()`
   - 更新了现有函数以使用新逻辑

3. **__init__.py**（新增）
   - 导出新的API函数
   - 维护向后兼容性

4. **API_USAGE_GUIDE.md**（新增）
   - 详细的使用指南
   - 示例代码
   - 输出格式说明

## 注意事项

1. 新的批改函数统一返回字符串格式的结果
2. Web接口函数返回 `GradingResult` 对象
3. 所有函数都包含完整的错误处理
4. 支持多种文件格式（图片、PDF、Word、文本）

## 后续计划

- 持续优化提示词以提高批改准确性
- 根据用户反馈调整输出格式
- 添加更多的批改选项和自定义功能 