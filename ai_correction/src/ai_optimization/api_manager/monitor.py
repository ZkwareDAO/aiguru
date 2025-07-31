"""
API调用监控系统

实现API调用统计、性能指标收集、实时监控和告警功能。
"""

import asyncio
import time
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from enum import Enum
import threading
from pathlib import Path

from ..models.api_models import APIResponse, ModelConfig, UsageStats
from ..config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(Enum):
    """指标类型"""
    RESPONSE_TIME = "response_time"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    COST = "cost"
    THROUGHPUT = "throughput"
    QUALITY_SCORE = "quality_score"

@dataclass
class APICallRecord:
    """API调用记录"""
    request_id: str
    model_id: str
    timestamp: datetime
    response_time: float
    success: bool
    error_message: Optional[str] = None
    usage_stats: Optional[UsageStats] = None
    quality_score: Optional[float] = None
    cost: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "timestamp": self.timestamp.isoformat(),
            "response_time": self.response_time,
            "success": self.success,
            "error_message": self.error_message,
            "usage_stats": self.usage_stats.to_dict() if self.usage_stats else None,
            "quality_score": self.quality_score,
            "cost": self.cost
        }

@dataclass
class MetricSnapshot:
    """指标快照"""
    timestamp: datetime
    model_id: str
    metric_type: MetricType
    value: float
    additional_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Alert:
    """告警"""
    id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    model_id: Optional[str] = None
    metric_type: Optional[MetricType] = None
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "model_id": self.model_id,
            "metric_type": self.metric_type.value if self.metric_type else None,
            "threshold_value": self.threshold_value,
            "actual_value": self.actual_value,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }

@dataclass
class MonitoringConfig:
    """监控配置"""
    # 数据保留设置
    max_records: int = 10000
    max_snapshots: int = 1000
    max_alerts: int = 500
    
    # 指标计算窗口
    metrics_window_minutes: int = 5
    
    # 告警阈值
    response_time_threshold: float = 30.0  # 秒
    error_rate_threshold: float = 0.1  # 10%
    cost_threshold_per_hour: float = 10.0  # 美元
    
    # 监控间隔
    monitoring_interval: int = 60  # 秒
    
    # 数据持久化
    enable_persistence: bool = True
    persistence_file: str = "logs/api_monitoring.json"

