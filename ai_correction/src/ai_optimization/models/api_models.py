"""
API调用相关数据模型

定义模型配置、API响应和调用上下文的数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
import json


class ModelProvider(Enum):
    """模型提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    BAIDU = "baidu"
    ALIBABA = "alibaba"
    CUSTOM = "custom"


class ModelStatus(Enum):
    """模型状态枚举"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class TaskType(Enum):
    """任务类型枚举"""
    GRADING = "grading"           # 批改
    ANALYSIS = "analysis"         # 分析
    SUMMARY = "summary"           # 总结
    TRANSLATION = "translation"   # 翻译
    QA = "qa"                    # 问答
    CLASSIFICATION = "classification"  # 分类


@dataclass
class UsageStats:
    """使用统计"""
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    request_count: int = 0
    
    def add_usage(self, prompt_tokens: int, completion_tokens: int, cost: float):
        """添加使用统计"""
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens = self.prompt_tokens + self.completion_tokens
        self.cost += cost
        self.request_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost": self.cost,
            "request_count": self.request_count
        }


@dataclass
class ModelConfig:
    """模型配置"""
    id: str
    name: str
    provider: ModelProvider
    endpoint: str
    supported_tasks: List[TaskType] = field(default_factory=list)
    max_content_size: int = 100000  # 最大内容大小（字符数）
    max_tokens: int = 4096
    cost_per_token: float = 0.0
    performance_rating: float = 0.0
    is_available: bool = True
    status: ModelStatus = ModelStatus.AVAILABLE
    api_key: Optional[str] = None
    additional_params: Dict[str, Any] = field(default_factory=dict)
    rate_limits: Dict[str, int] = field(default_factory=dict)  # 速率限制
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def supports_task(self, task_type: TaskType) -> bool:
        """检查是否支持指定任务类型"""
        return task_type in self.supported_tasks
    
    def can_handle_content_size(self, size: int) -> bool:
        """检查是否能处理指定大小的内容"""
        return size <= self.max_content_size
    
    def estimate_cost(self, token_count: int) -> float:
        """估算成本"""
        return token_count * self.cost_per_token
    
    def update_status(self, status: ModelStatus, reason: str = ""):
        """更新状态"""
        self.status = status
        self.is_available = status == ModelStatus.AVAILABLE
        self.updated_at = datetime.now()
        
        if not hasattr(self, 'status_history'):
            self.status_history = []
        
        self.status_history.append({
            "status": status.value,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider.value,
            "endpoint": self.endpoint,
            "supported_tasks": [task.value for task in self.supported_tasks],
            "max_content_size": self.max_content_size,
            "max_tokens": self.max_tokens,
            "cost_per_token": self.cost_per_token,
            "performance_rating": self.performance_rating,
            "is_available": self.is_available,
            "status": self.status.value,
            "additional_params": self.additional_params,
            "rate_limits": self.rate_limits,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelConfig':
        """从字典创建实例"""
        supported_tasks = [
            TaskType(task) for task in data.get("supported_tasks", [])
        ]
        
        return cls(
            id=data["id"],
            name=data["name"],
            provider=ModelProvider(data["provider"]),
            endpoint=data["endpoint"],
            supported_tasks=supported_tasks,
            max_content_size=data.get("max_content_size", 100000),
            max_tokens=data.get("max_tokens", 4096),
            cost_per_token=data.get("cost_per_token", 0.0),
            performance_rating=data.get("performance_rating", 0.0),
            is_available=data.get("is_available", True),
            status=ModelStatus(data.get("status", "available")),
            additional_params=data.get("additional_params", {}),
            rate_limits=data.get("rate_limits", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )


@dataclass
class APICallContext:
    """API调用上下文"""
    request_id: str
    model_config: ModelConfig
    task_type: TaskType
    content_size: int
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 30
    start_time: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def should_retry(self) -> bool:
        """判断是否应该重试"""
        return self.retry_count < self.max_retries
    
    def increment_retry(self):
        """增加重试次数"""
        self.retry_count += 1
    
    def get_elapsed_time(self) -> float:
        """获取已用时间（秒）"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def is_timeout(self) -> bool:
        """检查是否超时"""
        return self.get_elapsed_time() > self.timeout
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "model_config": self.model_config.to_dict(),
            "task_type": self.task_type.value,
            "content_size": self.content_size,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "start_time": self.start_time.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class APIResponse:
    """API响应"""
    request_id: str
    model_id: str
    content: str
    usage_stats: UsageStats = field(default_factory=UsageStats)
    response_time: float = 0.0
    quality_score: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    status_code: int = 200
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_successful(self) -> bool:
        """检查响应是否成功"""
        return 200 <= self.status_code < 300 and self.error_message is None
    
    def has_content(self) -> bool:
        """检查是否有内容"""
        return bool(self.content and self.content.strip())
    
    def get_cost_efficiency(self) -> float:
        """获取成本效率（质量分数/成本）"""
        if self.usage_stats.cost == 0 or self.quality_score is None:
            return 0.0
        return self.quality_score / self.usage_stats.cost
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "content": self.content,
            "usage_stats": self.usage_stats.to_dict(),
            "response_time": self.response_time,
            "quality_score": self.quality_score,
            "timestamp": self.timestamp.isoformat(),
            "status_code": self.status_code,
            "error_message": self.error_message,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIResponse':
        """从字典创建实例"""
        usage_data = data.get("usage_stats", {})
        usage_stats = UsageStats(
            total_tokens=usage_data.get("total_tokens", 0),
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            cost=usage_data.get("cost", 0.0),
            request_count=usage_data.get("request_count", 0)
        )
        
        return cls(
            request_id=data["request_id"],
            model_id=data["model_id"],
            content=data["content"],
            usage_stats=usage_stats,
            response_time=data.get("response_time", 0.0),
            quality_score=data.get("quality_score"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            status_code=data.get("status_code", 200),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {})
        )


@dataclass
class RetryStrategy:
    """重试策略"""
    strategy_type: str  # exponential, linear, immediate
    base_delay: float = 1.0
    max_delay: float = 60.0
    max_retries: int = 3
    backoff_multiplier: float = 2.0
    jitter: bool = True
    
    def calculate_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        if self.strategy_type == "exponential":
            delay = self.base_delay * (self.backoff_multiplier ** attempt)
        elif self.strategy_type == "linear":
            delay = self.base_delay * (attempt + 1)
        else:  # immediate
            delay = 0.0
        
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # 添加50%的随机抖动
        
        return delay
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """判断是否应该重试"""
        if attempt >= self.max_retries:
            return False
        
        # 根据错误类型判断是否应该重试
        error_type = type(error).__name__
        non_retryable_errors = [
            "AuthenticationError",
            "PermissionError", 
            "ValidationError",
            "InvalidRequestError"
        ]
        
        return error_type not in non_retryable_errors


# 导出所有模型类
__all__ = [
    "ModelProvider",
    "ModelStatus", 
    "TaskType",
    "UsageStats",
    "ModelConfig",
    "APICallContext",
    "APIResponse",
    "RetryStrategy"
]