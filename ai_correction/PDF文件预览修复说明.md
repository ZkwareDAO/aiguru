# PDF文件预览修复说明

## 修复内容

### 1. 后端API改进 (`main.py`)
- **PDF文本提取**: 使用PyPDF2库提取PDF文本内容，优先显示文本预览
- **PDF图像预览**: 当文本提取失败时，提供PDF的base64编码用于图像显示
- **错误处理**: 完善的错误处理和回退机制
- **文件大小显示**: 显示文件大小信息

### 2. 前端预览改进 (`frontend/app/detail/[id]/page.tsx`)
- **PDF专用处理**: 添加`isPdfFile()`函数和PDF文件专用预览逻辑
- **embed标签支持**: 使用HTML embed标签直接显示PDF文件
- **调试信息**: 添加详细的控制台调试信息
- **错误处理**: 改进错误处理和用户反馈

## 功能特性

### PDF文件处理优先级
1. **文本提取** (最优): 提取PDF前5页的文本内容，限制2000字符预览
2. **图像显示** (备选): 将PDF作为base64编码的图像显示
3. **下载链接** (兜底): 提供下载链接供用户查看

### 支持的文件类型
- **图片**: JPG, PNG, GIF, BMP, WebP
- **文本**: TXT, MD, PY, JS, HTML, CSS, JSON, XML
- **PDF**: 文本提取或图像预览
- **其他**: 显示文件信息和下载链接

## 测试步骤

### 1. 启动服务
```bash
# 后端服务
python main.py

# 前端服务
cd frontend
npm run dev
```

### 2. 测试流程
1. **登录系统**: 使用测试账号登录
2. **上传PDF文件**: 在批改页面上传包含PDF的文件
3. **查看批改结果**: 等待批改完成
4. **进入详情页面**: 点击"查看详情对照"按钮
5. **测试文件预览**: 
   - 点击PDF文件标签
   - 点击"加载预览"按钮
   - 观察预览效果

### 3. 调试信息
打开浏览器开发者工具(F12)，查看控制台输出：
- `加载文件预览: [文件路径]`
- `请求URL: [API地址]`
- `API响应数据: [响应内容]`
- `处理后的内容: [处理结果]`

## 预期效果

### PDF文本提取成功
- 显示PDF文件的文本内容预览
- 格式：`PDF文件内容预览 (XX KB): [文本内容]`

### PDF图像显示
- 使用embed标签直接显示PDF
- 支持缩放和滚动查看

### 错误处理
- 显示具体的错误信息
- 提供下载链接作为备选方案

## 技术细节

### 后端改进
```python
# PDF文本提取
import PyPDF2
with open(file_path, 'rb') as pdf_file:
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page_num in range(min(len(pdf_reader.pages), 5)):
        page = pdf_reader.pages[page_num]
        text += page.extract_text() + "\n"

# PDF base64编码
import base64
with open(file_path, 'rb') as f:
    pdf_data = f.read()
    base64_data = base64.b64encode(pdf_data).decode('utf-8')
```

### 前端改进
```typescript
// PDF文件检测
const isPdfFile = (filename: string) => {
  return filename.split('.').pop()?.toLowerCase() === 'pdf'
}

// PDF预览显示
{isPdf ? (
  <embed
    src={filePreviewData[fileInfo?.saved_path || '']}
    type="application/pdf"
    className="w-full h-full min-h-[400px] rounded-lg shadow-lg"
  />
) : (
  // 图片预览
)}
```

## 故障排除

### 常见问题
1. **PDF无法显示**: 检查PyPDF2是否安装 (`pip install PyPDF2`)
2. **文件路径错误**: 检查文件是否存在于用户目录
3. **权限问题**: 确认用户有访问文件的权限
4. **网络请求失败**: 检查后端服务是否正常运行

### 调试方法
1. 查看浏览器控制台的调试信息
2. 检查后端日志输出
3. 验证API响应格式
4. 测试文件下载功能

## 注意事项

1. **文件大小限制**: 大型PDF文件可能影响预览性能
2. **浏览器兼容性**: embed标签在某些浏览器中可能显示效果不同
3. **安全考虑**: 文件路径验证确保用户只能访问自己的文件
4. **性能优化**: PDF文本提取限制为前5页，内容限制2000字符

这个修复应该能够解决PDF文件无法预览的问题，并提供更好的用户体验。 