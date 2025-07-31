# 🚀 AI批改系统运行指南

## 📋 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows 10/11, macOS, Linux
- **内存**: 至少 4GB RAM
- **网络**: 需要互联网连接（用于AI API调用）

## 🎯 快速启动（推荐）

### Windows用户
```bash
# 双击运行启动器
start.bat
```

### 其他系统用户
```bash
# 使用Python启动
python start_simple.py
```

## 🔧 详细启动步骤

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置API密钥
```bash
# 复制配置模板
copy config_template.env .env

# 编辑.env文件，填入您的API密钥
# 获取API密钥：https://openrouter.ai/keys
```

### 3. 启动系统
```bash
# 方法1：使用启动脚本（推荐）
python start_simple.py

# 方法2：直接启动
streamlit run streamlit_simple.py --server.port 8501
```

## 🌐 访问系统

启动成功后，在浏览器中访问：
- **主界面**: http://localhost:8501
- **班级系统**: http://localhost:8501 (选择班级系统模式)

## 🛠️ 故障排除

### 问题1: "Bad message format" 或 "Cannot handle type undefined"

**原因**: Streamlit session state包含JavaScript undefined值

**解决方案**:
```bash
# 运行修复脚本
python fix_session_state.py

# 或者清理浏览器缓存后重新启动
```

### 问题2: 端口被占用

**解决方案**:
```bash
# 使用其他端口
streamlit run streamlit_simple.py --server.port 8502

# 或者检查并关闭占用进程
netstat -ano | findstr :8501
```

### 问题3: 依赖安装失败

**解决方案**:
```bash
# 升级pip
python -m pip install --upgrade pip

# 重新安装依赖
pip install -r requirements.txt --force-reinstall

# 或者使用虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 问题4: API密钥错误

**解决方案**:
1. 确保 `.env` 文件存在且格式正确
2. 验证API密钥是否有效
3. 检查网络连接
4. 访问 https://openrouter.ai/keys 重新生成密钥

## 📱 系统功能

### 班级系统模式
- 👨‍🏫 **教师功能**: 创建班级、发布作业、批改作业
- 👨‍🎓 **学生功能**: 加入班级、提交作业、查看成绩
- 🤖 **AI批改**: 智能批改作业并给出评分
- 📊 **统计分析**: 班级和作业统计

### 独立批改模式
- 📁 **文件上传**: 支持多种格式（图片、PDF、Word、文本），使用多模态大模型直接处理
- 🤖 **AI批改**: 智能识别和评分
- 📋 **结果展示**: 详细的批改报告

## 🔑 测试账户

### 班级系统测试账户
- **老师账户**: `teacher1` / `123456`
- **学生账户**: `student1` / `123456`

### 独立批改模式
- **演示账户**: `demo` / `demo`

## 📁 文件结构

```
ai_correction/
├── streamlit_simple.py      # 主应用文件
├── start_simple.py          # 启动脚本
├── start.bat               # Windows启动器
├── fix_session_state.py    # 修复脚本
├── requirements.txt        # 依赖列表
├── config_template.env     # 配置模板
├── .env                    # 配置文件（需要创建）
├── temp_uploads/          # 临时文件目录
├── logs/                  # 日志目录
└── uploads/               # 上传文件目录
```

## 🎯 使用建议

1. **首次使用**: 建议使用班级系统模式，功能更完整
2. **简单批改**: 如果只需要批改功能，使用独立模式
3. **开发调试**: 使用 `start_simple.py` 脚本，包含环境检查
4. **生产部署**: 配置正确的API密钥和环境变量

## 📞 技术支持

如果遇到问题，请：

1. 检查错误日志（在logs目录中）
2. 确认Python版本和依赖安装
3. 验证API密钥配置
4. 清理浏览器缓存和Streamlit缓存

## 🔄 更新系统

```bash
# 拉取最新代码
git pull

# 更新依赖
pip install -r requirements.txt --upgrade

# 重新启动系统
python start_simple.py
```

---

💡 **提示**: 如果遇到任何问题，请先运行 `python fix_session_state.py` 来修复session state问题，然后重新启动系统。 