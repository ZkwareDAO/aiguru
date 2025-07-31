#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志系统配置
提供结构化日志和性能监控，支持AI优化专用日志功能
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from datetime import datetime
import threading
import time
from collections import defaultdict, deque
from enum import Enum

try:
    from src.config.settings import LoggingSettings
except ImportError:
    # 如果无法导入，使用默认配置
    class LoggingSettings:
        def __init__(self):
            self.level = "INFO"
            self.file_path = Path("logs/app.log")
            self.max_size = 10 * 1024 * 1024  # 10MB
            self.backup_count = 5


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record):
        # 创建结构化日志记录
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """彩色控制台格式化器"""
    
    # 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 添加颜色
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        
        # 格式化消息
        formatted = super().format(record)
        return formatted


def setup_logging(config: LoggingSettings) -> logging.Logger:
    """设置日志系统"""
    
    # 创建根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.upper()))
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredConsoleFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（如果配置了文件路径）
    if config.file_path:
        # 确保日志目录存在
        config.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 使用轮转文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            config.file_path,
            maxBytes=config.max_size,
            backupCount=config.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, config.level.upper()))
        
        # 文件使用结构化格式
        file_formatter = StructuredFormatter()
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # 创建应用日志器
    app_logger = logging.getLogger('ai_grading_system')
    
    return app_logger


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertLevel(Enum):
    """告警级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class PerformanceLogger:
    """性能日志记录器"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_operation_start(self, operation: str, **kwargs):
        """记录操作开始"""
        extra_fields = {
            "operation": operation,
            "status": "started",
            **kwargs
        }
        
        # 创建带有额外字段的日志记录
        record = self.logger.makeRecord(
            self.logger.name,
            logging.INFO,
            __file__,
            0,
            f"操作开始: {operation}",
            (),
            None
        )
        record.extra_fields = extra_fields
        self.logger.handle(record)
    
    def log_operation_complete(self, operation: str, duration: float, success: bool = True, **kwargs):
        """记录操作完成"""
        extra_fields = {
            "operation": operation,
            "status": "completed" if success else "failed",
            "duration_seconds": duration,
            **kwargs
        }
        
        status_text = "完成" if success else "失败"
        message = f"操作{status_text}: {operation} (耗时: {duration:.2f}秒)"
        
        record = self.logger.makeRecord(
            self.logger.name,
            logging.INFO if success else logging.ERROR,
            __file__,
            0,
            message,
            (),
            None
        )
        record.extra_fields = extra_fields
        self.logger.handle(record)
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = "", **kwargs):
        """记录性能指标"""
        extra_fields = {
            "metric_name": metric_name,
            "metric_value": value,
            "metric_unit": unit,
            "metric_type": "performance",
            **kwargs
        }
        
        message = f"性能指标: {metric_name} = {value} {unit}"
        
        record = self.logger.makeRecord(
            self.logger.name,
            logging.INFO,
            __file__,
            0,
            message,
            (),
            None
        )
        record.extra_fields = extra_fields
        self.logger.handle(record)


