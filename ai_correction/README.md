# 🎓 AI智能批改系统

一个基于FastAPI + Next.js的现代化AI智能批改平台，支持多语言、多格式的作业批改。

## ✨ 特性

- 🤖 **AI智能批改**: 支持中英文作业批改
- 📁 **多文件支持**: 题目、评分标准、学生答案三文件批改
- 🎨 **现代化UI**: Next.js + Tailwind CSS + 动态效果
- 🔐 **用户认证**: JWT Token认证系统
- 📊 **历史记录**: 批改历史管理和查看
- ⚡ **热重载**: 开发时代码修改自动更新

## 🚀 快速启动

### 唯一启动方式（推荐）
```bash
# 双击运行统一启动器
start_unified.bat
```

**就这么简单！** 统一启动器会自动：
- ✅ 检查系统环境（Python + Node.js）
- ✅ 清理端口占用（8000 + 3000）
- ✅ 安装缺失依赖
- ✅ 启动后端服务（FastAPI）
- ✅ 启动前端服务（Next.js）
- ✅ 健康检查并打开浏览器

### 手动启动（开发者）
```bash
# 后端
python app.py

# 前端（新终端）
cd frontend
npm run dev
```

## 🌐 访问地址

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

## 🔑 测试账户

- 用户名: `test_user_1`
- 密码: `password1`

## 📋 启动文件说明

| 文件 | 功能 | 使用场景 |
|------|------|----------|
| `start_unified.bat` | 🚀 **统一启动器** | **唯一推荐**，一键启动全系统 |
| `启动说明.md` | 📖 详细使用指南 | 查看完整启动说明 |
| `check_status.bat` | 📊 服务状态检查 | 故障排查时使用 |

> ⚠️ **重要**: 已删除所有其他启动文件，统一使用 `start_unified.bat`

## 🛠️ 技术栈

### 后端
- **FastAPI**: 高性能Python Web框架
- **JWT**: 用户认证
- **Uvicorn**: ASGI服务器

### 前端
- **Next.js 15**: React全栈框架
- **TypeScript**: 类型安全
- **Tailwind CSS**: 原子化CSS
- **Radix UI**: 无障碍组件库

## 📁 项目结构

```
├── app.py                 # FastAPI后端主文件
├── functions/             # AI批改功能模块
├── 前端/                 # Next.js前端应用
│   ├── app/              # 应用页面
│   ├── components/       # React组件
│   └── lib/              # 工具库
├── start_unified.bat     # 统一启动器
├── check_status.bat      # 状态检查器
└── 运行指南.md           # 详细使用指南
```

## 🔧 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 运行状态检查
   check_status.bat
   
   # 清理端口（会重启服务）
   start_unified.bat
   ```

2. **依赖缺失**
   ```bash
   # 后端依赖
   pip install -r requirements.txt
   
   # 前端依赖
   cd 前端
   npm install
   ```

3. **服务无响应**
   - 检查防火墙设置
   - 确认端口8000和3000未被占用
   - 查看启动日志中的错误信息

## 📝 使用说明

1. **首次运行**: 双击 `start_unified.bat`，等待依赖安装
2. **日常使用**: 双击 `start_unified.bat`，快速启动
3. **开发调试**: 使用 `check_status.bat` 检查服务状态
4. **故障排查**: 查看启动器和服务窗口的日志输出
5. **详细指南**: 查看 `启动说明.md` 获取完整使用说明

## 🎯 API接口

- `POST /api/auth/login` - 用户登录
- `POST /api/auth/register` - 用户注册
- `POST /api/correction/upload` - 上传文件批改
- `GET /api/user/records` - 获取批改历史
- `GET /health` - 健康检查
- `GET /api/system/status` - 系统状态

## 📚 更多信息

- **启动指南**: `启动说明.md` - 详细的启动和故障排除指南
- **运行指南**: `运行指南.md` - 系统使用和功能说明
- **系统设计**: `MODULE_DESIGN.md` - 系统架构和模块设计

---

💡 **提示**: 现在只需要 `start_unified.bat` 一个文件即可启动整个系统！它会自动处理所有依赖检查、端口清理、服务启动和健康检查。 