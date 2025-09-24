#!/usr/bin/env python3
"""
系统健康检查脚本
检查系统各组件的健康状态
"""

import os
import sys
import json
import sqlite3
import requests
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Tuple
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self):
        self.checks = []
        self.results = {}
        
    def add_check(self, name: str, check_func, critical: bool = False):
        """添加健康检查项"""
        self.checks.append({
            'name': name,
            'func': check_func,
            'critical': critical
        })
    
    def check_database_connection(self) -> Tuple[bool, str]:
        """检查数据库连接"""
        try:
            if not os.path.exists('class_system.db'):
                return False, "数据库文件不存在"
            
            conn = sqlite3.connect('class_system.db', timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            return True, "数据库连接正常"
        except Exception as e:
            return False, f"数据库连接失败: {e}"
    
    def check_database_integrity(self) -> Tuple[bool, str]:
        """检查数据库完整性"""
        try:
            conn = sqlite3.connect('class_system.db')
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            
            if result[0] == 'ok':
                return True, "数据库完整性检查通过"
            else:
                return False, f"数据库完整性检查失败: {result[0]}"
        except Exception as e:
            return False, f"数据库完整性检查错误: {e}"
    
    def check_required_tables(self) -> Tuple[bool, str]:
        """检查必需的数据库表"""
        required_tables = [
            'assignments', 'submissions', 'classes', 'class_members',
            'grading_tasks', 'audit_logs', 'notifications'
        ]
        
        try:
            conn = sqlite3.connect('class_system.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            missing_tables = set(required_tables) - set(existing_tables)
            if missing_tables:
                return False, f"缺少数据库表: {', '.join(missing_tables)}"
            else:
                return True, f"所有必需表存在 ({len(required_tables)}个)"
        except Exception as e:
            return False, f"检查数据库表失败: {e}"
    
    def check_file_system(self) -> Tuple[bool, str]:
        """检查文件系统"""
        required_dirs = ['uploads', 'logs', 'config', 'data']
        missing_dirs = []
        
        for dir_name in required_dirs:
            if not os.path.exists(dir_name):
                missing_dirs.append(dir_name)
        
        if missing_dirs:
            return False, f"缺少目录: {', '.join(missing_dirs)}"
        else:
            return True, f"所有必需目录存在 ({len(required_dirs)}个)"
    
    def check_disk_space(self) -> Tuple[bool, str]:
        """检查磁盘空间"""
        try:
            import shutil
            total, used, free = shutil.disk_usage('.')
            free_gb = free / (1024**3)
            used_percent = (used / total) * 100
            
            if free_gb < 1:  # 少于1GB
                return False, f"磁盘空间不足: 剩余 {free_gb:.1f}GB"
            elif used_percent > 90:  # 使用率超过90%
                return False, f"磁盘使用率过高: {used_percent:.1f}%"
            else:
                return True, f"磁盘空间充足: 剩余 {free_gb:.1f}GB ({100-used_percent:.1f}% 可用)"
        except Exception as e:
            return False, f"检查磁盘空间失败: {e}"
    
    def check_python_environment(self) -> Tuple[bool, str]:
        """检查Python环境"""
        try:
            import streamlit
            import sqlite3
            import pandas
            
            python_version = sys.version.split()[0]
            streamlit_version = streamlit.__version__
            
            return True, f"Python环境正常 (Python {python_version}, Streamlit {streamlit_version})"
        except ImportError as e:
            return False, f"Python环境缺少依赖: {e}"
        except Exception as e:
            return False, f"检查Python环境失败: {e}"
    
    def check_streamlit_process(self) -> Tuple[bool, str]:
        """检查Streamlit进程"""
        try:
            import psutil
            streamlit_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'streamlit' in proc.info['name'].lower() or \
                       any('streamlit' in arg.lower() for arg in proc.info['cmdline']):
                        streamlit_processes.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if streamlit_processes:
                return True, f"Streamlit进程运行中 (PID: {', '.join(map(str, streamlit_processes))})"
            else:
                return False, "Streamlit进程未运行"
        except ImportError:
            # 如果没有psutil，尝试其他方法
            try:
                result = subprocess.run(['pgrep', '-f', 'streamlit'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    return True, f"Streamlit进程运行中 (PID: {', '.join(pids)})"
                else:
                    return False, "Streamlit进程未运行"
            except Exception:
                return False, "无法检查Streamlit进程状态"
        except Exception as e:
            return False, f"检查Streamlit进程失败: {e}"
    
    def check_web_service(self) -> Tuple[bool, str]:
        """检查Web服务可访问性"""
        try:
            response = requests.get('http://localhost:8501', timeout=10)
            if response.status_code == 200:
                return True, "Web服务可访问 (HTTP 200)"
            else:
                return False, f"Web服务响应异常 (HTTP {response.status_code})"
        except requests.exceptions.ConnectionError:
            return False, "Web服务连接失败 (端口8501不可访问)"
        except requests.exceptions.Timeout:
            return False, "Web服务响应超时"
        except Exception as e:
            return False, f"检查Web服务失败: {e}"
    
    def check_config_files(self) -> Tuple[bool, str]:
        """检查配置文件"""
        config_files = ['.env', 'config/ai_optimization.yaml']
        missing_files = []
        
        for file_path in config_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            return False, f"缺少配置文件: {', '.join(missing_files)}"
        else:
            return True, f"配置文件完整 ({len(config_files)}个)"
    
    def check_log_files(self) -> Tuple[bool, str]:
        """检查日志文件"""
        try:
            log_dir = 'logs'
            if not os.path.exists(log_dir):
                return False, "日志目录不存在"
            
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
            if not log_files:
                return True, "日志目录存在但无日志文件"
            
            # 检查最新日志文件的修改时间
            latest_log = max([os.path.join(log_dir, f) for f in log_files], 
                           key=os.path.getmtime)
            mtime = os.path.getmtime(latest_log)
            age_hours = (datetime.now().timestamp() - mtime) / 3600
            
            if age_hours > 24:
                return False, f"最新日志文件过旧 ({age_hours:.1f}小时前)"
            else:
                return True, f"日志文件正常 ({len(log_files)}个文件)"
        except Exception as e:
            return False, f"检查日志文件失败: {e}"
    
    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        # 添加所有检查项
        self.add_check("数据库连接", self.check_database_connection, critical=True)
        self.add_check("数据库完整性", self.check_database_integrity, critical=True)
        self.add_check("数据库表结构", self.check_required_tables, critical=True)
        self.add_check("文件系统", self.check_file_system, critical=True)
        self.add_check("磁盘空间", self.check_disk_space, critical=False)
        self.add_check("Python环境", self.check_python_environment, critical=True)
        self.add_check("Streamlit进程", self.check_streamlit_process, critical=False)
        self.add_check("Web服务", self.check_web_service, critical=False)
        self.add_check("配置文件", self.check_config_files, critical=True)
        self.add_check("日志文件", self.check_log_files, critical=False)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {},
            'summary': {
                'total': len(self.checks),
                'passed': 0,
                'failed': 0,
                'critical_failed': 0
            }
        }
        
        logger.info("开始系统健康检查...")
        
        for check in self.checks:
            name = check['name']
            func = check['func']
            critical = check['critical']
            
            try:
                success, message = func()
                results['checks'][name] = {
                    'status': 'pass' if success else 'fail',
                    'message': message,
                    'critical': critical
                }
                
                if success:
                    results['summary']['passed'] += 1
                    logger.info(f"✓ {name}: {message}")
                else:
                    results['summary']['failed'] += 1
                    if critical:
                        results['summary']['critical_failed'] += 1
                        results['overall_status'] = 'critical'
                    elif results['overall_status'] == 'healthy':
                        results['overall_status'] = 'warning'
                    logger.error(f"✗ {name}: {message}")
                    
            except Exception as e:
                results['checks'][name] = {
                    'status': 'error',
                    'message': f"检查过程中发生错误: {e}",
                    'critical': critical
                }
                results['summary']['failed'] += 1
                if critical:
                    results['summary']['critical_failed'] += 1
                    results['overall_status'] = 'critical'
                logger.error(f"✗ {name}: 检查过程中发生错误: {e}")
        
        return results
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """生成健康检查报告"""
        report = []
        report.append("=" * 60)
        report.append("系统健康检查报告")
        report.append("=" * 60)
        report.append(f"检查时间: {results['timestamp']}")
        report.append(f"总体状态: {results['overall_status'].upper()}")
        report.append("")
        
        summary = results['summary']
        report.append(f"检查项目: {summary['total']} 个")
        report.append(f"通过: {summary['passed']} 个")
        report.append(f"失败: {summary['failed']} 个")
        report.append(f"关键失败: {summary['critical_failed']} 个")
        report.append("")
        
        report.append("详细结果:")
        report.append("-" * 40)
        
        for name, result in results['checks'].items():
            status_symbol = "✓" if result['status'] == 'pass' else "✗"
            critical_mark = " [关键]" if result['critical'] else ""
            report.append(f"{status_symbol} {name}{critical_mark}")
            report.append(f"  {result['message']}")
            report.append("")
        
        if results['overall_status'] == 'critical':
            report.append("⚠️  检测到关键问题，请立即处理！")
        elif results['overall_status'] == 'warning':
            report.append("⚠️  检测到一些问题，建议尽快处理。")
        else:
            report.append("✅ 系统运行正常。")
        
        report.append("=" * 60)
        
        return '\n'.join(report)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='系统健康检查工具')
    parser.add_argument('--json', action='store_true', help='输出JSON格式结果')
    parser.add_argument('--output', help='输出文件路径')
    parser.add_argument('--exit-code', action='store_true', help='根据检查结果设置退出码')
    
    args = parser.parse_args()
    
    checker = HealthChecker()
    results = checker.run_all_checks()
    
    if args.json:
        output = json.dumps(results, indent=2, ensure_ascii=False)
    else:
        output = checker.generate_report(results)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"结果已保存到: {args.output}")
    else:
        print(output)
    
    # 根据检查结果设置退出码
    if args.exit_code:
        if results['overall_status'] == 'critical':
            sys.exit(2)  # 关键错误
        elif results['overall_status'] == 'warning':
            sys.exit(1)  # 警告
        else:
            sys.exit(0)  # 正常

if __name__ == '__main__':
    main()