class APIMonitor:
    """API调用监控器"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.config = self._load_monitoring_config()
        
        # 数据存储
        self.call_records: deque = deque(maxlen=self.config.max_records)
        self.metric_snapshots: deque = deque(maxlen=self.config.max_snapshots)
        self.alerts: deque = deque(maxlen=self.config.max_alerts)
        
        # 实时统计
        self.model_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_response_time": 0.0,
            "total_cost": 0.0,
            "last_call_time": None,
            "quality_scores": deque(maxlen=100)
        })
        
        # 告警回调
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        # 监控任务
        self._monitoring_task: Optional[asyncio.Task] = None
        self._lock = threading.RLock()
        
        # 启动监控
        self._start_monitoring()
        
        # 加载历史数据
        if self.config.enable_persistence:
            self._load_historical_data()
    
    def _load_monitoring_config(self) -> MonitoringConfig:
        """加载监控配置"""
        config_data = self.config_manager.get('monitoring', {})
        
        return MonitoringConfig(
            max_records=config_data.get('max_records', 10000),
            max_snapshots=config_data.get('max_snapshots', 1000),
            max_alerts=config_data.get('max_alerts', 500),
            metrics_window_minutes=config_data.get('metrics_window_minutes', 5),
            response_time_threshold=config_data.get('response_time_threshold', 30.0),
            error_rate_threshold=config_data.get('error_rate_threshold', 0.1),
            cost_threshold_per_hour=config_data.get('cost_threshold_per_hour', 10.0),
            monitoring_interval=config_data.get('monitoring_interval', 60),
            enable_persistence=config_data.get('enable_persistence', True),
            persistence_file=config_data.get('persistence_file', 'logs/api_monitoring.json')
        )
    
    def record_api_call(self, response: APIResponse, model_config: ModelConfig):
        """记录API调用"""
        with self._lock:
            # 创建调用记录
            record = APICallRecord(
                request_id=response.request_id,
                model_id=response.model_id,
                timestamp=response.timestamp,
                response_time=response.response_time,
                success=response.is_successful(),
                error_message=response.error_message,
                usage_stats=response.usage_stats,
                quality_score=response.quality_score,
                cost=response.usage_stats.cost if response.usage_stats else 0.0
            )
            
            # 添加到记录队列
            self.call_records.append(record)
            
            # 更新实时统计
            self._update_model_stats(record)
            
            # 检查告警条件
            self._check_alerts(record, model_config)
            
            logger.debug(f"记录API调用: {record.request_id} - {record.model_id}")
    
    def _update_model_stats(self, record: APICallRecord):
        """更新模型统计信息"""
        stats = self.model_stats[record.model_id]
        
        stats["total_calls"] += 1
        stats["total_response_time"] += record.response_time
        stats["total_cost"] += record.cost
        stats["last_call_time"] = record.timestamp
        
        if record.success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
        
        if record.quality_score is not None:
            stats["quality_scores"].append(record.quality_score)
    
    def _check_alerts(self, record: APICallRecord, model_config: ModelConfig):
        """检查告警条件"""
        # 响应时间告警
        if record.response_time > self.config.response_time_threshold:
            self._create_alert(
                level=AlertLevel.WARNING,
                title="响应时间过长",
                message=f"模型 {record.model_id} 响应时间 {record.response_time:.2f}s 超过阈值 {self.config.response_time_threshold}s",
                model_id=record.model_id,
                metric_type=MetricType.RESPONSE_TIME,
                threshold_value=self.config.response_time_threshold,
                actual_value=record.response_time
            )
        
        # 错误率告警
        stats = self.model_stats[record.model_id]
        if stats["total_calls"] >= 10:  # 至少10次调用后才检查错误率
            error_rate = stats["failed_calls"] / stats["total_calls"]
            if error_rate > self.config.error_rate_threshold:
                self._create_alert(
                    level=AlertLevel.ERROR,
                    title="错误率过高",
                    message=f"模型 {record.model_id} 错误率 {error_rate:.2%} 超过阈值 {self.config.error_rate_threshold:.2%}",
                    model_id=record.model_id,
                    metric_type=MetricType.ERROR_RATE,
                    threshold_value=self.config.error_rate_threshold,
                    actual_value=error_rate
                )
        
        # 成本告警（每小时）
        hourly_cost = self._calculate_hourly_cost(record.model_id)
        if hourly_cost > self.config.cost_threshold_per_hour:
            self._create_alert(
                level=AlertLevel.WARNING,
                title="成本过高",
                message=f"模型 {record.model_id} 每小时成本 ${hourly_cost:.2f} 超过阈值 ${self.config.cost_threshold_per_hour:.2f}",
                model_id=record.model_id,
                metric_type=MetricType.COST,
                threshold_value=self.config.cost_threshold_per_hour,
                actual_value=hourly_cost
            )
    
    def _calculate_hourly_cost(self, model_id: str) -> float:
        """计算每小时成本"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        hourly_cost = 0.0
        for record in self.call_records:
            if (record.model_id == model_id and 
                record.timestamp >= one_hour_ago):
                hourly_cost += record.cost
        
        return hourly_cost
    
    def _create_alert(self, level: AlertLevel, title: str, message: str,
                     model_id: Optional[str] = None,
                     metric_type: Optional[MetricType] = None,
                     threshold_value: Optional[float] = None,
                     actual_value: Optional[float] = None):
        """创建告警"""
        alert_id = f"alert_{int(time.time() * 1000)}"
        
        alert = Alert(
            id=alert_id,
            level=level,
            title=title,
            message=message,
            timestamp=datetime.now(),
            model_id=model_id,
            metric_type=metric_type,
            threshold_value=threshold_value,
            actual_value=actual_value
        )
        
        self.alerts.append(alert)
        
        # 触发告警回调
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"告警回调执行失败: {str(e)}")
        
        logger.warning(f"创建告警: {alert.title} - {alert.message}")
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """添加告警回调"""
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[Alert], None]):
        """移除告警回调"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    def get_model_metrics(self, model_id: str, 
                         time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """获取模型指标"""
        if time_range is None:
            time_range = timedelta(minutes=self.config.metrics_window_minutes)
        
        cutoff_time = datetime.now() - time_range
        
        # 过滤时间范围内的记录
        relevant_records = [
            record for record in self.call_records
            if record.model_id == model_id and record.timestamp >= cutoff_time
        ]
        
        if not relevant_records:
            return {
                "model_id": model_id,
                "time_range_minutes": time_range.total_seconds() / 60,
                "total_calls": 0,
                "metrics": {}
            }
        
        # 计算指标
        total_calls = len(relevant_records)
        successful_calls = sum(1 for r in relevant_records if r.success)
        failed_calls = total_calls - successful_calls
        
        response_times = [r.response_time for r in relevant_records]
        costs = [r.cost for r in relevant_records]
        quality_scores = [r.quality_score for r in relevant_records if r.quality_score is not None]
        
        metrics = {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0.0,
            "error_rate": failed_calls / total_calls if total_calls > 0 else 0.0,
            "average_response_time": sum(response_times) / len(response_times) if response_times else 0.0,
            "min_response_time": min(response_times) if response_times else 0.0,
            "max_response_time": max(response_times) if response_times else 0.0,
            "total_cost": sum(costs),
            "average_cost_per_call": sum(costs) / len(costs) if costs else 0.0,
            "throughput_per_minute": total_calls / (time_range.total_seconds() / 60),
            "average_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else None
        }
        
        return {
            "model_id": model_id,
            "time_range_minutes": time_range.total_seconds() / 60,
            "total_calls": total_calls,
            "metrics": metrics
        }
    
    def get_all_models_metrics(self, time_range: Optional[timedelta] = None) -> Dict[str, Dict[str, Any]]:
        """获取所有模型的指标"""
        model_ids = set(record.model_id for record in self.call_records)
        
        return {
            model_id: self.get_model_metrics(model_id, time_range)
            for model_id in model_ids
        }
    
    def get_system_overview(self) -> Dict[str, Any]:
        """获取系统概览"""
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        # 最近一小时的记录
        hour_records = [r for r in self.call_records if r.timestamp >= last_hour]
        day_records = [r for r in self.call_records if r.timestamp >= last_day]
        
        return {
            "timestamp": now.isoformat(),
            "total_records": len(self.call_records),
            "active_models": len(set(r.model_id for r in self.call_records)),
            "last_hour": {
                "total_calls": len(hour_records),
                "successful_calls": sum(1 for r in hour_records if r.success),
                "total_cost": sum(r.cost for r in hour_records),
                "average_response_time": sum(r.response_time for r in hour_records) / len(hour_records) if hour_records else 0.0
            },
            "last_day": {
                "total_calls": len(day_records),
                "successful_calls": sum(1 for r in day_records if r.success),
                "total_cost": sum(r.cost for r in day_records),
                "average_response_time": sum(r.response_time for r in day_records) / len(day_records) if day_records else 0.0
            },
            "active_alerts": len([a for a in self.alerts if not a.resolved]),
            "total_alerts": len(self.alerts)
        }
    
    def get_cost_analysis(self, time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """获取成本分析"""
        if time_range is None:
            time_range = timedelta(days=1)
        
        cutoff_time = datetime.now() - time_range
        relevant_records = [r for r in self.call_records if r.timestamp >= cutoff_time]
        
        # 按模型分组成本
        model_costs = defaultdict(float)
        model_calls = defaultdict(int)
        
        for record in relevant_records:
            model_costs[record.model_id] += record.cost
            model_calls[record.model_id] += 1
        
        # 计算成本效率
        cost_efficiency = {}
        for model_id in model_costs:
            avg_cost = model_costs[model_id] / model_calls[model_id]
            # 获取平均质量分数
            quality_scores = [r.quality_score for r in relevant_records 
                            if r.model_id == model_id and r.quality_score is not None]
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            
            cost_efficiency[model_id] = {
                "total_cost": model_costs[model_id],
                "total_calls": model_calls[model_id],
                "average_cost_per_call": avg_cost,
                "average_quality_score": avg_quality,
                "cost_efficiency": avg_quality / avg_cost if avg_cost > 0 else 0.0
            }
        
        return {
            "time_range_hours": time_range.total_seconds() / 3600,
            "total_cost": sum(model_costs.values()),
            "total_calls": sum(model_calls.values()),
            "model_breakdown": cost_efficiency,
            "projected_monthly_cost": sum(model_costs.values()) * (30 * 24) / (time_range.total_seconds() / 3600)
        }
    
    def get_alerts(self, resolved: Optional[bool] = None, 
                  level: Optional[AlertLevel] = None) -> List[Alert]:
        """获取告警列表"""
        alerts = list(self.alerts)
        
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        if level is not None:
            alerts = [a for a in alerts if a.level == level]
        
        # 按时间倒序排列
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        
        return alerts
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"告警已解决: {alert_id}")
                return True
        
        return False
    
    def _start_monitoring(self):
        """启动监控任务"""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_worker())
    
    async def _monitoring_worker(self):
        """监控工作任务"""
        while True:
            try:
                await asyncio.sleep(self.config.monitoring_interval)
                await self._collect_metrics()
                
                if self.config.enable_persistence:
                    self._save_data()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控任务异常: {str(e)}")
    
    async def _collect_metrics(self):
        """收集指标快照"""
        now = datetime.now()
        
        for model_id in set(record.model_id for record in self.call_records):
            metrics = self.get_model_metrics(model_id)["metrics"]
            
            # 创建指标快照
            for metric_name, value in metrics.items():
                if isinstance(value, (int, float)):
                    try:
                        metric_type = MetricType(metric_name)
                        snapshot = MetricSnapshot(
                            timestamp=now,
                            model_id=model_id,
                            metric_type=metric_type,
                            value=float(value)
                        )
                        self.metric_snapshots.append(snapshot)
                    except ValueError:
                        # 跳过不支持的指标类型
                        continue
    
    def _save_data(self):
        """保存数据到文件"""
        try:
            # 确保目录存在
            Path(self.config.persistence_file).parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "timestamp": datetime.now().isoformat(),
                "call_records": [record.to_dict() for record in list(self.call_records)[-1000:]],  # 只保存最近1000条
                "alerts": [alert.to_dict() for alert in list(self.alerts)[-100:]],  # 只保存最近100条告警
                "model_stats": {
                    model_id: {
                        **stats,
                        "last_call_time": stats["last_call_time"].isoformat() if stats["last_call_time"] else None,
                        "quality_scores": list(stats["quality_scores"])
                    }
                    for model_id, stats in self.model_stats.items()
                }
            }
            
            with open(self.config.persistence_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"保存监控数据失败: {str(e)}")
    
    def _load_historical_data(self):
        """加载历史数据"""
        try:
            if not Path(self.config.persistence_file).exists():
                return
            
            with open(self.config.persistence_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载调用记录
            for record_data in data.get("call_records", []):
                try:
                    usage_stats = None
                    if record_data.get("usage_stats"):
                        usage_stats = UsageStats(**record_data["usage_stats"])
                    
                    record = APICallRecord(
                        request_id=record_data["request_id"],
                        model_id=record_data["model_id"],
                        timestamp=datetime.fromisoformat(record_data["timestamp"]),
                        response_time=record_data["response_time"],
                        success=record_data["success"],
                        error_message=record_data.get("error_message"),
                        usage_stats=usage_stats,
                        quality_score=record_data.get("quality_score"),
                        cost=record_data.get("cost", 0.0)
                    )
                    self.call_records.append(record)
                except Exception as e:
                    logger.warning(f"加载调用记录失败: {str(e)}")
            
            # 加载告警
            for alert_data in data.get("alerts", []):
                try:
                    alert = Alert(
                        id=alert_data["id"],
                        level=AlertLevel(alert_data["level"]),
                        title=alert_data["title"],
                        message=alert_data["message"],
                        timestamp=datetime.fromisoformat(alert_data["timestamp"]),
                        model_id=alert_data.get("model_id"),
                        metric_type=MetricType(alert_data["metric_type"]) if alert_data.get("metric_type") else None,
                        threshold_value=alert_data.get("threshold_value"),
                        actual_value=alert_data.get("actual_value"),
                        resolved=alert_data.get("resolved", False),
                        resolved_at=datetime.fromisoformat(alert_data["resolved_at"]) if alert_data.get("resolved_at") else None
                    )
                    self.alerts.append(alert)
                except Exception as e:
                    logger.warning(f"加载告警失败: {str(e)}")
            
            logger.info(f"加载历史数据成功: {len(self.call_records)} 条记录, {len(self.alerts)} 条告警")
            
        except Exception as e:
            logger.error(f"加载历史数据失败: {str(e)}")
    
    def stop_monitoring(self):
        """停止监控"""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
        
        if self.config.enable_persistence:
            self._save_data()
    
    def clear_data(self, data_type: str = "all"):
        """清除数据"""
        with self._lock:
            if data_type in ["all", "records"]:
                self.call_records.clear()
                logger.info("清除调用记录")
            
            if data_type in ["all", "alerts"]:
                self.alerts.clear()
                logger.info("清除告警")
            
            if data_type in ["all", "snapshots"]:
                self.metric_snapshots.clear()
                logger.info("清除指标快照")
            
            if data_type in ["all", "stats"]:
                self.model_stats.clear()
                logger.info("清除统计信息")
    
    def export_data(self, format: str = "json") -> str:
        """导出数据"""
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "config": asdict(self.config),
            "call_records": [record.to_dict() for record in self.call_records],
            "alerts": [alert.to_dict() for alert in self.alerts],
            "model_stats": {
                model_id: {
                    **stats,
                    "last_call_time": stats["last_call_time"].isoformat() if stats["last_call_time"] else None,
                    "quality_scores": list(stats["quality_scores"])
                }
                for model_id, stats in self.model_stats.items()
            }
        }
        
        if format.lower() == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的导出格式: {format}")
    
    def __del__(self):
        """析构函数"""
        self.stop_monitoring()