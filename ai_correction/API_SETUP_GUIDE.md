# AI批改系统 API 配置指南

## 🚨 问题解决方案

### 问题1：OpenAI API调用频率限制错误
**错误信息：** `ERROR_OPENAI_RATE_LIMIT_EXCEEDED`

**解决方案：**
1. **自动模型切换** - 系统现在会自动切换到备用模型
2. **免费模型备选** - 包含多个免费模型作为备用
3. **手动重置** - 在界面上点击"🔄 重置到主要模型"按钮

### 问题2：没有可处理的文件内容
**错误信息：** `❌ 没有可处理的文件内容`

**解决方案：**
1. 确保文件正确上传到对应区域
2. 检查文件格式是否支持（txt、pdf、jpg、png、doc等）
3. 确认文件没有损坏
4. 重新上传文件

## 📋 API配置步骤

### 方法1：环境变量配置（推荐）

**Windows PowerShell：**
```powershell
$env:OPENROUTER_API_KEY="your_api_key_here"
streamlit run streamlit_simple.py --server.port 8502
```

**Windows CMD：**
```cmd
set OPENROUTER_API_KEY=your_api_key_here
streamlit run streamlit_simple.py --server.port 8502
```

**Linux/Mac：**
```bash
export OPENROUTER_API_KEY="your_api_key_here"
streamlit run streamlit_simple.py --server.port 8502
```

### 方法2：.env文件配置

1. **复制配置模板：**
   ```bash
   copy config_template.env .env
   ```

2. **编辑.env文件，填入您的API密钥：**
   ```
   OPENROUTER_API_KEY=your_actual_api_key_here
   ```

3. **重启应用程序**

## 🔑 获取API密钥

### OpenRouter（推荐）
1. 访问 [OpenRouter](https://openrouter.ai)
2. 注册账户并登录
3. 前往 [API Keys](https://openrouter.ai/keys)
4. 生成新的API密钥
5. 复制密钥（格式：`or-xxxxxx`）

### OpenAI（备选）
1. 访问 [OpenAI](https://platform.openai.com)
2. 登录您的账户
3. 前往 [API Keys](https://platform.openai.com/api-keys)
4. 创建新的API密钥
5. 复制密钥（格式：`sk-xxxxxx`）

## 🤖 支持的模型

### 主要模型（付费）
- `google/gemini-2.5-flash-lite-preview-06-17` - 主要模型
- `google/gemini-flash-1.5` - 备用模型1
- `google/gemini-pro` - 备用模型2
- `anthropic/claude-3-haiku` - 备用模型3

### 免费备用模型
- `meta-llama/llama-3-8b-instruct:free`
- `microsoft/wizardlm-2-8x22b:free`
- `gryphe/mythomist-7b:free`

## 🔧 故障排除

### 频率限制错误
- 系统会自动切换到备用模型
- 可在界面上手动重置模型
- 考虑使用免费模型作为备选

### 认证错误
- 检查API密钥格式是否正确
- 确认API密钥未过期
- 验证账户余额是否充足

### 文件处理错误
- 支持的格式：txt、pdf、jpg、png、gif、doc、docx
- 文件大小限制：单个文件不超过4MB
- 确保文件未损坏

## 🎯 使用建议

1. **首次使用：** 建议先配置OpenRouter API密钥
2. **频率限制：** 系统会自动处理，无需手动干预
3. **文件上传：** 确保文件格式正确，内容清晰
4. **错误处理：** 查看详细日志信息进行排错

## 📞 技术支持

如果遇到其他问题，请：
1. 查看控制台日志输出
2. 检查`logs/api_debug.log`文件
3. 确认网络连接稳定
4. 重启应用程序

---

**最后更新：** 2025-07-04
**版本：** v2.0 - 增强错误处理和多模型支持 