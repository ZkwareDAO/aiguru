@echo off
REM 阶段一 - 一键安装和测试脚本 (Windows)

echo ==================================
echo 🚀 阶段一 - 安装和测试
echo ==================================

REM 检查Python版本
echo.
echo 1. 检查Python版本...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python未安装或不在PATH中
    pause
    exit /b 1
)

REM 检查虚拟环境
echo.
echo 2. 检查虚拟环境...
if not defined VIRTUAL_ENV (
    echo ⚠️  未检测到虚拟环境
    echo 建议创建虚拟环境:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    set /p continue="是否继续? (y/n): "
    if /i not "%continue%"=="y" exit /b 1
)

REM 安装依赖
echo.
echo 3. 安装依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)

REM 检查环境变量
echo.
echo 4. 检查环境变量...
if not exist .env (
    echo ❌ .env 文件不存在
    echo 正在从 .env.example 创建...
    copy .env.example .env
    echo ✅ 已创建 .env 文件
    echo ⚠️  请编辑 .env 文件并填入必要的配置
    echo 必需配置:
    echo   - SECRET_KEY
    echo   - JWT_SECRET_KEY
    echo   - DATABASE_URL
    echo   - REDIS_URL
    echo   - OPENROUTER_API_KEY 或 OPENAI_API_KEY
    pause
)

REM 运行验证脚本
echo.
echo 5. 验证安装...
python scripts\verify_installation.py
if %errorlevel% neq 0 (
    echo ❌ 验证失败,请修复问题后重试
    pause
    exit /b 1
)

REM 检查数据库
echo.
echo 6. 检查数据库...
echo 确保PostgreSQL正在运行...
echo 如果使用Docker: docker-compose up -d postgres
set /p db_ready="数据库已启动? (y/n): "
if /i not "%db_ready%"=="y" (
    echo 请先启动数据库
    pause
    exit /b 1
)

REM 运行数据库迁移
echo.
echo 7. 运行数据库迁移...
alembic upgrade head
if %errorlevel% equ 0 (
    echo ✅ 数据库迁移完成
) else (
    echo ⚠️  数据库迁移失败或已是最新
)

REM 检查Redis
echo.
echo 8. 检查Redis...
echo 确保Redis正在运行...
echo 如果使用Docker: docker-compose up -d redis
set /p redis_ready="Redis已启动? (y/n): "
if /i not "%redis_ready%"=="y" (
    echo 请先启动Redis
    pause
    exit /b 1
)

REM 运行单元测试
echo.
echo 9. 运行单元测试...
pytest tests\test_agents.py -v
if %errorlevel% equ 0 (
    echo ✅ 单元测试通过
) else (
    echo ❌ 单元测试失败
    pause
    exit /b 1
)

REM 运行集成测试
echo.
echo 10. 运行集成测试...
python scripts\integration_test.py
if %errorlevel% equ 0 (
    echo ✅ 集成测试通过
) else (
    echo ⚠️  集成测试失败
)

REM 运行成本分析
echo.
echo 11. 运行成本分析...
set /p run_cost="是否运行成本分析? (需要API密钥) (y/n): "
if /i "%run_cost%"=="y" (
    python scripts\cost_analyzer.py
)

REM 运行演示
echo.
echo 12. 运行演示...
set /p run_demo="是否运行演示脚本? (需要API密钥) (y/n): "
if /i "%run_demo%"=="y" (
    python demo_agent_grading.py
)

REM 完成
echo.
echo ==================================
echo 🎉 安装和测试完成!
echo ==================================

echo.
echo 下一步:
echo 1. 启动后端服务:
echo    uvicorn app.main:app --reload
echo.
echo 2. 访问API文档:
echo    http://localhost:8000/docs
echo.
echo 3. 查看文档:
echo    - 快速开始: ..\QUICKSTART.md
echo    - 实施总结: ..\IMPLEMENTATION_SUMMARY.md
echo    - 检查清单: ..\CHECKLIST.md
echo.

set /p start_server="是否现在启动后端服务? (y/n): "
if /i "%start_server%"=="y" (
    echo.
    echo 启动后端服务...
    uvicorn app.main:app --reload
)

pause

