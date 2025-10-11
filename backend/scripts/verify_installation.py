"""验证安装和环境配置."""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_python_version():
    """检查Python版本"""
    print("=" * 80)
    print("1. 检查Python版本")
    print("=" * 80)
    
    version = sys.version_info
    print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 10:
        print("✅ Python版本符合要求 (>= 3.10)")
        return True
    else:
        print("❌ Python版本过低,需要 >= 3.10")
        return False


def check_dependencies():
    """检查依赖包"""
    print("\n" + "=" * 80)
    print("2. 检查依赖包")
    print("=" * 80)
    
    required_packages = {
        "fastapi": "FastAPI",
        "uvicorn": "Uvicorn",
        "sqlalchemy": "SQLAlchemy",
        "alembic": "Alembic",
        "redis": "Redis",
        "langchain": "LangChain",
        "langgraph": "LangGraph",
        "langchain_openai": "LangChain OpenAI",
        "pydantic": "Pydantic",
        "httpx": "HTTPX",
    }
    
    all_installed = True
    
    for package, name in required_packages.items():
        try:
            __import__(package)
            print(f"✅ {name:<20} 已安装")
        except ImportError:
            print(f"❌ {name:<20} 未安装")
            all_installed = False
    
    return all_installed


def check_environment_variables():
    """检查环境变量"""
    print("\n" + "=" * 80)
    print("3. 检查环境变量")
    print("=" * 80)
    
    required_vars = {
        "SECRET_KEY": "应用密钥",
        "JWT_SECRET_KEY": "JWT密钥",
        "DATABASE_URL": "数据库URL",
        "REDIS_URL": "Redis URL",
    }
    
    optional_vars = {
        "OPENROUTER_API_KEY": "OpenRouter API密钥",
        "OPENAI_API_KEY": "OpenAI API密钥",
    }
    
    all_set = True
    
    print("\n必需变量:")
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            # 隐藏敏感信息
            if "KEY" in var or "SECRET" in var:
                display_value = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display_value = value[:50] + "..." if len(value) > 50 else value
            print(f"✅ {desc:<20} = {display_value}")
        else:
            print(f"❌ {desc:<20} 未设置")
            all_set = False
    
    print("\n可选变量 (至少需要一个API密钥):")
    has_api_key = False
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        if value:
            display_value = value[:8] + "..." if len(value) > 8 else "***"
            print(f"✅ {desc:<20} = {display_value}")
            if "API_KEY" in var:
                has_api_key = True
        else:
            print(f"⚠️  {desc:<20} 未设置")
    
    if not has_api_key:
        print("\n❌ 错误: 需要至少设置一个API密钥 (OPENROUTER_API_KEY 或 OPENAI_API_KEY)")
        all_set = False
    
    return all_set


def check_database_connection():
    """检查数据库连接"""
    print("\n" + "=" * 80)
    print("4. 检查数据库连接")
    print("=" * 80)
    
    try:
        from sqlalchemy import create_engine, text
        from app.core.config import settings
        
        if not settings.DATABASE_URL:
            print("❌ DATABASE_URL 未配置")
            return False
        
        # 创建同步引擎用于测试
        db_url = settings.DATABASE_URL.replace("+asyncpg", "")
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        print(f"✅ 数据库连接成功")
        print(f"   URL: {settings.DATABASE_URL[:50]}...")
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {str(e)}")
        return False


def check_redis_connection():
    """检查Redis连接"""
    print("\n" + "=" * 80)
    print("5. 检查Redis连接")
    print("=" * 80)
    
    try:
        import redis
        from app.core.config import settings
        
        if not settings.REDIS_URL:
            print("❌ REDIS_URL 未配置")
            return False
        
        client = redis.from_url(settings.REDIS_URL)
        client.ping()
        
        print(f"✅ Redis连接成功")
        print(f"   URL: {settings.REDIS_URL[:50]}...")
        return True
        
    except Exception as e:
        print(f"❌ Redis连接失败: {str(e)}")
        return False


def check_agent_modules():
    """检查Agent模块"""
    print("\n" + "=" * 80)
    print("6. 检查Agent模块")
    print("=" * 80)
    
    modules = {
        "app.agents.state": "GradingState",
        "app.agents.unified_grading_agent": "UnifiedGradingAgent",
        "app.agents.preprocess_agent": "PreprocessAgent",
        "app.agents.complexity_assessor": "ComplexityAssessor",
        "app.agents.smart_orchestrator": "SmartOrchestrator",
        "app.services.cache_service": "CacheService",
    }
    
    all_imported = True
    
    for module, class_name in modules.items():
        try:
            mod = __import__(module, fromlist=[class_name])
            getattr(mod, class_name)
            print(f"✅ {class_name:<25} 导入成功")
        except Exception as e:
            print(f"❌ {class_name:<25} 导入失败: {str(e)}")
            all_imported = False
    
    return all_imported


def check_api_routes():
    """检查API路由"""
    print("\n" + "=" * 80)
    print("7. 检查API路由")
    print("=" * 80)
    
    try:
        from app.main import app
        
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append((route.path, route.methods))
        
        # 检查关键路由
        key_routes = [
            "/health",
            "/api/v1/health",
            "/api/v1/v2/grading/submit-sync",
            "/api/v1/v2/grading/cache/stats",
        ]
        
        all_found = True
        for key_route in key_routes:
            found = any(key_route in path for path, _ in routes)
            if found:
                print(f"✅ {key_route:<40} 已注册")
            else:
                print(f"❌ {key_route:<40} 未找到")
                all_found = False
        
        print(f"\n总共注册了 {len(routes)} 个路由")
        return all_found
        
    except Exception as e:
        print(f"❌ 检查路由失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("\n🔍 开始验证安装和环境配置...\n")
    
    results = {
        "Python版本": check_python_version(),
        "依赖包": check_dependencies(),
        "环境变量": check_environment_variables(),
        "数据库连接": check_database_connection(),
        "Redis连接": check_redis_connection(),
        "Agent模块": check_agent_modules(),
        "API路由": check_api_routes(),
    }
    
    # 总结
    print("\n" + "=" * 80)
    print("验证总结")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:<15} {status}")
    
    print(f"\n总计: {passed}/{total} 项通过")
    
    if passed == total:
        print("\n🎉 所有检查通过!系统已准备就绪!")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 项检查失败,请修复后重试")
        print("\n💡 提示:")
        if not results["依赖包"]:
            print("   - 运行: pip install -r requirements.txt")
        if not results["环境变量"]:
            print("   - 复制 .env.example 为 .env 并填入配置")
        if not results["数据库连接"]:
            print("   - 启动PostgreSQL: docker-compose up -d postgres")
        if not results["Redis连接"]:
            print("   - 启动Redis: docker-compose up -d redis")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())

