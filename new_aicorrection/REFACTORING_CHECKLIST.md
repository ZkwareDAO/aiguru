# 🔄 new_aicorrection 项目重构清单

## 📋 重构目标
- ✅ 删除前后端分离架构（移除 `frontend/` 目录）
- ✅ 保留所有 LangGraph 核心代码
- ✅ 保留后端所有核心功能
- ✅ 保留所有文档和配置文件
- ✅ 清理过时和重复的文件

---

## 🗑️ 需要删除的文件和目录

### 1. 前端相关（整个目录）
```
❌ new_aicorrection/frontend/                    # 整个 Next.js 前端目录
   ├── app/
   ├── components/
   ├── hooks/
   ├── lib/
   ├── public/
   ├── styles/
   ├── node_modules/
   ├── package.json
   ├── package-lock.json
   ├── pnpm-lock.yaml
   ├── tsconfig.json
   ├── next.config.mjs
   ├── postcss.config.mjs
   ├── components.json
   ├── Dockerfile
   ├── nixpacks.toml
   └── ...其他前端文件
```

### 2. 前端相关配置文件（根目录）
```
❌ new_aicorrection/vercel.json                  # Vercel 部署配置
❌ new_aicorrection/quick_deploy.sh              # 前后端联合部署脚本
❌ new_aicorrection/deploy.py                    # 前后端联合部署脚本
❌ new_aicorrection/deploy_railway.bat           # 前后端联合部署脚本
❌ new_aicorrection/start_dev.bat                # 前后端联合启动脚本
```

### 3. 过时的部署和配置文档
```
❌ new_aicorrection/DEPLOYMENT_GUIDE.md          # 过时的部署指南（前后端）
❌ new_aicorrection/DEPLOYMENT_STATUS.md         # 过时的部署状态
❌ new_aicorrection/RELEASE_NOTES_v2.0.md        # 过时的发布说明
❌ new_aicorrection/railway_config_summary.md    # 过时的 Railway 配置总结
❌ new_aicorrection/railway_env_vars.txt         # 过时的环境变量文档
❌ new_aicorrection/fix_deployment.py            # 过时的部署修复脚本
❌ new_aicorrection/urgent_fix_deployment.py     # 过时的紧急修复脚本
```

### 4. 根目录的前端 Dockerfile
```
❌ new_aicorrection/Dockerfile                   # 前端 Dockerfile（后端已有）
❌ new_aicorrection/Procfile                     # Procfile（不需要）
```

### 5. 后端重复的文档
```
❌ new_aicorrection/backend/README_new.md        # 重复的 README（保留 README.md）
❌ new_aicorrection/backend/SETUP_SUMMARY.md     # 过时的设置总结
❌ new_aicorrection/backend/TEST_README.md       # 过时的测试说明
```

### 6. 后端的测试覆盖率报告
```
❌ new_aicorrection/backend/htmlcov/             # HTML 覆盖率报告（不需要提交）
```

### 7. 后端的本地数据库文件
```
❌ new_aicorrection/backend/ai_education.db      # SQLite 本地数据库（不需要）
```

---

## ✅ 需要保留的文件和目录

### 1. LangGraph 核心代码（必须保留）
```
✅ new_aicorrection/backend/app/services/langgraph_grading_workflow.py
✅ new_aicorrection/backend/app/services/langgraph_state.py
✅ new_aicorrection/backend/app/services/langgraph_nodes/
   ├── __init__.py
   ├── upload_validator.py
   ├── document_ingestor.py
   ├── image_enhancer.py
   ├── region_locator.py
   ├── rubric_interpreter.py
   ├── scoring_agent.py
   └── result_assembler.py
✅ new_aicorrection/backend/app/api/langgraph_grading.py
```

### 2. 后端核心代码
```
✅ new_aicorrection/backend/app/
   ├── main.py
   ├── api/                    # 所有 API 端点
   ├── models/                 # 数据库模型
   ├── schemas/                # Pydantic 模式
   ├── services/               # 业务逻辑
   ├── core/                   # 核心配置
   └── utils/                  # 工具函数
```

