#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess
import platform
import webbrowser
import signal
import threading
from pathlib import Path

class SystemStarter:
    def __init__(self):
        self.system = platform.system()
        self.processes = []
        self.project_root = Path(__file__).parent
        self.logs_dir = self.project_root / "logs"
        
        # 创建日志目录
        self.logs_dir.mkdir(exist_ok=True)
        
    def log(self, message, level="INFO"):
        """记录日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)
        
        # 写入日志文件
        with open(self.logs_dir / "startup.log", "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
    
    def check_requirements(self):
        """检查环境要求"""
        self.log("检查系统环境...")
        
        # 检查Python版本
        if sys.version_info < (3, 8):
            self.log("Python版本过低，需要3.8+", "ERROR")
            return False
            
        # 检查必要文件
        required_files = ["main.py", "requirements.txt"]
        required_dirs = ["frontend", "functions"]
        
        for file in required_files:
            if not (self.project_root / file).exists():
                self.log(f"缺少必要文件: {file}", "ERROR")
                return False
                
        for dir in required_dirs:
            if not (self.project_root / dir).exists():
                self.log(f"缺少必要目录: {dir}", "ERROR")
                return False
        
        # 检查Node.js
        try:
            result = subprocess.run(["node", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.log("Node.js未安装或未添加到PATH", "ERROR")
                return False
            self.log(f"✓ Node.js版本: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.log("Node.js未安装或未添加到PATH", "ERROR")
            return False
            
        self.log("✓ 环境检查通过")
        return True
    
    def install_dependencies(self):
        """安装依赖"""
        self.log("安装Python依赖...")
        
        # 检查虚拟环境
        venv_paths = ["venv", ".venv"]
        venv_activated = False
        
        for venv in venv_paths:
            venv_path = self.project_root / venv
            if venv_path.exists():
                if self.system == "Windows":
                    activate_script = venv_path / "Scripts" / "activate.bat"
                else:
                    activate_script = venv_path / "bin" / "activate"
                
                if activate_script.exists():
                    self.log(f"✓ 找到虚拟环境: {venv}")
                    venv_activated = True
                    break
        
        if not venv_activated:
            self.log("未找到虚拟环境，使用系统Python", "WARNING")
        
        # 安装Python依赖
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                                  cwd=self.project_root, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                self.log(f"Python依赖安装失败: {result.stderr}", "ERROR")
                return False
            self.log("✓ Python依赖安装完成")
        except subprocess.TimeoutExpired:
            self.log("Python依赖安装超时", "ERROR")
            return False
        
        # 安装前端依赖
        self.log("安装前端依赖...")
        frontend_dir = self.project_root / "frontend"
        
        try:
            result = subprocess.run(["npm", "install"], 
                                  cwd=frontend_dir, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                self.log(f"前端依赖安装失败: {result.stderr}", "ERROR")
                return False
            self.log("✓ 前端依赖安装完成")
        except subprocess.TimeoutExpired:
            self.log("前端依赖安装超时", "ERROR")
            return False
            
        return True
    
    def start_backend(self):
        """启动后端服务"""
        self.log("启动后端服务...")
        
        try:
            if self.system == "Windows":
                process = subprocess.Popen([sys.executable, "main.py"],
                                         cwd=self.project_root,
                                         creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                process = subprocess.Popen([sys.executable, "main.py"],
                                         cwd=self.project_root)
            
            self.processes.append(("backend", process))
            self.log("✓ 后端服务启动中...")
            
            # 等待后端启动
            for i in range(20):  # 最多等待40秒
                try:
                    import requests
                    response = requests.get("http://localhost:8001/health", timeout=2)
                    if response.status_code == 200:
                        self.log("✓ 后端服务启动成功")
                        return True
                except:
                    pass
                
                self.log(f"等待后端服务启动... ({i+1}/20)")
                time.sleep(2)
            
            self.log("后端服务启动超时", "WARNING")
            return False
            
        except Exception as e:
            self.log(f"后端服务启动失败: {e}", "ERROR")
            return False
    
    def start_frontend(self):
        """启动前端服务"""
        self.log("启动前端服务...")
        
        frontend_dir = self.project_root / "frontend"
        
        try:
            if self.system == "Windows":
                process = subprocess.Popen(["npm", "run", "dev"],
                                         cwd=frontend_dir,
                                         creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                process = subprocess.Popen(["npm", "run", "dev"],
                                         cwd=frontend_dir)
            
            self.processes.append(("frontend", process))
            self.log("✓ 前端服务启动中...")
            
            # 等待前端启动
            time.sleep(10)  # 给前端更多启动时间
            
            for i in range(15):  # 最多等待30秒
                try:
                    import requests
                    response = requests.get("http://localhost:3000", timeout=2)
                    if response.status_code == 200:
                        self.log("✓ 前端服务启动成功")
                        return True
                except:
                    pass
                
                self.log(f"等待前端服务启动... ({i+1}/15)")
                time.sleep(2)
            
            self.log("前端服务可能仍在启动中", "WARNING")
            return True
            
        except Exception as e:
            self.log(f"前端服务启动失败: {e}", "ERROR")
            return False
    
    def open_browser(self):
        """打开浏览器"""
        self.log("正在打开浏览器...")
        time.sleep(3)
        try:
            webbrowser.open("http://localhost:3000")
            self.log("✓ 浏览器已打开")
        except Exception as e:
            self.log(f"无法自动打开浏览器: {e}", "WARNING")
            self.log("请手动访问: http://localhost:3000")
    
    def monitor_services(self):
        """监控服务状态"""
        self.log("开始监控服务状态...")
        
        while True:
            try:
                time.sleep(30)  # 每30秒检查一次
                
                # 检查后端
                try:
                    import requests
                    response = requests.get("http://localhost:8001/health", timeout=5)
                    if response.status_code == 200:
                        backend_status = "正常"
                    else:
                        backend_status = "异常"
                except:
                    backend_status = "异常"
                
                # 检查前端
                try:
                    import requests
                    response = requests.get("http://localhost:3000", timeout=5)
                    if response.status_code == 200:
                        frontend_status = "正常"
                    else:
                        frontend_status = "异常"
                except:
                    frontend_status = "异常"
                
                timestamp = time.strftime("%H:%M:%S")
                self.log(f"[{timestamp}] 服务状态 - 后端: {backend_status}, 前端: {frontend_status}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.log(f"监控服务时出错: {e}", "ERROR")
    
    def cleanup(self):
        """清理进程"""
        self.log("正在停止服务...")
        
        for name, process in self.processes:
            try:
                if process.poll() is None:  # 进程还在运行
                    self.log(f"停止{name}服务...")
                    process.terminate()
                    
                    # 等待进程结束
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self.log(f"强制停止{name}服务...")
                        process.kill()
                        
            except Exception as e:
                self.log(f"停止{name}服务时出错: {e}", "ERROR")
        
        self.log("✓ 所有服务已停止")
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        self.log("接收到停止信号，正在清理...")
        self.cleanup()
        sys.exit(0)
    
    def start(self):
        """启动系统"""
        # 注册信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        print("=" * 50)
        print("     AI智能批改系统 - 统一启动脚本")
        print("=" * 50)
        print()
        
        try:
            # 1. 检查环境
            if not self.check_requirements():
                self.log("环境检查失败，退出", "ERROR")
                return False
            
            # 2. 安装依赖
            if not self.install_dependencies():
                self.log("依赖安装失败，退出", "ERROR")
                return False
            
            # 3. 启动后端
            if not self.start_backend():
                self.log("后端启动失败", "ERROR")
                # 继续启动前端
            
            # 4. 启动前端
            if not self.start_frontend():
                self.log("前端启动失败", "ERROR")
                return False
            
            # 5. 打开浏览器
            browser_thread = threading.Thread(target=self.open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            # 6. 显示信息
            print()
            print("=" * 50)
            print("            启动完成！")
            print("=" * 50)
            print()
            print("🚀 服务访问地址:")
            print("   前端界面: http://localhost:3000")
            print("   后端API:  http://localhost:8001")
            print("   API文档:  http://localhost:8001/docs")
            print()
            print("🔐 测试账户:")
            print("   用户名: testuser")
            print("   密码:   123456")
            print()
            print("📝 操作说明:")
            print("   1. 前端页面会自动打开")
            print("   2. 使用测试账户登录")
            print("   3. 上传文件进行AI批改")
            print("   4. 查看历史记录和详情")
            print()
            print("⚠️  注意事项:")
            print("   - 按Ctrl+C停止所有服务")
            print("   - 日志保存在logs/startup.log")
            print("   - 如遇问题请查看日志文件")
            print()
            
            # 7. 监控服务
            self.monitor_services()
            
        except KeyboardInterrupt:
            self.log("用户中断，正在停止服务...")
        except Exception as e:
            self.log(f"启动过程中出错: {e}", "ERROR")
        finally:
            self.cleanup()

if __name__ == "__main__":
    starter = SystemStarter()
    starter.start() 