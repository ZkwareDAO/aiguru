#!/usr/bin/env python3
"""
AI教育平台2.0 Railway自动部署脚本
支持OpenRouter Gemini 2.5 Flash Lite AI模型
"""

import subprocess
import sys
import json
import os

def run_command(cmd, check=True):
    """执行命令并返回结果"""
    print(f"🔧 执行命令: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {e}")
        if e.stderr:
            print(f"错误信息: {e.stderr}")
        return None

def check_railway_auth():
    """检查Railway认证状态"""
    print("1️⃣ 检查Railway认证状态...")
    result = run_command("railway whoami", check=False)
    if result and result.returncode == 0:
        print("✅ Railway认证成功")
        return True
    else:
        print("❌ 请先登录Railway: railway login")
        return False

def get_project_status():
    """获取项目状态"""
    print("2️⃣ 获取项目状态...")
    result = run_command("railway status", check=False)
    return result

def setup_environment_variables():
    """设置环境变量"""
    print("3️⃣ 设置环境变量...")
    
    # 数据库连接字符串
    db_vars = [
        "DATABASE_URL=postgresql://postgres:sfraebGPmjkZtWpAsHqeHrxUrxuDSQFz@postgres.railway.internal:5432/railway",
        "REDIS_URL=redis://default:fXZjFSKZfAfkTiqBfomlFHzcddmZZLLv@redis.railway.internal:6379"
    ]
    
    # 应用配置
    app_vars = [
        "ENVIRONMENT=production",
        "DEBUG=false",
        "HOST=0.0.0.0",
        "PORT=8000",
        "CORS_ORIGINS=*",
        "SECRET_KEY=aiguru2-super-secret-key-for-jwt-tokens-production",
        "MAX_FILE_SIZE=52428800",
        "LOG_LEVEL=INFO"
    ]
    
    print("📝 需要手动配置的关键环境变量：")
    print("   OPENROUTER_API_KEY=sk-or-v1-your-api-key")
    print("   FIREBASE_PROJECT_ID=your-project-id") 
    print("   FIREBASE_CLIENT_EMAIL=your-service-account-email")
    print("   FIREBASE_PRIVATE_KEY=your-private-key")
    
    return db_vars + app_vars

def deploy_backend():
    """部署后端服务"""
    print("4️⃣ 部署后端服务...")
    
    # 切换到后端目录
    os.chdir("backend")
    
    # 创建服务并部署
    result = run_command("railway up", check=False)
    
    # 返回根目录
    os.chdir("..")
    
    return result

def deploy_frontend():
    """部署前端服务"""
    print("5️⃣ 部署前端服务...")
    
    # 切换到前端目录
    os.chdir("frontend")
    
    # 创建服务并部署
    result = run_command("railway up", check=False)
    
    # 返回根目录
    os.chdir("..")
    
    return result

def get_deployment_urls():
    """获取部署URL"""
    print("6️⃣ 获取部署URL...")
    run_command("railway status")

def main():
    """主部署流程"""
    print("🚀 AI教育平台2.0 Railway自动部署")
    print("=" * 50)
    
    # 检查认证
    if not check_railway_auth():
        sys.exit(1)
    
    # 获取项目状态
    get_project_status()
    
    # 设置环境变量
    env_vars = setup_environment_variables()
    
    # 部署后端
    backend_result = deploy_backend()
    if backend_result and backend_result.returncode == 0:
        print("✅ 后端部署成功")
    else:
        print("⚠️ 后端部署需要检查")
    
    # 部署前端
    frontend_result = deploy_frontend()
    if frontend_result and frontend_result.returncode == 0:
        print("✅ 前端部署成功")
    else:
        print("⚠️ 前端部署需要检查")
    
    # 获取部署URL
    get_deployment_urls()
    
    print("\n🎉 部署完成！")
    print("📝 请手动在Railway控制台配置以下环境变量：")
    print("   - OPENROUTER_API_KEY (OpenRouter Gemini 2.5 Flash Lite)")
    print("   - Firebase Auth配置")
    print("🌐 Railway控制台: https://railway.com/project/9ecbe5a8-9ed5-4c8d-b28f-65eb8dd9f74c")

if __name__ == "__main__":
    main()