class AIOptimizationLogger:
    """AI优化专用日志记录器"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.performance_logger = PerformanceLogger(logger)
    
    def log_prompt_generation(self, template_id: str, prompt_length: int, 
                            generation_time: float, success: bool = True, **kwargs):
        """记录提示词生成"""
        extra_fields = {
            "event_type": "prompt_generation",
            "template_id": template_id,
            "prompt_length": prompt_length,
            "generation_time": generation_time,
            "success": success,
            **kwargs
        }
        
        status = "成功" if success else "失败"
        message = f"提示词生成{status}: 模板={template_id}, 长度={prompt_length}, 耗时={generation_time:.3f}s"
        
        self._log_with_extra(
            logging.INFO if success else logging.ERROR,
            message,
            extra_fields
        )
    
    def log_api_call(self, model_id: str, request_tokens: int, response_tokens: int,
                    response_time: float, cost: float, success: bool = True, **kwargs):
        """记录API调用"""
        extra_fields = {
            "event_type": "api_call",
            "model_id": model_id,
            "request_tokens": request_tokens,
            "response_tokens": response_tokens,
            "total_tokens": request_tokens + response_tokens,
            "response_time": response_time,
            "cost": cost,
            "success": success,
            **kwargs
        }
        
        status = "成功" if success else "失败"
        message = (f"API调用{status}: 模型={model_id}, "
                  f"tokens={request_tokens + response_tokens}, "
                  f"耗时={response_time:.3f}s, 成本=${cost:.4f}")
        
        self._log_with_extra(
            logging.INFO if success else logging.ERROR,
            message,
            extra_fields
        )
    
    def log_quality_check(self, rule_id: str, check_result: bool, 
                         quality_score: float, **kwargs):
        """记录质量检查"""
        extra_fields = {
            "event_type": "quality_check",
            "rule_id": rule_id,
            "check_result": check_result,
            "quality_score": quality_score,
            **kwargs
        }
        
        result = "通过" if check_result else "失败"
        message = f"质量检查{result}: 规则={rule_id}, 分数={quality_score:.3f}"
        
        self._log_with_extra(
            logging.INFO if check_result else logging.WARNING,
            message,
            extra_fields
        )
    
    def log_content_processing(self, content_type: str, file_size: int,
                             processing_time: float, success: bool = True, **kwargs):
        """记录内容处理"""
        extra_fields = {
            "event_type": "content_processing",
            "content_type": content_type,
            "file_size": file_size,
            "processing_time": processing_time,
            "success": success,
            **kwargs
        }
        
        status = "成功" if success else "失败"
        message = (f"内容处理{status}: 类型={content_type}, "
                  f"大小={file_size}bytes, 耗时={processing_time:.3f}s")
        
        self._log_with_extra(
            logging.INFO if success else logging.ERROR,
            message,
            extra_fields
        )
    
    def log_cache_operation(self, operation: str, cache_key: str, 
                          hit: bool = None, **kwargs):
        """记录缓存操作"""
        extra_fields = {
            "event_type": "cache_operation",
            "operation": operation,
            "cache_key": cache_key,
            **kwargs
        }
        
        if hit is not None:
            extra_fields["cache_hit"] = hit
            hit_status = "命中" if hit else "未命中"
            message = f"缓存{operation}: key={cache_key}, {hit_status}"
        else:
            message = f"缓存{operation}: key={cache_key}"
        
        self._log_with_extra(logging.DEBUG, message, extra_fields)
    
    def log_error_recovery(self, error_type: str, recovery_action: str,
                          success: bool = True, **kwargs):
        """记录错误恢复"""
        extra_fields = {
            "event_type": "error_recovery",
            "error_type": error_type,
            "recovery_action": recovery_action,
            "success": success,
            **kwargs
        }
        
        status = "成功" if success else "失败"
        message = f"错误恢复{status}: 错误类型={error_type}, 恢复动作={recovery_action}"
        
        self._log_with_extra(
            logging.INFO if success else logging.ERROR,
            message,
            extra_fields
        )
    
    def _log_with_extra(self, level: int, message: str, extra_fields: Dict[str, Any]):
        """使用额外字段记录日志"""
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            __file__,
            0,
            message,
            (),
            None
        )
        record.extra_fields = extra_fields
        self.logger.handle(record)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = threading.RLock()
    
    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """增加计数器"""
        with self._lock:
            key = self._make_key(name, tags)
            self.counters[key] += value
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """设置仪表值"""
        with self._lock:
            key = self._make_key(name, tags)
            self.gauges[key] = value
    
    def record_timer(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录计时器值"""
        with self._lock:
            key = self._make_key(name, tags)
            self.timers[key].append(value)
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录直方图值"""
        with self._lock:
            key = self._make_key(name, tags)
            self.metrics[key].append(value)
    
    def get_counter(self, name: str, tags: Dict[str, str] = None) -> int:
        """获取计数器值"""
        with self._lock:
            key = self._make_key(name, tags)
            return self.counters.get(key, 0)
    
    def get_gauge(self, name: str, tags: Dict[str, str] = None) -> Optional[float]:
        """获取仪表值"""
        with self._lock:
            key = self._make_key(name, tags)
            return self.gauges.get(key)
    
    def get_timer_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, float]:
        """获取计时器统计"""
        with self._lock:
            key = self._make_key(name, tags)
            values = list(self.timers.get(key, []))
            
            if not values:
                return {}
            
            values.sort()
            count = len(values)
            
            return {
                "count": count,
                "min": values[0],
                "max": values[-1],
                "mean": sum(values) / count,
                "p50": values[count // 2],
                "p95": values[int(count * 0.95)] if count > 1 else values[0],
                "p99": values[int(count * 0.99)] if count > 1 else values[0]
            }
    
    def get_histogram_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, float]:
        """获取直方图统计"""
        with self._lock:
            key = self._make_key(name, tags)
            values = self.metrics.get(key, [])
            
            if not values:
                return {}
            
            sorted_values = sorted(values)
            count = len(sorted_values)
            
            return {
                "count": count,
                "min": sorted_values[0],
                "max": sorted_values[-1],
                "mean": sum(sorted_values) / count,
                "p50": sorted_values[count // 2],
                "p95": sorted_values[int(count * 0.95)] if count > 1 else sorted_values[0],
                "p99": sorted_values[int(count * 0.99)] if count > 1 else sorted_values[0]
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        with self._lock:
            result = {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "timers": {},
                "histograms": {}
            }
            
            for name in self.timers:
                result["timers"][name] = self.get_timer_stats(name)
            
            for name in self.metrics:
                result["histograms"][name] = self.get_histogram_stats(name)
            
            return result
    
    def reset_metrics(self):
        """重置所有指标"""
        with self._lock:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()
            self.timers.clear()
    
    def _make_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """生成指标键"""
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"


class AlertManager:
    """告警管理器"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.notification_handlers: List[callable] = []
        self._lock = threading.RLock()
    
    def add_alert_rule(self, name: str, condition: callable, 
                      level: AlertLevel = AlertLevel.MEDIUM,
                      message_template: str = "", 
                      cooldown_seconds: int = 300):
        """添加告警规则"""
        with self._lock:
            self.alert_rules[name] = {
                "condition": condition,
                "level": level,
                "message_template": message_template,
                "cooldown_seconds": cooldown_seconds,
                "last_triggered": 0
            }
    
    def check_alerts(self, metrics: Dict[str, Any]):
        """检查告警条件"""
        current_time = time.time()
        
        with self._lock:
            for rule_name, rule in self.alert_rules.items():
                try:
                    # 检查冷却时间
                    if current_time - rule["last_triggered"] < rule["cooldown_seconds"]:
                        continue
                    
                    # 检查告警条件
                    if rule["condition"](metrics):
                        self._trigger_alert(rule_name, rule, metrics)
                        rule["last_triggered"] = current_time
                        
                except Exception as e:
                    self.logger.error(f"告警规则检查失败 {rule_name}: {e}")
    
    def _trigger_alert(self, rule_name: str, rule: Dict[str, Any], metrics: Dict[str, Any]):
        """触发告警"""
        alert = {
            "rule_name": rule_name,
            "level": rule["level"].value,
            "message": rule["message_template"].format(**metrics) if rule["message_template"] else f"告警触发: {rule_name}",
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        }
        
        # 记录告警历史
        self.alert_history.append(alert)
        
        # 记录日志
        log_level = {
            AlertLevel.LOW: logging.INFO,
            AlertLevel.MEDIUM: logging.WARNING,
            AlertLevel.HIGH: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }.get(rule["level"], logging.WARNING)
        
        self.logger.log(log_level, f"告警触发: {alert['message']}")
        
        # 发送通知
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"告警通知发送失败: {e}")
    
    def add_notification_handler(self, handler: callable):
        """添加通知处理器"""
        self.notification_handlers.append(handler)
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取告警历史"""
        with self._lock:
            return list(self.alert_history)[-limit:]
    
    def clear_alert_history(self):
        """清空告警历史"""
        with self._lock:
            self.alert_history.clear()


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, logger: logging.Logger, 
                 metrics_collector: MetricsCollector = None,
                 alert_manager: AlertManager = None):
        self.logger = logger
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.alert_manager = alert_manager or AlertManager(logger)
        self.ai_logger = AIOptimizationLogger(logger)
        self._monitoring_thread = None
        self._monitoring_enabled = False
        self._monitoring_interval = 60  # 60秒
        
        # 设置默认告警规则
        self._setup_default_alerts()
    
    def _setup_default_alerts(self):
        """设置默认告警规则"""
        # 响应时间过长告警
        self.alert_manager.add_alert_rule(
            "slow_response",
            lambda m: m.get("timers", {}).get("api_response_time", {}).get("p95", 0) > 30,
            AlertLevel.HIGH,
            "API响应时间过长: P95={timers[api_response_time][p95]:.2f}s"
        )
        
        # 错误率过高告警
        self.alert_manager.add_alert_rule(
            "high_error_rate",
            lambda m: m.get("counters", {}).get("api_errors", 0) / max(m.get("counters", {}).get("api_calls", 1), 1) > 0.1,
            AlertLevel.HIGH,
            "API错误率过高: {error_rate:.2%}"
        )
        
        # 成本过高告警
        self.alert_manager.add_alert_rule(
            "high_cost",
            lambda m: m.get("gauges", {}).get("hourly_cost", 0) > 10.0,
            AlertLevel.MEDIUM,
            "小时成本过高: ${hourly_cost:.2f}"
        )
    
    def start_monitoring(self, interval: int = 60):
        """启动监控"""
        if self._monitoring_enabled:
            return
        
        self._monitoring_enabled = True
        self._monitoring_interval = interval
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_worker,
            daemon=True
        )
        self._monitoring_thread.start()
        
        self.logger.info(f"性能监控已启动，间隔: {interval}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring_enabled = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        
        self.logger.info("性能监控已停止")
    
    def _monitoring_worker(self):
        """监控工作线程"""
        while self._monitoring_enabled:
            try:
                # 收集指标
                metrics = self.metrics_collector.get_all_metrics()
                
                # 检查告警
                self.alert_manager.check_alerts(metrics)
                
                # 记录监控日志
                self.logger.debug(f"性能监控检查完成，指标数量: {len(metrics)}")
                
                time.sleep(self._monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"性能监控异常: {e}")
                time.sleep(self._monitoring_interval)
    
    def record_api_call(self, model_id: str, response_time: float, 
                       tokens: int, cost: float, success: bool = True):
        """记录API调用指标"""
        # 记录指标
        self.metrics_collector.increment_counter("api_calls", tags={"model": model_id})
        self.metrics_collector.record_timer("api_response_time", response_time, tags={"model": model_id})
        self.metrics_collector.increment_counter("api_tokens", tokens, tags={"model": model_id})
        self.metrics_collector.record_histogram("api_cost", cost, tags={"model": model_id})
        
        if not success:
            self.metrics_collector.increment_counter("api_errors", tags={"model": model_id})
        
        # 记录日志
        self.ai_logger.log_api_call(
            model_id=model_id,
            request_tokens=0,  # 需要从调用方传入
            response_tokens=tokens,
            response_time=response_time,
            cost=cost,
            success=success
        )
    
    def record_quality_check(self, rule_id: str, passed: bool, score: float):
        """记录质量检查指标"""
        self.metrics_collector.increment_counter("quality_checks", tags={"rule": rule_id})
        self.metrics_collector.record_histogram("quality_scores", score, tags={"rule": rule_id})
        
        if passed:
            self.metrics_collector.increment_counter("quality_passed", tags={"rule": rule_id})
        else:
            self.metrics_collector.increment_counter("quality_failed", tags={"rule": rule_id})
        
        self.ai_logger.log_quality_check(rule_id, passed, score)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        metrics = self.metrics_collector.get_all_metrics()
        alerts = self.alert_manager.get_alert_history(10)
        
        return {
            "metrics": metrics,
            "recent_alerts": alerts,
            "monitoring_status": "running" if self._monitoring_enabled else "stopped"
        }


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器"""
    return logging.getLogger(name)


def get_performance_logger(name: str) -> PerformanceLogger:
    """获取性能日志器"""
    logger = get_logger(name)
    return PerformanceLogger(logger)


if __name__ == "__main__":
    # 日志系统测试
    from src.config.settings import LoggingSettings
    
    config = LoggingSettings()
    logger = setup_logging(config)
    
    # 测试不同级别的日志
    logger.debug("这是调试信息")
    logger.info("这是信息日志")
    logger.warning("这是警告信息")
    logger.error("这是错误信息")
    
    # 测试性能日志
    perf_logger = get_performance_logger("test")
    perf_logger.log_operation_start("test_operation", user_id="test_user")
    
    import time
    time.sleep(0.1)
    
    perf_logger.log_operation_complete("test_operation", 0.1, True, user_id="test_user")
    perf_logger.log_performance_metric("response_time", 0.1, "seconds")
    
    print("✅ 日志系统测试完成")