### 3. 数据库和认证
```
✅ new_aicorrection/backend/alembic/             # 数据库迁移
✅ new_aicorrection/backend/alembic.ini
✅ new_aicorrection/backend/app/core/auth.py
✅ new_aicorrection/backend/app/core/firebase_auth.py
✅ new_aicorrection/backend/app/core/database.py
```

### 4. 配置和依赖
```
✅ new_aicorrection/backend/requirements.txt
✅ new_aicorrection/backend/requirements-dev.txt
✅ new_aicorrection/backend/pyproject.toml
✅ new_aicorrection/backend/.env.example
✅ new_aicorrection/backend/config/
✅ new_aicorrection/backend/railway.toml.example
✅ new_aicorrection/backend/docker-compose.yml
✅ new_aicorrection/backend/Dockerfile
```

### 5. 文档（保留所有）
```
✅ new_aicorrection/backend/WORKFLOW_DIAGRAM.md
✅ new_aicorrection/backend/LANGGRAPH_IMPLEMENTATION.md
✅ new_aicorrection/backend/DEPLOYMENT_CHECKLIST.md
✅ new_aicorrection/backend/QUICK_START.md
✅ new_aicorrection/backend/IMPLEMENTATION_SUMMARY.md
✅ new_aicorrection/backend/UPLOAD_SUMMARY.md
✅ new_aicorrection/backend/README.md
✅ new_aicorrection/docs/                       # 所有需求文档
```

### 6. 测试
```
✅ new_aicorrection/backend/tests/               # 所有测试文件
✅ new_aicorrection/backend/test_*.py            # 测试脚本
```

### 7. 脚本
```
✅ new_aicorrection/backend/scripts/             # 所有脚本
✅ new_aicorrection/backend/deploy.sh
✅ new_aicorrection/backend/deploy.bat
```

### 8. 根目录文档
```
✅ new_aicorrection/README.md                    # 项目主文档
```

---

## 📊 删除统计

| 类别 | 数量 | 说明 |
|------|------|------|
| 前端目录 | 1 | `frontend/` 整个目录 |
| 前端配置 | 1 | `vercel.json` |
| 部署脚本 | 4 | 前后端联合脚本 |
| 过时文档 | 8 | 部署和配置文档 |
| 重复文档 | 3 | 后端重复文档 |
| 其他文件 | 3 | Dockerfile, Procfile, 数据库 |
| 覆盖率报告 | 1 | htmlcov 目录 |
| **总计** | **~21** | **包括 frontend 目录下的所有文件** |

---

## 🎯 重构后的项目结构

```
new_aicorrection/
├── backend/                          # 后端应用
│   ├── app/
│   │   ├── api/                     # API 端点
│   │   ├── services/
│   │   │   ├── langgraph_*          # LangGraph 核心
│   │   │   └── langgraph_nodes/     # 所有节点
│   │   ├── models/                  # 数据库模型
│   │   ├── schemas/                 # Pydantic 模式
│   │   ├── core/                    # 核心配置
│   │   └── main.py
│   ├── tests/                       # 测试
│   ├── alembic/                     # 数据库迁移
│   ├── scripts/                     # 脚本
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── WORKFLOW_DIAGRAM.md
│   ├── LANGGRAPH_IMPLEMENTATION.md
│   ├── DEPLOYMENT_CHECKLIST.md
│   ├── QUICK_START.md
│   └── README.md
├── docs/                            # 需求文档
├── README.md                        # 项目主文档
└── .env.example
```

---

## ⚠️ 注意事项

1. **确认删除前**：请仔细审查此清单
2. **备份重要文件**：如有自定义配置，请先备份
3. **更新文档**：删除后需要更新相关文档中的引用
4. **Git 提交**：删除后需要 `git add -A && git commit`

---

## ✨ 重构完成后的优势

- ✅ 项目结构更清晰（仅保留后端）
- ✅ 减少不必要的文件（删除前端相关）
- ✅ 保留所有核心功能（LangGraph + 数据库 + 认证）
- ✅ 文档更精简（移除过时文档）
- ✅ 部署更简单（单体后端）
- ✅ 代码库更轻量（减少 ~200+ 个文件）

---

**请确认此清单，我将立即执行删除操作。**

