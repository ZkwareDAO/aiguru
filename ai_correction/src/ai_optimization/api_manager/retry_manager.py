"""
智能重试管理器

实现多种重试策略、错误分类和模型自动切换功能。
"""

import asyncio
import time
import random
import logging
from typing import Dict, List, Optional, Callable, Any, Type, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from ..models.api_models import APIResponse, ModelConfig, RetryStrategy, APICallContext
from .model_manager import ModelManager

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """错误类型枚举"""
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    SERVER_ERROR = "server_error"
    AUTH_ERROR = "auth_error"
    VALIDATION_ERROR = "validation_error"
    MODEL_ERROR = "model_error"
    UNKNOWN_ERROR = "unknown_error"

class RetryDecision(Enum):
    """重试决策枚举"""
    RETRY_SAME_MODEL = "retry_same_model"
    SWITCH_MODEL = "switch_model"
    ABORT = "abort"

@dataclass
class RetryContext:
    """重试上下文"""
    original_request: Dict[str, Any]
    current_model_id: str
    attempt_count: int = 0
    max_attempts: int = 3
    failed_models: List[str] = field(default_factory=list)
    last_error: Optional[Exception] = None
    last_error_type: Optional[ErrorType] = None
    start_time: datetime = field(default_factory=datetime.now)
    total_delay: float = 0.0
    
    def add_failed_model(self, model_id: str):
        """添加失败的模型"""
        if model_id not in self.failed_models:
            self.failed_models.append(model_id)
    
    def get_elapsed_time(self) -> float:
        """获取总耗时"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def should_continue(self) -> bool:
        """判断是否应该继续重试"""
        return (self.attempt_count < self.max_attempts and 
                self.get_elapsed_time() < 300)  # 最大5分钟

@dataclass
class RetryResult:
    """重试结果"""
    success: bool
    response: Optional[APIResponse] = None
    final_error: Optional[Exception] = None
    total_attempts: int = 0
    total_time: float = 0.0
    models_tried: List[str] = field(default_factory=list)
    retry_log: List[Dict[str, Any]] = field(default_factory=list)

class RetryManager:
    """智能重试管理器"""
    
    def __init__(self, model_manager: Optional[ModelManager] = None):
        self.model_manager = model_manager
        self.retry_strategies: Dict[ErrorType, RetryStrategy] = self._init_retry_strategies()
        self.error_classifiers: List[Callable[[Exception], ErrorType]] = self._init_error_classifiers()
        self.retry_statistics: Dict[str, Dict[str, Any]] = {}
        
    def _init_retry_strategies(self) -> Dict[ErrorType, RetryStrategy]:
        """初始化重试策略"""
        return {
            ErrorType.NETWORK_ERROR: RetryStrategy(
                strategy_type="exponential",
                base_delay=1.0,
                max_delay=30.0,
                max_retries=3,
                backoff_multiplier=2.0,
                jitter=True
            ),
            ErrorType.TIMEOUT_ERROR: RetryStrategy(
                strategy_type="linear",
                base_delay=2.0,
                max_delay=10.0,
                max_retries=2,
                jitter=False
            ),
            ErrorType.RATE_LIMIT_ERROR: RetryStrategy(
                strategy_type="exponential",
                base_delay=5.0,
                max_delay=120.0,
                max_retries=5,
                backoff_multiplier=2.0,
                jitter=True
            ),
            ErrorType.SERVER_ERROR: RetryStrategy(
                strategy_type="exponential",
                base_delay=2.0,
                max_delay=60.0,
                max_retries=3,
                backoff_multiplier=1.5,
                jitter=True
            ),
            ErrorType.MODEL_ERROR: RetryStrategy(
                strategy_type="immediate",
                base_delay=0.0,
                max_delay=0.0,
                max_retries=0,  # 模型错误不重试，直接切换
                jitter=False
            ),
            ErrorType.AUTH_ERROR: RetryStrategy(
                strategy_type="immediate",
                base_delay=0.0,
                max_delay=0.0,
                max_retries=0,  # 认证错误不重试
                jitter=False
            ),
            ErrorType.VALIDATION_ERROR: RetryStrategy(
                strategy_type="immediate",
                base_delay=0.0,
                max_delay=0.0,
                max_retries=0,  # 验证错误不重试
                jitter=False
            ),
            ErrorType.UNKNOWN_ERROR: RetryStrategy(
                strategy_type="exponential",
                base_delay=1.0,
                max_delay=30.0,
                max_retries=2,
                backoff_multiplier=2.0,
                jitter=True
            )
        }
    
    def _init_error_classifiers(self) -> List[Callable[[Exception], ErrorType]]:
        """初始化错误分类器"""
        return [
            self._classify_by_exception_type,
            self._classify_by_error_message,
            self._classify_by_http_status
        ]
    
    def _classify_by_exception_type(self, error: Exception) -> Optional[ErrorType]:
        """根据异常类型分类错误"""
        error_type_name = type(error).__name__
        
        type_mapping = {
            'TimeoutError': ErrorType.TIMEOUT_ERROR,
            'asyncio.TimeoutError': ErrorType.TIMEOUT_ERROR,
            'aiohttp.ServerTimeoutError': ErrorType.TIMEOUT_ERROR,
            'ConnectionError': ErrorType.NETWORK_ERROR,
            'aiohttp.ClientConnectionError': ErrorType.NETWORK_ERROR,
            'aiohttp.ClientConnectorError': ErrorType.NETWORK_ERROR,
            'AuthenticationError': ErrorType.AUTH_ERROR,
            'PermissionError': ErrorType.AUTH_ERROR,
            'ValidationError': ErrorType.VALIDATION_ERROR,
            'ValueError': ErrorType.VALIDATION_ERROR,
        }
        
        return type_mapping.get(error_type_name)
    
    def _classify_by_error_message(self, error: Exception) -> Optional[ErrorType]:
        """根据错误消息分类错误"""
        error_msg = str(error).lower()
        
        if any(keyword in error_msg for keyword in ['rate limit', 'too many requests', '429']):
            return ErrorType.RATE_LIMIT_ERROR
        elif any(keyword in error_msg for keyword in ['timeout', 'timed out']):
            return ErrorType.TIMEOUT_ERROR
        elif any(keyword in error_msg for keyword in ['network', 'connection', 'dns']):
            return ErrorType.NETWORK_ERROR
        elif any(keyword in error_msg for keyword in ['unauthorized', 'forbidden', 'api key', 'authentication']):
            return ErrorType.AUTH_ERROR
        elif any(keyword in error_msg for keyword in ['invalid', 'validation', 'bad request']):
            return ErrorType.VALIDATION_ERROR
        elif any(keyword in error_msg for keyword in ['model', 'not found', 'unsupported']):
            return ErrorType.MODEL_ERROR
        elif any(keyword in error_msg for keyword in ['server error', '500', '502', '503', '504']):
            return ErrorType.SERVER_ERROR
        
        return None
    
    def _classify_by_http_status(self, error: Exception) -> Optional[ErrorType]:
        """根据HTTP状态码分类错误"""
        error_msg = str(error)
        
        # 提取HTTP状态码
        import re
        status_match = re.search(r'HTTP (\d{3})', error_msg)
        if status_match:
            status_code = int(status_match.group(1))
            
            if status_code == 429:
                return ErrorType.RATE_LIMIT_ERROR
            elif status_code in [401, 403]:
                return ErrorType.AUTH_ERROR
            elif status_code in [400, 422]:
                return ErrorType.VALIDATION_ERROR
            elif status_code in [404, 405]:
                return ErrorType.MODEL_ERROR
            elif status_code >= 500:
                return ErrorType.SERVER_ERROR
        
        return None
    
    def classify_error(self, error: Exception) -> ErrorType:
        """分类错误类型"""
        for classifier in self.error_classifiers:
            error_type = classifier(error)
            if error_type:
                return error_type
        
        return ErrorType.UNKNOWN_ERROR
    
    def make_retry_decision(self, context: RetryContext, error: Exception) -> RetryDecision:
        """做出重试决策"""
        error_type = self.classify_error(error)
        context.last_error = error
        context.last_error_type = error_type
        
        # 获取重试策略
        strategy = self.retry_strategies.get(error_type, self.retry_strategies[ErrorType.UNKNOWN_ERROR])
        
        # 检查是否应该重试
        if not strategy.should_retry(context.attempt_count, error):
            return RetryDecision.ABORT
        
        # 检查是否应该切换模型
        if self._should_switch_model(error_type, context):
            return RetryDecision.SWITCH_MODEL
        
        return RetryDecision.RETRY_SAME_MODEL
    
    def _should_switch_model(self, error_type: ErrorType, context: RetryContext) -> bool:
        """判断是否应该切换模型"""
        # 模型相关错误立即切换
        if error_type in [ErrorType.MODEL_ERROR, ErrorType.AUTH_ERROR]:
            return True
        
        # 如果同一个模型连续失败多次，考虑切换
        if context.attempt_count >= 2:
            return True
        
        # 如果是速率限制错误且有其他可用模型，切换
        if error_type == ErrorType.RATE_LIMIT_ERROR and self.model_manager:
            available_models = self.model_manager.get_available_models()
            unused_models = [m for m in available_models if m.id not in context.failed_models]
            return len(unused_models) > 0
        
        return False
    
    async def execute_with_retry(self, 
                               api_call: Callable,
                               request_data: Dict[str, Any],
                               initial_model: ModelConfig,
                               max_attempts: int = 5) -> RetryResult:
        """
        执行带重试的API调用
        
        Args:
            api_call: API调用函数
            request_data: 请求数据
            initial_model: 初始模型
            max_attempts: 最大尝试次数
            
        Returns:
            RetryResult: 重试结果
        """
        context = RetryContext(
            original_request=request_data,
            current_model_id=initial_model.id,
            max_attempts=max_attempts
        )
        
        result = RetryResult(success=False)
        current_model = initial_model
        
        while context.should_continue():
            context.attempt_count += 1
            attempt_start = time.time()
            
            try:
                logger.info(f"尝试 {context.attempt_count}/{max_attempts} - 模型: {current_model.id}")
                
                # 执行API调用
                response = await api_call(current_model, **request_data)
                
                # 成功响应
                if response and response.is_successful():
                    result.success = True
                    result.response = response
                    result.total_attempts = context.attempt_count
                    result.total_time = context.get_elapsed_time()
                    result.models_tried = [current_model.id] + context.failed_models
                    
                    # 记录成功日志
                    result.retry_log.append({
                        "attempt": context.attempt_count,
                        "model_id": current_model.id,
                        "success": True,
                        "response_time": time.time() - attempt_start
                    })
                    
                    # 更新统计信息
                    self._update_retry_statistics(current_model.id, True, context.attempt_count)
                    
                    return result
                else:
                    # 响应失败，作为错误处理
                    error_msg = response.error_message if response else "Empty response"
                    raise Exception(f"API调用失败: {error_msg}")
                    
            except Exception as e:
                attempt_time = time.time() - attempt_start
                logger.warning(f"尝试 {context.attempt_count} 失败: {str(e)}")
                
                # 记录失败日志
                result.retry_log.append({
                    "attempt": context.attempt_count,
                    "model_id": current_model.id,
                    "success": False,
                    "error": str(e),
                    "error_type": self.classify_error(e).value,
                    "response_time": attempt_time
                })
                
                # 做出重试决策
                decision = self.make_retry_decision(context, e)
                
                if decision == RetryDecision.ABORT:
                    logger.error(f"重试中止: {str(e)}")
                    break
                elif decision == RetryDecision.SWITCH_MODEL:
                    # 切换模型
                    context.add_failed_model(current_model.id)
                    new_model = await self._select_alternative_model(context, request_data)
                    
                    if new_model:
                        logger.info(f"切换模型: {current_model.id} -> {new_model.id}")
                        current_model = new_model
                        context.current_model_id = new_model.id
                    else:
                        logger.error("没有可用的替代模型")
                        break
                else:
                    # 重试相同模型，计算延迟
                    error_type = context.last_error_type or ErrorType.UNKNOWN_ERROR
                    strategy = self.retry_strategies[error_type]
                    delay = strategy.calculate_delay(context.attempt_count - 1)
                    
                    if delay > 0:
                        logger.info(f"等待 {delay:.2f} 秒后重试")
                        await asyncio.sleep(delay)
                        context.total_delay += delay
                
                result.final_error = e
        
        # 所有重试都失败
        result.success = False
        result.total_attempts = context.attempt_count
        result.total_time = context.get_elapsed_time()
        result.models_tried = [context.current_model_id] + context.failed_models
        
        # 更新统计信息
        self._update_retry_statistics(context.current_model_id, False, context.attempt_count)
        
        logger.error(f"所有重试都失败，总尝试次数: {context.attempt_count}")
        return result
    
    async def _select_alternative_model(self, context: RetryContext, request_data: Dict[str, Any]) -> Optional[ModelConfig]:
        """选择替代模型"""
        if not self.model_manager:
            return None
        
        # 获取任务类型（如果有的话）
        task_type = request_data.get('task_type')
        content_size = len(str(request_data.get('content', '')))
        
        # 排除已失败的模型
        exclude_models = context.failed_models + [context.current_model_id]
        
        # 选择最优替代模型
        alternative_model = self.model_manager.select_optimal_model(
            task_type=task_type,
            content_size=content_size,
            priority='balanced',
            exclude_models=exclude_models
        )
        
        return alternative_model
    
    def _update_retry_statistics(self, model_id: str, success: bool, attempts: int):
        """更新重试统计信息"""
        if model_id not in self.retry_statistics:
            self.retry_statistics[model_id] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_attempts": 0,
                "average_attempts": 0.0,
                "last_updated": datetime.now().isoformat()
            }
        
        stats = self.retry_statistics[model_id]
        stats["total_calls"] += 1
        stats["total_attempts"] += attempts
        
        if success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
        
        stats["average_attempts"] = stats["total_attempts"] / stats["total_calls"]
        stats["last_updated"] = datetime.now().isoformat()
    
    def get_retry_statistics(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """获取重试统计信息"""
        if model_id:
            return self.retry_statistics.get(model_id, {})
        return self.retry_statistics.copy()
    
    def update_retry_strategy(self, error_type: ErrorType, strategy: RetryStrategy):
        """更新重试策略"""
        self.retry_strategies[error_type] = strategy
        logger.info(f"更新重试策略: {error_type.value}")
    
    def add_error_classifier(self, classifier: Callable[[Exception], Optional[ErrorType]]):
        """添加自定义错误分类器"""
        self.error_classifiers.append(classifier)
    
    def get_strategy_effectiveness(self) -> Dict[str, Dict[str, float]]:
        """获取策略有效性分析"""
        effectiveness = {}
        
        for error_type, strategy in self.retry_strategies.items():
            # 计算该策略的成功率和平均重试次数
            relevant_stats = []
            for model_id, stats in self.retry_statistics.items():
                if stats["total_calls"] > 0:
                    relevant_stats.append(stats)
            
            if relevant_stats:
                total_calls = sum(s["total_calls"] for s in relevant_stats)
                successful_calls = sum(s["successful_calls"] for s in relevant_stats)
                avg_attempts = sum(s["average_attempts"] * s["total_calls"] for s in relevant_stats) / total_calls
                
                effectiveness[error_type.value] = {
                    "success_rate": successful_calls / total_calls if total_calls > 0 else 0.0,
                    "average_attempts": avg_attempts,
                    "total_calls": total_calls,
                    "strategy_config": {
                        "type": strategy.strategy_type,
                        "base_delay": strategy.base_delay,
                        "max_delay": strategy.max_delay,
                        "max_retries": strategy.max_retries
                    }
                }
        
        return effectiveness
    
    def optimize_strategies(self):
        """基于统计数据优化重试策略"""
        effectiveness = self.get_strategy_effectiveness()
        
        for error_type_str, data in effectiveness.items():
            try:
                error_type = ErrorType(error_type_str)
                
                # 如果成功率过低，增加重试次数
                if data["success_rate"] < 0.5 and data["total_calls"] > 10:
                    current_strategy = self.retry_strategies[error_type]
                    if current_strategy.max_retries < 5:
                        new_strategy = RetryStrategy(
                            strategy_type=current_strategy.strategy_type,
                            base_delay=current_strategy.base_delay,
                            max_delay=current_strategy.max_delay,
                            max_retries=min(current_strategy.max_retries + 1, 5),
                            backoff_multiplier=current_strategy.backoff_multiplier,
                            jitter=current_strategy.jitter
                        )
                        self.update_retry_strategy(error_type, new_strategy)
                        logger.info(f"优化策略 {error_type.value}: 增加最大重试次数到 {new_strategy.max_retries}")
                
                # 如果平均重试次数过高，调整延迟策略
                elif data["average_attempts"] > 3.0 and data["total_calls"] > 10:
                    current_strategy = self.retry_strategies[error_type]
                    if current_strategy.base_delay < 5.0:
                        new_strategy = RetryStrategy(
                            strategy_type=current_strategy.strategy_type,
                            base_delay=min(current_strategy.base_delay * 1.5, 5.0),
                            max_delay=current_strategy.max_delay,
                            max_retries=current_strategy.max_retries,
                            backoff_multiplier=current_strategy.backoff_multiplier,
                            jitter=current_strategy.jitter
                        )
                        self.update_retry_strategy(error_type, new_strategy)
                        logger.info(f"优化策略 {error_type.value}: 增加基础延迟到 {new_strategy.base_delay}")
                        
            except ValueError:
                continue  # 跳过无效的错误类型
    
    def reset_statistics(self):
        """重置统计信息"""
        self.retry_statistics.clear()
        logger.info("重试统计信息已重置")
    
    def export_configuration(self) -> Dict[str, Any]:
        """导出配置"""
        return {
            "retry_strategies": {
                error_type.value: {
                    "strategy_type": strategy.strategy_type,
                    "base_delay": strategy.base_delay,
                    "max_delay": strategy.max_delay,
                    "max_retries": strategy.max_retries,
                    "backoff_multiplier": strategy.backoff_multiplier,
                    "jitter": strategy.jitter
                }
                for error_type, strategy in self.retry_strategies.items()
            },
            "statistics": self.retry_statistics
        }
    
    def import_configuration(self, config: Dict[str, Any]):
        """导入配置"""
        try:
            # 导入重试策略
            if "retry_strategies" in config:
                for error_type_str, strategy_config in config["retry_strategies"].items():
                    try:
                        error_type = ErrorType(error_type_str)
                        strategy = RetryStrategy(**strategy_config)
                        self.retry_strategies[error_type] = strategy
                    except (ValueError, TypeError) as e:
                        logger.warning(f"导入策略失败 {error_type_str}: {str(e)}")
            
            # 导入统计信息
            if "statistics" in config:
                self.retry_statistics.update(config["statistics"])
            
            logger.info("配置导入成功")
            
        except Exception as e:
            logger.error(f"配置导入失败: {str(e)}")
            raise