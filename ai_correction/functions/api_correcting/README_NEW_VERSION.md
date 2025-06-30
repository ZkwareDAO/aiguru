# Calling API 新版本功能说明

## 📋 概述

本文档描述了 `calling_api.py` 文件的最新改进，使其完全兼容新的网站版本，并提供了更强大、更可靠的批改功能。

## 🚀 主要改进

### 1. 配置管理系统
- **APIConfig 类**：集中管理所有API配置
- **动态配置更新**：运行时修改API参数
- **配置状态监控**：实时查看当前配置状态

```python
# 获取API状态
status = get_api_status()

# 更新配置
new_config = {
    "max_tokens": 50000,  # 支持更长的输入输出
    "temperature": 0.8,
    "max_retries": 5
}
update_api_config(new_config)
```

### 2. 增强的错误处理和重试机制
- **自动重试**：API调用失败时自动重试（最多3次）
- **指数退避**：重试间隔递增，避免频繁请求
- **详细日志**：完整的操作日志记录
- **异常处理**：统一的错误处理机制

### 3. 标准化返回格式
- **GradingResult 类**：统一的结果包装器
- **JSON格式输出**：标准化的API响应格式
- **性能监控**：记录处理时间和时间戳
- **成功/失败状态**：明确的操作结果指示

```python
{
  "success": true,
  "data": { /* 实际数据 */ },
  "error_message": "",
  "processing_time": 2.5,
  "timestamp": 1751020035.625
}
```

### 4. 网站兼容接口

#### 4.1 生成评分方案
```python
result = web_generate_marking_scheme(
    image_files=["scheme1.png", "scheme2.png"],
    language="zh"
)
```

#### 4.2 使用评分方案批改
```python
result = web_correction_with_scheme(
    marking_scheme_files=["scheme.png"],
    student_answer_files=["answer.png"],
    strictness_level="中等",
    language="zh"
)
```

#### 4.3 自动生成方案并批改
```python
result = web_correction_without_scheme(
    student_answer_files=["answer.png"],
    strictness_level="严格",
    language="zh"
)
```

#### 4.4 多页PDF批改
```python
result = web_correction_multiple_answers(
    marking_scheme_files=["scheme.png"],
    student_pdf_path="answers.pdf",
    strictness_level="宽松",
    language="en"
)
```

### 5. 批处理功能
支持同时处理多个批改请求：

```python
batch_requests = [
    {
        "id": "student_001",
        "type": "with_scheme",
        "marking_scheme_files": ["scheme.png"],
        "student_answer_files": ["answer1.png"],
        "strictness_level": "中等",
        "language": "zh"
    },
    {
        "id": "student_002",
        "type": "without_scheme",
        "student_answer_files": ["answer2.png"],
        "strictness_level": "严格",
        "language": "zh"
    }
]

result = web_batch_correction(batch_requests)
```

### 6. 装饰器模式
- **@safe_api_call**：自动包装函数，提供统一的错误处理
- **性能监控**：自动记录执行时间
- **日志记录**：自动记录函数执行状态

## 🔧 技术改进

### 类型注解
所有函数都添加了完整的类型注解，提高代码可读性和IDE支持：

```python
def call_tongyiqianwen_api(
    input_text: str, 
    *input_contents, 
    system_message: str = "", 
    language: str = "zh"
) -> str:
```

### 日志系统
集成的日志系统提供详细的操作记录：

```python
logger.info(f"API调用尝试 {attempt + 1}/{api_config.max_retries}")
logger.error(f"API调用失败 (尝试 {attempt + 1}): {str(e)}")
```

### 模块导入兼容性
改进的导入机制，支持不同的调用方式：

```python
try:
    import prompts
except ImportError:
    from . import prompts
```

## 📊 性能优化

1. **连接复用**：OpenAI客户端的高效使用
2. **指数退避**：智能重试策略
3. **内存管理**：优化的文件处理
4. **并发处理**：支持批量并发处理

## 🛡️ 错误处理

### 分层错误处理
1. **API级别**：网络和服务错误
2. **功能级别**：业务逻辑错误
3. **数据级别**：文件和格式错误

### 错误分类
- **网络错误**：自动重试
- **参数错误**：立即返回错误信息
- **文件错误**：详细的错误描述
- **API限制**：优雅的降级处理

## 🔍 监控和调试

### 状态监控
```python
# 获取完整的API状态
status = get_api_status()
print(json.dumps(status, ensure_ascii=False, indent=2))
```

### 性能监控
所有操作都会记录执行时间，便于性能优化：

```json
{
  "processing_time": 2.5,
  "timestamp": 1751020035.625
}
```

## 🌍 多语言支持

完全支持中英文双语：
- 提示词自动选择
- 错误信息本地化
- 返回结果格式化

## 📝 使用示例

### 基本批改流程
```python
from functions.api_correcting.calling_api import web_correction_with_scheme

# 批改单个学生答案
result = web_correction_with_scheme(
    marking_scheme_files=["math_scheme.png"],
    student_answer_files=["student_answer.png"],
    strictness_level="中等",
    language="zh"
)

if result.success:
    print("批改成功:", result.data)
else:
    print("批改失败:", result.error_message)
```

### 批量处理
```python
from functions.api_correcting.calling_api import web_batch_correction

# 批量批改多个学生
batch_result = web_batch_correction(batch_requests)
print(f"成功处理: {batch_result.data['success_count']}/{batch_result.data['total_requests']}")
```

## 🔧 配置建议

### 生产环境配置
```python
production_config = {
    "max_tokens": 50000,  # 支持复杂的长篇批改任务
    "temperature": 0.3,   # 更稳定的输出
    "max_retries": 5,     # 更多重试次数
    "retry_delay": 2.0    # 更长的重试间隔
}
update_api_config(production_config)
```

### 开发环境配置
```python
development_config = {
    "max_tokens": 25000,  # 开发环境适中配置
    "temperature": 0.7,
    "max_retries": 3,
    "retry_delay": 1.0
}
update_api_config(development_config)
```

## 📈 版本兼容性

- ✅ **向后兼容**：保留所有原有函数
- ✅ **新接口**：提供标准化的网站接口
- ✅ **错误处理**：改进的错误处理机制
- ✅ **性能提升**：优化的API调用策略

## 🎯 总结

新版本的 `calling_api.py` 提供了：
- 🔄 **可靠性**：重试机制和错误处理
- 📊 **监控性**：详细的日志和性能数据
- 🔧 **可配置性**：动态配置管理
- 🌐 **网站兼容**：标准化的API接口
- ⚡ **高性能**：优化的处理流程
- 🛡️ **稳定性**：完善的异常处理

这些改进确保了批改系统在新网站版本中的稳定运行和最佳性能。 