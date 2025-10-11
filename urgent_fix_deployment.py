#!/usr/bin/env python3
"""
紧急修复Railway部署失败问题
根据MCP检查结果解决部署错误
"""

import subprocess
import sys
import os
import time

def run_command(cmd, check=True):
    """执行命令并返回结果"""
    print(f"🔧 执行: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ 失败: {e}")
        if e.stderr:
            print(f"错误: {e.stderr}")
        return None

def main():
    """紧急修复部署"""
    print("🚨 AI教育平台2.0 紧急部署修复")
    print("=" * 50)
    
    # 1. 确认Railway状态
    print("1️⃣ 检查Railway连接...")
    result = run_command("railway whoami")
    if not result or result.returncode != 0:
        print("❌ Railway未登录，请先执行: railway login")
        return
    
    # 2. 删除失败的应用服务
    print("2️⃣ 清理失败的服务...")
    run_command("railway service", check=False)
    
    # 3. 重新链接并创建应用服务
    print("3️⃣ 重新创建应用服务...")
    
    # 回到根目录
    if os.path.basename(os.getcwd()) != "new_aicorrection":
        os.chdir("..")
    
    # 删除可能存在的服务链接
    run_command("railway unlink", check=False)
    
    # 重新链接项目
    run_command("railway link aiguru2")
    
    # 创建新的应用服务
    print("4️⃣ 创建后端应用服务...")
    os.chdir("backend")
    
    # 设置环境变量并部署
    env_vars = [
        "ENVIRONMENT=production",
        "DATABASE_URL=postgresql://postgres:sfraebGPmjkZtWpAsHqeHrxUrxuDSQFz@postgres.railway.internal:5432/railway",
        "REDIS_URL=redis://default:fXZjFSKZfAfkTiqBfomlFHzcddmZZLLv@redis.railway.internal:6379",
        "SECRET_KEY=aiguru2-production-secret-key-2024",
        "PORT=8000"
    ]
    
    for var in env_vars:
        run_command(f"railway variables set {var}")
    
    # 部署后端
    result = run_command("railway up --detach")
    if result and result.returncode == 0:
        print("✅ 后端服务部署成功")
    else:
        print("⚠️ 后端部署失败，检查日志")
        run_command("railway logs", check=False)
    
    # 5. 创建前端服务
    print("5️⃣ 创建前端应用服务...")
    os.chdir("../frontend")
    
    frontend_vars = [
        "NODE_ENV=production",
        "PORT=3000"
    ]
    
    for var in frontend_vars:
        run_command(f"railway variables set {var}")
    
    result = run_command("railway up --detach")
    if result and result.returncode == 0:
        print("✅ 前端服务部署成功")
    else:
        print("⚠️ 前端部署失败，检查日志")
    
    # 6. 最终状态检查
    print("6️⃣ 检查最终部署状态...")
    os.chdir("..")
    run_command("railway status")
    run_command("railway domain")
    
    print("\n🎉 紧急修复完成！")
    print("📝 请检查Railway控制台确认服务状态")
    print("🔑 记住配置关键环境变量：")
    print("   - OPENROUTER_API_KEY")
    print("   - FIREBASE_PROJECT_ID")
    print("   - FIREBASE_CLIENT_EMAIL")
    print("   - FIREBASE_PRIVATE_KEY")

if __name__ == "__main__":
    main()