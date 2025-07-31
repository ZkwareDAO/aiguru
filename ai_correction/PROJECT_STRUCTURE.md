# 📁 AI批改系统项目结构

## 🎯 核心文件

### 主应用文件
- `streamlit_simple.py` - 主应用文件（155KB，3627行）
- `database.py` - 数据库管理模块（16KB，500行）

### 启动文件
- `start_simple.py` - Python启动脚本
- `start.bat` - Windows一键启动器
- `fix_session_state.py` - Session state修复脚本

### 配置文件
- `requirements.txt` - Python依赖列表
- `config_template.env` - API配置模板
- `.env` - 实际配置文件（需要创建）

### 文档文件
- `README.md` - 项目说明文档
- `RUNNING_GUIDE.md` - 详细运行指南
- `MODULE_DESIGN.md` - 系统设计文档

## 📂 目录结构

### 核心功能目录
```
functions/
├── api_correcting/          # AI批改核心功能
│   ├── calling_api.py      # API调用模块
│   ├── intelligent_batch_processor.py  # 智能批处理
│   ├── document_processor.py # 多模态文档处理器
│   ├── result_generator.py  # 结果生成器
│   ├── prompts_simplified.py  # 提示词模板
│   └── fonts/              # 字体文件
├── ai_recognition.py       # AI识别模块
```

### 数据目录
```
class_files/                # 班级系统文件
├── assignments/           # 作业文件
├── submissions/           # 学生提交
└── marking/              # 批改文件

uploads/                   # 用户上传文件
temp_uploads/              # 临时文件
logs/                      # 日志文件
test_files/                # 测试文件
├── ANSWER_test_student.txt
└── MARKING_test_standard.txt
```

### 数据库文件
- `class_system.db` - 班级系统数据库

## 🗑️ 已清理的冗余文件

### 删除的文档文件
- 各种修复总结文档（20+个）
- API配置指南文档
- 系统升级总结文档
- 批处理系统指南文档

### 删除的测试文件
- HTML测试结果文件
- JSON测试数据文件
- 文本测试结果文件

### 删除的脚本文件
- 各种修复脚本
- 调试脚本
- 编码修复脚本

### 删除的目录
- 空的pages、modules、database、models目录
- professional_logs、professional_uploads目录
- .yoyo目录
- __pycache__目录

## 📊 清理效果

### 文件数量减少
- **删除文档**: 20+ 个MD文件
- **删除测试文件**: 10+ 个测试结果文件
- **删除脚本**: 5+ 个临时脚本
- **删除目录**: 8+ 个空目录

### 项目大小优化
- 删除了大量冗余的HTML、JSON、TXT文件
- 清理了临时生成的测试结果
- 移除了重复的配置和文档

### 结构清晰化
- 保留了核心功能文件
- 简化了目录结构
- 统一了启动方式

## 🚀 运行方式

### 快速启动
```bash
# Windows
start.bat

# 其他系统
python start_simple.py
```

### 直接启动
```bash
streamlit run streamlit_simple.py --server.port 8501
```

## 📋 保留的核心功能

1. **AI批改系统** - 完整的批改功能
2. **班级管理系统** - 教师和学生功能
3. **文件处理** - 多格式文件支持
4. **数据库管理** - SQLite数据库
5. **用户认证** - 登录注册系统
6. **结果展示** - 批改结果展示

## 🔧 维护建议

1. **定期清理**: 定期删除temp_uploads中的临时文件
2. **日志管理**: 定期清理logs目录中的旧日志
3. **测试文件**: 保留test_files中的核心测试文件
4. **数据库备份**: 定期备份class_system.db

---

💡 **提示**: 项目现在结构清晰，只保留核心功能文件，便于维护和部署。 