#!/usr/bin/env python3
"""
生产模式启动脚本 - 禁用热重载，避免频繁重启
"""

import uvicorn
import logging
import os
from pathlib import Path

def setup_production_logging():
    """设置生产环境日志"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "production.log"),
            logging.StreamHandler()
        ]
    )

def main():
    """主启动函数"""
    print("🚀 启动AI智能批改系统 - 生产模式")
    print("📝 特点：稳定运行，不会因文件变化而重启")
    
    # 设置日志
    setup_production_logging()
    
    # 确保必要目录存在
    for dir_name in ["uploads", "logs", "user_data"]:
        Path(dir_name).mkdir(exist_ok=True)
    
    print("✅ 目录结构已准备")
    print("🌐 启动服务器...")
    print("📊 访问地址：")
    print("   - 前端应用: http://localhost:3000")
    print("   - 后端API:  http://localhost:8000")
    print("   - API文档:  http://localhost:8000/docs")
    print()
    print("⚠️  注意：生产模式下代码修改不会自动重启")
    print("🛑 停止服务：按 Ctrl+C")
    print()
    
    try:
        # 启动服务器 - 生产模式配置
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # 禁用热重载
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")
        logging.error(f"服务启动失败: {e}", exc_info=True)

if __name__ == "__main__":
    main() 