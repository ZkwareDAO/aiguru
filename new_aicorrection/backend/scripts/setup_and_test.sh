#!/bin/bash

# 阶段一 - 一键安装和测试脚本

set -e  # 遇到错误立即退出

echo "=================================="
echo "🚀 阶段一 - 安装和测试"
echo "=================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Python版本
echo -e "\n${YELLOW}1. 检查Python版本...${NC}"
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 检查是否在虚拟环境中
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}⚠️  未检测到虚拟环境${NC}"
    echo "建议创建虚拟环境:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate  # Linux/Mac"
    echo "  venv\\Scripts\\activate     # Windows"
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 安装依赖
echo -e "\n${YELLOW}2. 安装依赖...${NC}"
pip install -r requirements.txt

# 检查环境变量
echo -e "\n${YELLOW}3. 检查环境变量...${NC}"
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env 文件不存在${NC}"
    echo "正在从 .env.example 创建..."
    cp .env.example .env
    echo -e "${GREEN}✅ 已创建 .env 文件${NC}"
    echo -e "${YELLOW}⚠️  请编辑 .env 文件并填入必要的配置${NC}"
    echo "必需配置:"
    echo "  - SECRET_KEY"
    echo "  - JWT_SECRET_KEY"
    echo "  - DATABASE_URL"
    echo "  - REDIS_URL"
    echo "  - OPENROUTER_API_KEY 或 OPENAI_API_KEY"
    read -p "配置完成后按回车继续..."
fi

# 运行验证脚本
echo -e "\n${YELLOW}4. 验证安装...${NC}"
python scripts/verify_installation.py
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 验证失败,请修复问题后重试${NC}"
    exit 1
fi

# 检查数据库
echo -e "\n${YELLOW}5. 检查数据库...${NC}"
echo "确保PostgreSQL正在运行..."
echo "如果使用Docker: docker-compose up -d postgres"
read -p "数据库已启动? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "请先启动数据库"
    exit 1
fi

# 运行数据库迁移
echo -e "\n${YELLOW}6. 运行数据库迁移...${NC}"
alembic upgrade head
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 数据库迁移完成${NC}"
else
    echo -e "${YELLOW}⚠️  数据库迁移失败或已是最新${NC}"
fi

# 检查Redis
echo -e "\n${YELLOW}7. 检查Redis...${NC}"
echo "确保Redis正在运行..."
echo "如果使用Docker: docker-compose up -d redis"
read -p "Redis已启动? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "请先启动Redis"
    exit 1
fi

# 运行单元测试
echo -e "\n${YELLOW}8. 运行单元测试...${NC}"
pytest tests/test_agents.py -v
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 单元测试通过${NC}"
else
    echo -e "${RED}❌ 单元测试失败${NC}"
    exit 1
fi

# 运行集成测试
echo -e "\n${YELLOW}9. 运行集成测试...${NC}"
python scripts/integration_test.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 集成测试通过${NC}"
else
    echo -e "${YELLOW}⚠️  集成测试失败${NC}"
fi

# 运行成本分析
echo -e "\n${YELLOW}10. 运行成本分析...${NC}"
read -p "是否运行成本分析? (需要API密钥) (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python scripts/cost_analyzer.py
fi

# 运行演示
echo -e "\n${YELLOW}11. 运行演示...${NC}"
read -p "是否运行演示脚本? (需要API密钥) (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python demo_agent_grading.py
fi

# 完成
echo -e "\n=================================="
echo -e "${GREEN}🎉 安装和测试完成!${NC}"
echo "=================================="

echo -e "\n下一步:"
echo "1. 启动后端服务:"
echo "   uvicorn app.main:app --reload"
echo ""
echo "2. 访问API文档:"
echo "   http://localhost:8000/docs"
echo ""
echo "3. 查看文档:"
echo "   - 快速开始: ../QUICKSTART.md"
echo "   - 实施总结: ../IMPLEMENTATION_SUMMARY.md"
echo "   - 检查清单: ../CHECKLIST.md"
echo ""

read -p "是否现在启动后端服务? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${GREEN}启动后端服务...${NC}"
    uvicorn app.main:app --reload
fi

