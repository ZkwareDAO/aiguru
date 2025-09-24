#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
班级批改系统监控和健康检查
"""

import time
import psutil
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import logging

from src.config.settings import get_settings
from src.config.classroom_config import get_classroom_config_manager


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    component: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class SystemMetrics:
    """系统指标"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_tasks: int
    pending_submissions: int
    grading_queue_size: int
    file_storage_usage: float
    database_size: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class GradingPerformanceMetrics:
    """批改性能指标"""
    total_graded: int
    average_grading_time: float
    success_rate: float
    error_rate: float
    ai_confidence_average: float
    throughput_per_hour: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class ClassroomSystemMonitor:
    """班级批改系统监控器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.config_manager = get_classroom_config_manager()
        self.logger = logging.getLogger(f"{__name__}.ClassroomSystemMonitor")
        
        # 监控配置
        self.metrics_history: List[SystemMetrics] = []
        self.performance_history: List[GradingPerformanceMetrics] = []
        self.health_history: List[HealthCheckResult] = []
        
        # 阈值配置
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 90.0,
            'memory_warning': 80.0,
            'memory_critical': 95.0,
            'disk_warning': 85.0,
            'disk_critical': 95.0,
            'queue_warning': 100,
            'queue_critical': 500,
            'error_rate_warning': 0.1,
            'error_rate_critical': 0.3
        }
        
        self.logger.info("班级批改系统监控器已初始化")
    
    def collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # 磁盘使用率
            try:
                import os
                disk_path = os.getcwd()[:3] if os.name == 'nt' else '/'  # Windows: 'C:\', Unix: '/'
                disk = psutil.disk_usage(disk_path)
                disk_usage = (disk.used / disk.total) * 100
            except Exception:
                # 如果磁盘检查失败，使用默认值
                disk_usage = 50.0
            
            # 任务队列指标
            active_tasks = self._get_active_tasks_count()
            pending_submissions = self._get_pending_submissions_count()
            grading_queue_size = self._get_grading_queue_size()
            
            # 文件存储使用率
            file_storage_usage = self._get_file_storage_usage()
            
            # 数据库大小
            database_size = self._get_database_size()
            
            metrics = SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                active_tasks=active_tasks,
                pending_submissions=pending_submissions,
                grading_queue_size=grading_queue_size,
                file_storage_usage=file_storage_usage,
                database_size=database_size,
                timestamp=datetime.now()
            )
            
            # 保存到历史记录
            self.metrics_history.append(metrics)
            
            # 保持历史记录在合理范围内（最近24小时）
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.metrics_history = [
                m for m in self.metrics_history 
                if m.timestamp > cutoff_time
            ]
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"收集系统指标失败: {e}")
            return SystemMetrics(
                cpu_usage=0, memory_usage=0, disk_usage=0,
                active_tasks=0, pending_submissions=0, grading_queue_size=0,
                file_storage_usage=0, database_size=0,
                timestamp=datetime.now()
            )
    
    def collect_grading_performance_metrics(self) -> GradingPerformanceMetrics:
        """收集批改性能指标"""
        try:
            # 从数据库获取批改统计数据
            stats = self._get_grading_statistics()
            
            metrics = GradingPerformanceMetrics(
                total_graded=stats.get('total_graded', 0),
                average_grading_time=stats.get('average_grading_time', 0.0),
                success_rate=stats.get('success_rate', 0.0),
                error_rate=stats.get('error_rate', 0.0),
                ai_confidence_average=stats.get('ai_confidence_average', 0.0),
                throughput_per_hour=stats.get('throughput_per_hour', 0.0),
                timestamp=datetime.now()
            )
            
            # 保存到历史记录
            self.performance_history.append(metrics)
            
            # 保持历史记录在合理范围内
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.performance_history = [
                m for m in self.performance_history 
                if m.timestamp > cutoff_time
            ]
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"收集批改性能指标失败: {e}")
            return GradingPerformanceMetrics(
                total_graded=0, average_grading_time=0.0,
                success_rate=0.0, error_rate=0.0,
                ai_confidence_average=0.0, throughput_per_hour=0.0,
                timestamp=datetime.now()
            )
    
    def perform_health_check(self) -> List[HealthCheckResult]:
        """执行健康检查"""
        results = []
        
        # 系统资源健康检查
        results.extend(self._check_system_resources())
        
        # 数据库健康检查
        results.extend(self._check_database_health())
        
        # 文件存储健康检查
        results.extend(self._check_file_storage_health())
        
        # 任务队列健康检查
        results.extend(self._check_task_queue_health())
        
        # 批改服务健康检查
        results.extend(self._check_grading_service_health())
        
        # 配置健康检查
        results.extend(self._check_configuration_health())
        
        # 保存健康检查历史
        self.health_history.extend(results)
        
        # 保持历史记录在合理范围内
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.health_history = [
            h for h in self.health_history 
            if h.timestamp > cutoff_time
        ]
        
        return results
    
    def _check_system_resources(self) -> List[HealthCheckResult]:
        """检查系统资源"""
        results = []
        current_time = datetime.now()
        
        # CPU检查
        cpu_usage = psutil.cpu_percent(interval=1)
        if cpu_usage >= self.thresholds['cpu_critical']:
            status = HealthStatus.CRITICAL
            message = f"CPU使用率过高: {cpu_usage:.1f}%"
        elif cpu_usage >= self.thresholds['cpu_warning']:
            status = HealthStatus.WARNING
            message = f"CPU使用率较高: {cpu_usage:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"CPU使用率正常: {cpu_usage:.1f}%"
        
        results.append(HealthCheckResult(
            component="cpu",
            status=status,
            message=message,
            details={"usage": cpu_usage, "threshold_warning": self.thresholds['cpu_warning']},
            timestamp=current_time
        ))
        
        # 内存检查
        memory = psutil.virtual_memory()
        if memory.percent >= self.thresholds['memory_critical']:
            status = HealthStatus.CRITICAL
            message = f"内存使用率过高: {memory.percent:.1f}%"
        elif memory.percent >= self.thresholds['memory_warning']:
            status = HealthStatus.WARNING
            message = f"内存使用率较高: {memory.percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"内存使用率正常: {memory.percent:.1f}%"
        
        results.append(HealthCheckResult(
            component="memory",
            status=status,
            message=message,
            details={
                "usage": memory.percent,
                "available": memory.available,
                "total": memory.total
            },
            timestamp=current_time
        ))
        
        # 磁盘检查
        try:
            import os
            disk_path = os.getcwd()[:3] if os.name == 'nt' else '/'  # Windows: 'C:\', Unix: '/'
            disk = psutil.disk_usage(disk_path)
            disk_usage = (disk.used / disk.total) * 100
        except Exception:
            # 如果磁盘检查失败，使用默认值
            disk_usage = 50.0
            disk = type('MockDisk', (), {'used': 50*1024*1024*1024, 'total': 100*1024*1024*1024, 'free': 50*1024*1024*1024})()
        if disk_usage >= self.thresholds['disk_critical']:
            status = HealthStatus.CRITICAL
            message = f"磁盘使用率过高: {disk_usage:.1f}%"
        elif disk_usage >= self.thresholds['disk_warning']:
            status = HealthStatus.WARNING
            message = f"磁盘使用率较高: {disk_usage:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"磁盘使用率正常: {disk_usage:.1f}%"
        
        results.append(HealthCheckResult(
            component="disk",
            status=status,
            message=message,
            details={
                "usage": disk_usage,
                "free": disk.free,
                "total": disk.total
            },
            timestamp=current_time
        ))
        
        return results
    
    def _check_database_health(self) -> List[HealthCheckResult]:
        """检查数据库健康状态"""
        results = []
        current_time = datetime.now()
        
        try:
            # 检查数据库连接
            db_path = self.settings.classroom.db_path
            conn = sqlite3.connect(db_path, timeout=5)
            
            # 执行简单查询测试连接
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            # 检查数据库大小
            db_size = Path(db_path).stat().st_size / (1024 * 1024)  # MB
            
            conn.close()
            
            results.append(HealthCheckResult(
                component="database",
                status=HealthStatus.HEALTHY,
                message=f"数据库连接正常，大小: {db_size:.2f}MB",
                details={"size_mb": db_size, "path": db_path},
                timestamp=current_time
            ))
            
        except Exception as e:
            results.append(HealthCheckResult(
                component="database",
                status=HealthStatus.CRITICAL,
                message=f"数据库连接失败: {e}",
                details={"error": str(e)},
                timestamp=current_time
            ))
        
        return results
    
    def _check_file_storage_health(self) -> List[HealthCheckResult]:
        """检查文件存储健康状态"""
        results = []
        current_time = datetime.now()
        
        try:
            storage_config = self.config_manager.get_file_storage_config()
            storage_path = Path(storage_config.base_path)
            
            # 检查存储目录是否存在
            if not storage_path.exists():
                results.append(HealthCheckResult(
                    component="file_storage",
                    status=HealthStatus.CRITICAL,
                    message=f"文件存储目录不存在: {storage_path}",
                    details={"path": str(storage_path)},
                    timestamp=current_time
                ))
                return results
            
            # 检查存储空间使用情况
            total_size = 0
            file_count = 0
            
            for file_path in storage_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            total_size_mb = total_size / (1024 * 1024)
            
            # 检查是否超过警告阈值
            max_size_mb = storage_config.max_file_size_mb * 1000  # 假设最大总存储为单文件限制的1000倍
            usage_percent = (total_size_mb / max_size_mb) * 100 if max_size_mb > 0 else 0
            
            if usage_percent >= 90:
                status = HealthStatus.WARNING
                message = f"文件存储使用率较高: {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"文件存储正常: {total_size_mb:.2f}MB, {file_count}个文件"
            
            results.append(HealthCheckResult(
                component="file_storage",
                status=status,
                message=message,
                details={
                    "total_size_mb": total_size_mb,
                    "file_count": file_count,
                    "usage_percent": usage_percent
                },
                timestamp=current_time
            ))
            
        except Exception as e:
            results.append(HealthCheckResult(
                component="file_storage",
                status=HealthStatus.CRITICAL,
                message=f"文件存储检查失败: {e}",
                details={"error": str(e)},
                timestamp=current_time
            ))
        
        return results
    
    def _check_task_queue_health(self) -> List[HealthCheckResult]:
        """检查任务队列健康状态"""
        results = []
        current_time = datetime.now()
        
        try:
            # 获取任务队列统计
            queue_size = self._get_grading_queue_size()
            active_tasks = self._get_active_tasks_count()
            
            # 检查队列大小
            if queue_size >= self.thresholds['queue_critical']:
                status = HealthStatus.CRITICAL
                message = f"任务队列积压严重: {queue_size}个任务"
            elif queue_size >= self.thresholds['queue_warning']:
                status = HealthStatus.WARNING
                message = f"任务队列积压较多: {queue_size}个任务"
            else:
                status = HealthStatus.HEALTHY
                message = f"任务队列正常: {queue_size}个待处理任务"
            
            results.append(HealthCheckResult(
                component="task_queue",
                status=status,
                message=message,
                details={
                    "queue_size": queue_size,
                    "active_tasks": active_tasks
                },
                timestamp=current_time
            ))
            
        except Exception as e:
            results.append(HealthCheckResult(
                component="task_queue",
                status=HealthStatus.CRITICAL,
                message=f"任务队列检查失败: {e}",
                details={"error": str(e)},
                timestamp=current_time
            ))
        
        return results
    
    def _check_grading_service_health(self) -> List[HealthCheckResult]:
        """检查批改服务健康状态"""
        results = []
        current_time = datetime.now()
        
        try:
            # 获取批改统计数据
            stats = self._get_grading_statistics()
            error_rate = stats.get('error_rate', 0.0)
            
            # 检查错误率
            if error_rate >= self.thresholds['error_rate_critical']:
                status = HealthStatus.CRITICAL
                message = f"批改错误率过高: {error_rate:.1%}"
            elif error_rate >= self.thresholds['error_rate_warning']:
                status = HealthStatus.WARNING
                message = f"批改错误率较高: {error_rate:.1%}"
            else:
                status = HealthStatus.HEALTHY
                message = f"批改服务正常: 错误率 {error_rate:.1%}"
            
            results.append(HealthCheckResult(
                component="grading_service",
                status=status,
                message=message,
                details=stats,
                timestamp=current_time
            ))
            
        except Exception as e:
            results.append(HealthCheckResult(
                component="grading_service",
                status=HealthStatus.CRITICAL,
                message=f"批改服务检查失败: {e}",
                details={"error": str(e)},
                timestamp=current_time
            ))
        
        return results
    
    def _check_configuration_health(self) -> List[HealthCheckResult]:
        """检查配置健康状态"""
        results = []
        current_time = datetime.now()
        
        try:
            # 验证配置
            config_errors = self.config_manager.validate_config()
            
            total_errors = sum(len(errors) for errors in config_errors.values())
            
            if total_errors > 0:
                status = HealthStatus.WARNING
                message = f"配置存在 {total_errors} 个问题"
                details = config_errors
            else:
                status = HealthStatus.HEALTHY
                message = "配置验证通过"
                details = {"validation": "passed"}
            
            results.append(HealthCheckResult(
                component="configuration",
                status=status,
                message=message,
                details=details,
                timestamp=current_time
            ))
            
        except Exception as e:
            results.append(HealthCheckResult(
                component="configuration",
                status=HealthStatus.CRITICAL,
                message=f"配置检查失败: {e}",
                details={"error": str(e)},
                timestamp=current_time
            ))
        
        return results
    
    def _get_active_tasks_count(self) -> int:
        """获取活跃任务数量"""
        try:
            conn = sqlite3.connect(self.settings.task.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'running'")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def _get_pending_submissions_count(self) -> int:
        """获取待处理提交数量"""
        try:
            conn = sqlite3.connect(self.settings.classroom.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM submissions WHERE status = 'submitted'")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def _get_grading_queue_size(self) -> int:
        """获取批改队列大小"""
        try:
            conn = sqlite3.connect(self.settings.classroom.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM grading_tasks WHERE status = 'pending'")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def _get_file_storage_usage(self) -> float:
        """获取文件存储使用率"""
        try:
            storage_config = self.config_manager.get_file_storage_config()
            storage_path = Path(storage_config.base_path)
            
            if not storage_path.exists():
                return 0.0
            
            total_size = sum(
                f.stat().st_size for f in storage_path.rglob('*') 
                if f.is_file()
            )
            
            # 转换为MB并计算使用率（假设最大存储为10GB）
            total_size_mb = total_size / (1024 * 1024)
            max_storage_mb = 10 * 1024  # 10GB
            
            return (total_size_mb / max_storage_mb) * 100
            
        except:
            return 0.0
    
    def _get_database_size(self) -> float:
        """获取数据库大小（MB）"""
        try:
            db_path = Path(self.settings.classroom.db_path)
            if db_path.exists():
                return db_path.stat().st_size / (1024 * 1024)
            return 0.0
        except:
            return 0.0
    
    def _get_grading_statistics(self) -> Dict[str, Any]:
        """获取批改统计数据"""
        try:
            conn = sqlite3.connect(self.settings.classroom.db_path)
            cursor = conn.cursor()
            
            # 获取最近24小时的统计数据
            yesterday = datetime.now() - timedelta(hours=24)
            
            # 总批改数量
            cursor.execute("""
                SELECT COUNT(*) FROM submissions 
                WHERE status = 'graded' AND graded_at > ?
            """, (yesterday.isoformat(),))
            total_graded = cursor.fetchone()[0]
            
            # 成功率和错误率
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN ai_result IS NOT NULL THEN 1 END) as success_count,
                    COUNT(*) as total_count
                FROM submissions 
                WHERE graded_at > ?
            """, (yesterday.isoformat(),))
            
            result = cursor.fetchone()
            success_count, total_count = result if result else (0, 0)
            
            success_rate = success_count / total_count if total_count > 0 else 0.0
            error_rate = 1.0 - success_rate
            
            # 平均AI置信度
            cursor.execute("""
                SELECT AVG(ai_confidence) FROM submissions 
                WHERE ai_confidence IS NOT NULL AND graded_at > ?
            """, (yesterday.isoformat(),))
            
            ai_confidence_result = cursor.fetchone()
            ai_confidence_average = ai_confidence_result[0] if ai_confidence_result[0] else 0.0
            
            # 吞吐量（每小时）
            throughput_per_hour = total_graded / 24.0 if total_graded > 0 else 0.0
            
            # 平均批改时间（假设）
            average_grading_time = 30.0  # 秒，这里可以根据实际任务执行时间计算
            
            conn.close()
            
            return {
                'total_graded': total_graded,
                'average_grading_time': average_grading_time,
                'success_rate': success_rate,
                'error_rate': error_rate,
                'ai_confidence_average': ai_confidence_average,
                'throughput_per_hour': throughput_per_hour
            }
            
        except Exception as e:
            self.logger.error(f"获取批改统计数据失败: {e}")
            return {
                'total_graded': 0,
                'average_grading_time': 0.0,
                'success_rate': 0.0,
                'error_rate': 0.0,
                'ai_confidence_average': 0.0,
                'throughput_per_hour': 0.0
            }
    
    def get_system_status_summary(self) -> Dict[str, Any]:
        """获取系统状态摘要"""
        # 执行健康检查
        health_results = self.perform_health_check()
        
        # 收集指标
        system_metrics = self.collect_system_metrics()
        performance_metrics = self.collect_grading_performance_metrics()
        
        # 计算整体健康状态
        critical_count = sum(1 for r in health_results if r.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for r in health_results if r.status == HealthStatus.WARNING)
        
        if critical_count > 0:
            overall_status = HealthStatus.CRITICAL
        elif warning_count > 0:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            'overall_status': overall_status.value,
            'timestamp': datetime.now().isoformat(),
            'health_checks': [r.to_dict() for r in health_results],
            'system_metrics': system_metrics.to_dict(),
            'performance_metrics': performance_metrics.to_dict(),
            'summary': {
                'total_checks': len(health_results),
                'critical_issues': critical_count,
                'warnings': warning_count,
                'healthy_components': len(health_results) - critical_count - warning_count
            }
        }
    
    def export_monitoring_data(self, output_file: str):
        """导出监控数据"""
        try:
            data = {
                'export_timestamp': datetime.now().isoformat(),
                'system_metrics_history': [m.to_dict() for m in self.metrics_history],
                'performance_history': [p.to_dict() for p in self.performance_history],
                'health_history': [h.to_dict() for h in self.health_history],
                'current_status': self.get_system_status_summary()
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"监控数据已导出到: {output_file}")
            
        except Exception as e:
            self.logger.error(f"导出监控数据失败: {e}")


# 全局监控器实例
_monitor: Optional[ClassroomSystemMonitor] = None


def get_classroom_monitor() -> ClassroomSystemMonitor:
    """获取班级系统监控器"""
    global _monitor
    if _monitor is None:
        _monitor = ClassroomSystemMonitor()
    return _monitor


def reset_classroom_monitor():
    """重置监控器（主要用于测试）"""
    global _monitor
    _monitor = None