#!/usr/bin/env python3
"""
AI教育平台2.0 部署修复脚本
解决Nixpacks构建失败问题
"""

import subprocess
import sys
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

def main():
    """主修复流程"""
    print("🔧 AI教育平台2.0 部署修复")
    print("=" * 40)
    
    # 1. 检查Railway状态
    print("1️⃣ 检查当前Railway状态...")
    run_command("railway status")
    
    # 2. 删除失败的部署
    print("2️⃣ 清理失败的部署...")
    run_command("railway down", check=False)
    
    # 3. 分别部署后端服务
    print("3️⃣ 部署后端服务...")
    os.chdir("backend")
    result = run_command("railway up --detach")
    os.chdir("..")
    
    if result and result.returncode == 0:
        print("✅ 后端服务部署成功")
    else:
        print("⚠️ 后端部署需要检查日志")
    
    # 4. 分别部署前端服务
    print("4️⃣ 部署前端服务...")
    os.chdir("frontend")
    result = run_command("railway up --detach")
    os.chdir("..")
    
    if result and result.returncode == 0:
        print("✅ 前端服务部署成功")
    else:
        print("⚠️ 前端部署需要检查日志")
    
    # 5. 检查最终状态
    print("5️⃣ 检查部署状态...")
    run_command("railway status")
    
    print("\n🎉 部署修复完成！")
    print("📝 如果仍有问题，请检查Railway控制台日志")
    print("🌐 Railway控制台: https://railway.com/project/9ecbe5a8-9ed5-4c8d-b28f-65eb8dd9f74c")

if __name__ == "__main__":
    main()