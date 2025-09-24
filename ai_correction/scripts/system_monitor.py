#!/usr/bin/env python3
"""
班级作业批改系统监控脚本
监控系统资源使用情况、应用状态和性能指标
"""

import os
import sys
import time
import json
import sqlite3
import psutil
import logging
import argparse
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """系统指标数据类"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_percent: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    load_average: List[float]

@dataclass
class ApplicationMetrics:
    """应用指标数据类"""
    timestamp: str
    active_users: int
    total_assignments: int
    total_submissions: int
    pending_grading_tasks: int
    processing_grading_tasks: int
    completed_grading_tasks: int
    failed_grading_tasks: int
    database_size_mb: float
    upload_files_count: int
    upload_files_size_mb: float

@dataclass
class AlertRule:
    """告警规则数据类"""
    name: str
    metric: str
    operator: str  # '>', '<', '>=', '<=', '=='
    threshold: float
    duration: int  # 持续时间（秒）
    severity: str  # 'info', 'warning', 'error', 'critical'
    message: str

class SystemMonitor:
    def __init__(self, config_file: str = 'config/monitoring.json'):
        self.config_file = config_file
        self.config = self.load_config()
        self.alert_states = {}  # 存储告警状态
        self.metrics_history = []  # 存储历史指标
        self.max_history_size = 1000
        
        # 确保日志目录存在
        os.makedirs('logs', exist_ok=True)
    
    def load_config(self) -> Dict[str, Any]:
        """加载监控配置"""
        default_config = {
            "monitoring": {
                "interval": 60,  # 监控间隔（秒）
                "history_retention": 24,  # 历史数据保留时间（小时）
                "enable_alerts": True,
                "enable_email_alerts": False
            },
            "database": {
                "path": "class_system.db"
            },
            "email": {
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_email": "monitor@example.com",
                "to_emails": ["admin@example.com"]
            },
            "alert_rules": [
                {
                    "name": "high_cpu",
                    "metric": "cpu_percent",
                    "operator": ">",
                    "threshold": 80.0,
                    "duration": 300,
                    "severity": "warning",
                    "message": "CPU使用率过高: {value}%"
                },
                {
                    "name": "high_memory",
                    "metric": "memory_percent",
                    "operator": ">",
                    "threshold": 85.0,
                    "duration": 300,
                    "severity": "warning",
                    "message": "内存使用率过高: {value}%"
                },
                {
                    "name": "low_disk_space",
                    "metric": "disk_percent",
                    "operator": ">",
                    "threshold": 90.0,
                    "duration": 60,
                    "severity": "error",
                    "message": "磁盘空间不足: {value}%"
                },
                {
                    "name": "high_grading_queue",
                    "metric": "pending_grading_tasks",
                    "operator": ">",
                    "threshold": 100,
                    "duration": 600,
                    "severity": "warning",
                    "message": "批改任务队列积压: {value}个任务"
                }
            ]
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                return default_config
        else:
            # 创建默认配置文件
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            logger.info(f"创建默认配置文件: {self.config_file}")
            return default_config
    
    def collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / 1024 / 1024
            
            # 磁盘使用情况
            disk = psutil.disk_usage('.')
            disk_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / 1024 / 1024 / 1024
            
            # 网络使用情况
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
            
            # 进程数量
            process_count = len(psutil.pids())
            
            # 系统负载
            try:
                load_average = list(os.getloadavg())
            except (OSError, AttributeError):
                # Windows系统不支持getloadavg
                load_average = [0.0, 0.0, 0.0]
            
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_mb=memory_available_mb,
                disk_percent=disk_percent,
                disk_free_gb=disk_free_gb,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv,
                process_count=process_count,
                load_average=load_average
            )
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            return None
    
    def collect_application_metrics(self) -> ApplicationMetrics:
        """收集应用指标"""
        try:
            db_path = self.config['database']['path']
            
            if not os.path.exists(db_path):
                logger.warning(f"数据库文件不存在: {db_path}")
                return None
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 统计作业数量
            cursor.execute("SELECT COUNT(*) FROM assignments WHERE is_active = 1")
            total_assignments = cursor.fetchone()[0]
            
            # 统计提交数量
            cursor.execute("SELECT COUNT(*) FROM submissions")
            total_submissions = cursor.fetchone()[0]
            
            # 统计批改任务
            pending_tasks = 0
            processing_tasks = 0
            completed_tasks = 0
            failed_tasks = 0
            
            # 检查批改任务表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='grading_tasks'")
            if cursor.fetchone():
                cursor.execute("SELECT status, COUNT(*) FROM grading_tasks GROUP BY status")
                task_stats = cursor.fetchall()
                
                for status, count in task_stats:
                    if status == 'pending':
                        pending_tasks = count
                    elif status == 'processing':
                        processing_tasks = count
                    elif status == 'completed':
                        completed_tasks = count
                    elif status == 'failed':
                        failed_tasks = count
            
            # 数据库大小
            database_size_mb = os.path.getsize(db_path) / 1024 / 1024
            
            conn.close()
            
            # 统计上传文件
            upload_files_count = 0
            upload_files_size_mb = 0
            
            if os.path.exists('uploads'):
                for root, dirs, files in os.walk('uploads'):
                    upload_files_count += len(files)
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            upload_files_size_mb += os.path.getsize(file_path) / 1024 / 1024
                        except OSError:
                            pass
            
            # 活跃用户数（简化实现，实际应该从会话或日志中统计）
            active_users = 0
            
            return ApplicationMetrics(
                timestamp=datetime.now().isoformat(),
                active_users=active_users,
                total_assignments=total_assignments,
                total_submissions=total_submissions,
                pending_grading_tasks=pending_tasks,
                processing_grading_tasks=processing_tasks,
                completed_grading_tasks=completed_tasks,
                failed_grading_tasks=failed_tasks,
                database_size_mb=database_size_mb,
                upload_files_count=upload_files_count,
                upload_files_size_mb=upload_files_size_mb
            )
        except Exception as e:
            logger.error(f"收集应用指标失败: {e}")
            return None
    
    def check_streamlit_process(self) -> Dict[str, Any]:
        """检查Streamlit进程状态"""
        try:
            streamlit_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
                try:
                    if 'streamlit' in proc.info['name'].lower() or \
                       any('streamlit' in arg.lower() for arg in proc.info['cmdline']):
                        streamlit_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': ' '.join(proc.info['cmdline']),
                            'cpu_percent': proc.info['cpu_percent'],
                            'memory_percent': proc.info['memory_percent']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            return {
                'running': len(streamlit_processes) > 0,
                'process_count': len(streamlit_processes),
                'processes': streamlit_processes
            }
        except Exception as e:
            logger.error(f"检查Streamlit进程失败: {e}")
            return {'running': False, 'process_count': 0, 'processes': []}
    
    def evaluate_alert_rules(self, system_metrics: SystemMetrics, 
                           app_metrics: ApplicationMetrics) -> List[Dict[str, Any]]:
        """评估告警规则"""
        if not self.config['monitoring']['enable_alerts']:
            return []
        
        alerts = []
        current_time = datetime.now()
        
        # 合并指标数据
        all_metrics = {}
        if system_metrics:
            all_metrics.update(asdict(system_metrics))
        if app_metrics:
            all_metrics.update(asdict(app_metrics))
        
        for rule_config in self.config['alert_rules']:
            rule = AlertRule(**rule_config)
            
            if rule.metric not in all_metrics:
                continue
            
            current_value = all_metrics[rule.metric]
            
            # 评估条件
            condition_met = False
            if rule.operator == '>':
                condition_met = current_value > rule.threshold
            elif rule.operator == '<':
                condition_met = current_value < rule.threshold
            elif rule.operator == '>=':
                condition_met = current_value >= rule.threshold
            elif rule.operator == '<=':
                condition_met = current_value <= rule.threshold
            elif rule.operator == '==':
                condition_met = current_value == rule.threshold
            
            # 管理告警状态
            if rule.name not in self.alert_states:
                self.alert_states[rule.name] = {
                    'active': False,
                    'start_time': None,
                    'last_alert_time': None
                }
            
            alert_state = self.alert_states[rule.name]
            
            if condition_met:
                if not alert_state['active']:
                    # 开始新的告警状态
                    alert_state['active'] = True
                    alert_state['start_time'] = current_time
                else:
                    # 检查是否达到持续时间
                    duration = (current_time - alert_state['start_time']).total_seconds()
                    if duration >= rule.duration:
                        # 检查是否需要发送告警（避免重复发送）
                        if (alert_state['last_alert_time'] is None or 
                            (current_time - alert_state['last_alert_time']).total_seconds() >= 3600):  # 1小时内不重复
                            
                            alert = {
                                'rule_name': rule.name,
                                'severity': rule.severity,
                                'message': rule.message.format(value=current_value),
                                'metric': rule.metric,
                                'current_value': current_value,
                                'threshold': rule.threshold,
                                'duration': duration,
                                'timestamp': current_time.isoformat()
                            }
                            alerts.append(alert)
                            alert_state['last_alert_time'] = current_time
            else:
                if alert_state['active']:
                    # 条件不再满足，重置告警状态
                    alert_state['active'] = False
                    alert_state['start_time'] = None
        
        return alerts
    
    def send_email_alert(self, alerts: List[Dict[str, Any]]):
        """发送邮件告警"""
        if not self.config['monitoring']['enable_email_alerts'] or not alerts:
            return
        
        try:
            email_config = self.config['email']
            
            # 创建邮件内容
            subject = f"[系统告警] 班级作业批改系统 - {len(alerts)}个告警"
            
            body = "系统监控检测到以下告警:\n\n"
            for alert in alerts:
                body += f"告警: {alert['rule_name']}\n"
                body += f"级别: {alert['severity']}\n"
                body += f"消息: {alert['message']}\n"
                body += f"当前值: {alert['current_value']}\n"
                body += f"阈值: {alert['threshold']}\n"
                body += f"时间: {alert['timestamp']}\n"
                body += "-" * 50 + "\n"
            
            body += f"\n监控时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # 发送邮件
            msg = MimeMultipart()
            msg['From'] = email_config['from_email']
            msg['To'] = ', '.join(email_config['to_emails'])
            msg['Subject'] = subject
            
            msg.attach(MimeText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            
            for to_email in email_config['to_emails']:
                server.send_message(msg, to_addrs=[to_email])
            
            server.quit()
            logger.info(f"邮件告警已发送给: {email_config['to_emails']}")
            
        except Exception as e:
            logger.error(f"发送邮件告警失败: {e}")
    
    def save_metrics(self, system_metrics: SystemMetrics, app_metrics: ApplicationMetrics):
        """保存指标数据"""
        try:
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'system': asdict(system_metrics) if system_metrics else None,
                'application': asdict(app_metrics) if app_metrics else None
            }
            
            # 保存到历史记录
            self.metrics_history.append(metrics_data)
            
            # 限制历史记录大小
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]
            
            # 保存到文件
            metrics_file = f"logs/metrics_{datetime.now().strftime('%Y%m%d')}.json"
            with open(metrics_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(metrics_data, ensure_ascii=False) + '\n')
                
        except Exception as e:
            logger.error(f"保存指标数据失败: {e}")
    
    def generate_report(self) -> str:
        """生成监控报告"""
        try:
            if not self.metrics_history:
                return "暂无监控数据"
            
            latest_metrics = self.metrics_history[-1]
            system_data = latest_metrics.get('system', {})
            app_data = latest_metrics.get('application', {})
            
            report = []
            report.append("=" * 60)
            report.append("班级作业批改系统监控报告")
            report.append("=" * 60)
            report.append(f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("")
            
            # 系统指标
            if system_data:
                report.append("系统资源使用情况:")
                report.append("-" * 30)
                report.append(f"CPU使用率: {system_data.get('cpu_percent', 0):.1f}%")
                report.append(f"内存使用率: {system_data.get('memory_percent', 0):.1f}%")
                report.append(f"可用内存: {system_data.get('memory_available_mb', 0):.1f} MB")
                report.append(f"磁盘使用率: {system_data.get('disk_percent', 0):.1f}%")
                report.append(f"磁盘剩余空间: {system_data.get('disk_free_gb', 0):.1f} GB")
                report.append(f"进程数量: {system_data.get('process_count', 0)}")
                report.append("")
            
            # 应用指标
            if app_data:
                report.append("应用运行状况:")
                report.append("-" * 30)
                report.append(f"总作业数: {app_data.get('total_assignments', 0)}")
                report.append(f"总提交数: {app_data.get('total_submissions', 0)}")
                report.append(f"待批改任务: {app_data.get('pending_grading_tasks', 0)}")
                report.append(f"批改中任务: {app_data.get('processing_grading_tasks', 0)}")
                report.append(f"已完成任务: {app_data.get('completed_grading_tasks', 0)}")
                report.append(f"失败任务: {app_data.get('failed_grading_tasks', 0)}")
                report.append(f"数据库大小: {app_data.get('database_size_mb', 0):.1f} MB")
                report.append(f"上传文件数: {app_data.get('upload_files_count', 0)}")
                report.append(f"上传文件大小: {app_data.get('upload_files_size_mb', 0):.1f} MB")
                report.append("")
            
            # Streamlit进程状态
            streamlit_status = self.check_streamlit_process()
            report.append("应用进程状态:")
            report.append("-" * 30)
            if streamlit_status['running']:
                report.append(f"Streamlit状态: 运行中 ({streamlit_status['process_count']}个进程)")
                for proc in streamlit_status['processes']:
                    report.append(f"  PID: {proc['pid']}, CPU: {proc['cpu_percent']:.1f}%, 内存: {proc['memory_percent']:.1f}%")
            else:
                report.append("Streamlit状态: 未运行")
            report.append("")
            
            # 活跃告警
            active_alerts = [state for state in self.alert_states.values() if state['active']]
            if active_alerts:
                report.append(f"活跃告警: {len(active_alerts)}个")
                report.append("-" * 30)
                for rule_name, state in self.alert_states.items():
                    if state['active']:
                        duration = (datetime.now() - state['start_time']).total_seconds()
                        report.append(f"  {rule_name}: 持续 {duration:.0f} 秒")
            else:
                report.append("活跃告警: 无")
            
            report.append("=" * 60)
            
            return '\n'.join(report)
            
        except Exception as e:
            logger.error(f"生成监控报告失败: {e}")
            return f"生成报告失败: {e}"
    
    def run_once(self):
        """执行一次监控检查"""
        logger.info("开始监控检查...")
        
        # 收集指标
        system_metrics = self.collect_system_metrics()
        app_metrics = self.collect_application_metrics()
        
        if system_metrics:
            logger.info(f"系统指标 - CPU: {system_metrics.cpu_percent:.1f}%, "
                       f"内存: {system_metrics.memory_percent:.1f}%, "
                       f"磁盘: {system_metrics.disk_percent:.1f}%")
        
        if app_metrics:
            logger.info(f"应用指标 - 作业: {app_metrics.total_assignments}, "
                       f"提交: {app_metrics.total_submissions}, "
                       f"待批改: {app_metrics.pending_grading_tasks}")
        
        # 评估告警
        alerts = self.evaluate_alert_rules(system_metrics, app_metrics)
        if alerts:
            logger.warning(f"检测到 {len(alerts)} 个告警")
            for alert in alerts:
                logger.warning(f"告警: {alert['message']}")
            
            # 发送邮件告警
            self.send_email_alert(alerts)
        
        # 保存指标
        self.save_metrics(system_metrics, app_metrics)
        
        logger.info("监控检查完成")
    
    def run_continuous(self):
        """持续监控模式"""
        logger.info("启动持续监控模式...")
        interval = self.config['monitoring']['interval']
        
        try:
            while True:
                self.run_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("监控已停止")
        except Exception as e:
            logger.error(f"监控过程中发生错误: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='班级作业批改系统监控工具')
    parser.add_argument('--config', default='config/monitoring.json', help='配置文件路径')
    parser.add_argument('--once', action='store_true', help='执行一次监控检查')
    parser.add_argument('--report', action='store_true', help='生成监控报告')
    parser.add_argument('--daemon', action='store_true', help='后台运行模式')
    
    args = parser.parse_args()
    
    # 确保必要目录存在
    os.makedirs('logs', exist_ok=True)
    os.makedirs('config', exist_ok=True)
    
    monitor = SystemMonitor(args.config)
    
    if args.report:
        # 生成报告
        report = monitor.generate_report()
        print(report)
    elif args.once:
        # 执行一次检查
        monitor.run_once()
    elif args.daemon:
        # 后台运行模式
        import daemon
        with daemon.DaemonContext():
            monitor.run_continuous()
    else:
        # 前台持续监控
        monitor.run_continuous()

if __name__ == '__main__':
    main()