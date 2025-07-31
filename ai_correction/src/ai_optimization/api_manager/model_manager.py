"""
多模型管理器

实现模型配置管理、状态监控、智能选择和负载均衡功能。
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import random

from ..models.api_models import ModelConfig, ModelStatus, ModelProvider, TaskType, UsageStats
from ..config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

@dataclass
class ModelPerformanceMetrics:
    """模型性能指标"""
    model_id: str
    success_rate: float = 0.0
    average_response_time: float = 0.0
    average_quality_score: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    total_cost: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_metrics(self, response_time: float, quality_score: float, 
                      cost: float, success: bool):
        """更新性能指标"""
        self.total_requests += 1
        if not success:
            self.failed_requests += 1
        
        # 更新成功率
        self.success_rate = (self.total_requests - self.failed_requests) / self.total_requests
        
        # 更新平均响应时间（指数移动平均）
        alpha = 0.1  # 平滑因子
        if self.average_response_time == 0:
            self.average_response_time = response_time
        else:
            self.average_response_time = (1 - alpha) * self.average_response_time + alpha * response_time
        
        # 更新平均质量分数
        if success and quality_score > 0:
            if self.average_quality_score == 0:
                self.average_quality_score = quality_score
            else:
                self.average_quality_score = (1 - alpha) * self.average_quality_score + alpha * quality_score
        
        # 更新总成本
        self.total_cost += cost
        self.last_updated = datetime.now()
    
    def get_efficiency_score(self) -> float:
        """计算效率分数（质量/成本/时间的综合指标）"""
        if self.total_cost == 0 or self.average_response_time == 0:
            return 0.0
        
        # 归一化各项指标
        quality_factor = min(self.average_quality_score, 1.0)
        time_factor = max(0.1, min(1.0, 10.0 / self.average_response_time))  # 10秒内为满分
        cost_factor = max(0.1, min(1.0, 0.01 / (self.total_cost / max(self.total_requests, 1))))  # 成本越低越好
        success_factor = self.success_rate
        
        # 综合评分
        return (quality_factor * 0.3 + time_factor * 0.2 + cost_factor * 0.2 + success_factor * 0.3)

class LoadBalancingStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_RANDOM = "weighted_random"
    LEAST_LOADED = "least_loaded"
    PERFORMANCE_BASED = "performance_based"
    COST_OPTIMIZED = "cost_optimized"

class ModelManager:
    """多模型管理器"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.models: Dict[str, ModelConfig] = {}
        self.performance_metrics: Dict[str, ModelPerformanceMetrics] = {}
        self.load_balancing_strategy = LoadBalancingStrategy.PERFORMANCE_BASED
        self.round_robin_index = 0
        self._health_check_interval = 300  # 5分钟
        self._health_check_task: Optional[asyncio.Task] = None
        self._model_locks: Dict[str, asyncio.Semaphore] = {}
        
        # 加载模型配置
        self._load_models_from_config()
        
        # 启动健康检查
        self._start_health_check()
    
    def _load_models_from_config(self):
        """从配置文件加载模型"""
        try:
            models_config = self.config_manager.get('models', {})
            
            for model_id, model_data in models_config.items():
                try:
                    # 确保必需字段存在
                    if not all(key in model_data for key in ['name', 'provider', 'endpoint']):
                        logger.warning(f"模型配置不完整，跳过: {model_id}")
                        continue
                    
                    # 处理支持的任务类型
                    supported_tasks = []
                    for task in model_data.get('supported_tasks', []):
                        try:
                            supported_tasks.append(TaskType(task))
                        except ValueError:
                            logger.warning(f"未知任务类型: {task}")
                    
                    # 创建模型配置
                    model_config = ModelConfig(
                        id=model_id,
                        name=model_data['name'],
                        provider=ModelProvider(model_data['provider']),
                        endpoint=model_data['endpoint'],
                        supported_tasks=supported_tasks,
                        max_content_size=model_data.get('max_content_size', 100000),
                        max_tokens=model_data.get('max_tokens', 4096),
                        cost_per_token=model_data.get('cost_per_token', 0.0),
                        performance_rating=model_data.get('performance_rating', 0.0),
                        is_available=model_data.get('is_available', True),
                        api_key=model_data.get('api_key') or self.config_manager.get('api_keys.default'),
                        additional_params=model_data.get('additional_params', {}),
                        rate_limits=model_data.get('rate_limits', {})
                    )
                    
                    self.models[model_id] = model_config
                    self.performance_metrics[model_id] = ModelPerformanceMetrics(model_id)
                    self._model_locks[model_id] = asyncio.Semaphore(
                        model_data.get('max_concurrent_requests', 5)
                    )
                    
                    logger.info(f"加载模型配置: {model_id} ({model_config.name})")
                    
                except Exception as e:
                    logger.error(f"加载模型配置失败 {model_id}: {str(e)}")
            
            if not self.models:
                logger.warning("没有加载到任何模型配置，使用默认配置")
                self._create_default_models()
                
        except Exception as e:
            logger.error(f"加载模型配置失败: {str(e)}")
            self._create_default_models()
    
    def _create_default_models(self):
        """创建默认模型配置"""
        default_models = [
            {
                "id": "gemini-2.5-flash",
                "name": "Gemini 2.5 Flash",
                "provider": "google",
                "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                "supported_tasks": ["grading", "analysis", "summary"],
                "max_tokens": 8192,
                "cost_per_token": 0.000001
            },
            {
                "id": "claude-3-haiku",
                "name": "Claude 3 Haiku",
                "provider": "anthropic",
                "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                "supported_tasks": ["grading", "analysis"],
                "max_tokens": 4096,
                "cost_per_token": 0.000002
            }
        ]
        
        for model_data in default_models:
            model_config = ModelConfig(
                id=model_data["id"],
                name=model_data["name"],
                provider=ModelProvider(model_data["provider"]),
                endpoint=model_data["endpoint"],
                supported_tasks=[TaskType(task) for task in model_data["supported_tasks"]],
                max_tokens=model_data["max_tokens"],
                cost_per_token=model_data["cost_per_token"],
                api_key=self.config_manager.get('api_keys.default', '')
            )
            
            self.models[model_data["id"]] = model_config
            self.performance_metrics[model_data["id"]] = ModelPerformanceMetrics(model_data["id"])
            self._model_locks[model_data["id"]] = asyncio.Semaphore(5)
    
    def get_available_models(self, task_type: Optional[TaskType] = None) -> List[ModelConfig]:
        """获取可用模型列表"""
        available_models = []
        
        for model in self.models.values():
            if not model.is_available or model.status != ModelStatus.AVAILABLE:
                continue
            
            if task_type and not model.supports_task(task_type):
                continue
            
            available_models.append(model)
        
        return available_models
    
    def select_optimal_model(self, 
                           task_type: TaskType,
                           content_size: int = 0,
                           priority: str = 'balanced',
                           exclude_models: List[str] = None) -> Optional[ModelConfig]:
        """
        选择最优模型
        
        Args:
            task_type: 任务类型
            content_size: 内容大小
            priority: 优先级策略 ('speed', 'quality', 'cost', 'balanced')
            exclude_models: 排除的模型ID列表
            
        Returns:
            最优模型配置
        """
        exclude_models = exclude_models or []
        available_models = [
            model for model in self.get_available_models(task_type)
            if model.id not in exclude_models and model.can_handle_content_size(content_size)
        ]
        
        if not available_models:
            logger.warning(f"没有可用模型支持任务类型: {task_type}")
            return None
        
        # 根据负载均衡策略选择模型
        if self.load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._select_round_robin(available_models)
        elif self.load_balancing_strategy == LoadBalancingStrategy.WEIGHTED_RANDOM:
            return self._select_weighted_random(available_models)
        elif self.load_balancing_strategy == LoadBalancingStrategy.LEAST_LOADED:
            return self._select_least_loaded(available_models)
        elif self.load_balancing_strategy == LoadBalancingStrategy.PERFORMANCE_BASED:
            return self._select_performance_based(available_models, priority)
        elif self.load_balancing_strategy == LoadBalancingStrategy.COST_OPTIMIZED:
            return self._select_cost_optimized(available_models)
        else:
            return available_models[0]  # 默认返回第一个
    
    def _select_round_robin(self, models: List[ModelConfig]) -> ModelConfig:
        """轮询选择"""
        if not models:
            return None
        
        selected = models[self.round_robin_index % len(models)]
        self.round_robin_index += 1
        return selected
    
    def _select_weighted_random(self, models: List[ModelConfig]) -> ModelConfig:
        """加权随机选择"""
        if not models:
            return None
        
        # 基于性能评分计算权重
        weights = []
        for model in models:
            metrics = self.performance_metrics.get(model.id)
            if metrics:
                weight = max(0.1, metrics.get_efficiency_score())
            else:
                weight = model.performance_rating or 0.5
            weights.append(weight)
        
        # 加权随机选择
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(models)
        
        rand_val = random.uniform(0, total_weight)
        current_weight = 0
        
        for i, weight in enumerate(weights):
            current_weight += weight
            if rand_val <= current_weight:
                return models[i]
        
        return models[-1]  # 备用
    
    def _select_least_loaded(self, models: List[ModelConfig]) -> ModelConfig:
        """选择负载最低的模型"""
        if not models:
            return None
        
        # 简单实现：选择当前请求数最少的模型
        least_loaded = models[0]
        min_load = self._get_current_load(least_loaded.id)
        
        for model in models[1:]:
            load = self._get_current_load(model.id)
            if load < min_load:
                min_load = load
                least_loaded = model
        
        return least_loaded
    
    def _select_performance_based(self, models: List[ModelConfig], priority: str) -> ModelConfig:
        """基于性能选择模型"""
        if not models:
            return None
        
        scored_models = []
        
        for model in models:
            metrics = self.performance_metrics.get(model.id)
            
            if priority == 'speed':
                # 优先考虑响应速度
                score = self._calculate_speed_score(model, metrics)
            elif priority == 'quality':
                # 优先考虑质量
                score = self._calculate_quality_score(model, metrics)
            elif priority == 'cost':
                # 优先考虑成本
                score = self._calculate_cost_score(model, metrics)
            else:  # balanced
                # 综合评分
                score = self._calculate_balanced_score(model, metrics)
            
            scored_models.append((model, score))
        
        # 按分数排序，选择最高分的模型
        scored_models.sort(key=lambda x: x[1], reverse=True)
        return scored_models[0][0]
    
    def _select_cost_optimized(self, models: List[ModelConfig]) -> ModelConfig:
        """选择成本最优的模型"""
        if not models:
            return None
        
        # 选择成本最低且质量可接受的模型
        cost_models = []
        for model in models:
            metrics = self.performance_metrics.get(model.id)
            quality_threshold = 0.6  # 最低质量要求
            
            if metrics and metrics.average_quality_score < quality_threshold:
                continue  # 质量不达标
            
            cost_models.append((model, model.cost_per_token))
        
        if not cost_models:
            return models[0]  # 如果没有符合质量要求的，返回第一个
        
        # 按成本排序，选择最便宜的
        cost_models.sort(key=lambda x: x[1])
        return cost_models[0][0]
    
    def _calculate_speed_score(self, model: ModelConfig, metrics: Optional[ModelPerformanceMetrics]) -> float:
        """计算速度分数"""
        if not metrics or metrics.average_response_time == 0:
            return model.performance_rating or 0.5
        
        # 响应时间越短分数越高
        max_time = 60.0  # 最大可接受时间
        speed_score = max(0.0, (max_time - metrics.average_response_time) / max_time)
        success_bonus = metrics.success_rate * 0.3
        
        return min(1.0, speed_score + success_bonus)
    
    def _calculate_quality_score(self, model: ModelConfig, metrics: Optional[ModelPerformanceMetrics]) -> float:
        """计算质量分数"""
        if not metrics:
            return model.performance_rating or 0.5
        
        quality_score = metrics.average_quality_score * 0.7
        success_bonus = metrics.success_rate * 0.3
        
        return min(1.0, quality_score + success_bonus)
    
    def _calculate_cost_score(self, model: ModelConfig, metrics: Optional[ModelPerformanceMetrics]) -> float:
        """计算成本分数"""
        # 成本越低分数越高
        max_cost = 0.01  # 最大可接受成本
        cost_score = max(0.0, (max_cost - model.cost_per_token) / max_cost)
        
        if metrics:
            success_bonus = metrics.success_rate * 0.2
            cost_score += success_bonus
        
        return min(1.0, cost_score)
    
    def _calculate_balanced_score(self, model: ModelConfig, metrics: Optional[ModelPerformanceMetrics]) -> float:
        """计算综合平衡分数"""
        if not metrics:
            return model.performance_rating or 0.5
        
        return metrics.get_efficiency_score()
    
    def _get_current_load(self, model_id: str) -> int:
        """获取模型当前负载（简化实现）"""
        semaphore = self._model_locks.get(model_id)
        if semaphore:
            return semaphore._value  # 可用许可数，越少表示负载越高
        return 0
    
    def update_model_performance(self, model_id: str, response_time: float, 
                               quality_score: float, cost: float, success: bool):
        """更新模型性能指标"""
        if model_id in self.performance_metrics:
            self.performance_metrics[model_id].update_metrics(
                response_time, quality_score, cost, success
            )
            
            # 如果成功率过低，暂时禁用模型
            metrics = self.performance_metrics[model_id]
            if metrics.total_requests >= 10 and metrics.success_rate < 0.3:
                self.set_model_status(model_id, ModelStatus.ERROR, "成功率过低")
    
    def set_model_status(self, model_id: str, status: ModelStatus, reason: str = ""):
        """设置模型状态"""
        if model_id in self.models:
            self.models[model_id].update_status(status, reason)
            logger.info(f"模型状态更新: {model_id} -> {status.value} ({reason})")
    
    def get_model_status(self, model_id: str) -> Optional[ModelStatus]:
        """获取模型状态"""
        model = self.models.get(model_id)
        return model.status if model else None
    
    def get_model_metrics(self, model_id: str) -> Optional[ModelPerformanceMetrics]:
        """获取模型性能指标"""
        return self.performance_metrics.get(model_id)
    
    def get_all_model_metrics(self) -> Dict[str, ModelPerformanceMetrics]:
        """获取所有模型的性能指标"""
        return self.performance_metrics.copy()
    
    def set_load_balancing_strategy(self, strategy: LoadBalancingStrategy):
        """设置负载均衡策略"""
        self.load_balancing_strategy = strategy
        logger.info(f"负载均衡策略更新为: {strategy.value}")
    
    async def acquire_model_lock(self, model_id: str) -> bool:
        """获取模型锁（用于并发控制）"""
        semaphore = self._model_locks.get(model_id)
        if semaphore:
            try:
                await semaphore.acquire()
                return True
            except Exception as e:
                logger.error(f"获取模型锁失败 {model_id}: {str(e)}")
                return False
        return False
    
    def release_model_lock(self, model_id: str):
        """释放模型锁"""
        semaphore = self._model_locks.get(model_id)
        if semaphore:
            try:
                semaphore.release()
            except Exception as e:
                logger.error(f"释放模型锁失败 {model_id}: {str(e)}")
    
    def _start_health_check(self):
        """启动健康检查任务"""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_worker())
    
    async def _health_check_worker(self):
        """健康检查工作任务"""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查异常: {str(e)}")
    
    async def _perform_health_check(self):
        """执行健康检查"""
        logger.debug("开始模型健康检查")
        
        for model_id, model in self.models.items():
            try:
                # 检查模型是否长时间无响应
                metrics = self.performance_metrics.get(model_id)
                if metrics:
                    time_since_update = (datetime.now() - metrics.last_updated).total_seconds()
                    
                    # 如果超过1小时没有更新且成功率低，标记为不可用
                    if time_since_update > 3600 and metrics.success_rate < 0.5:
                        self.set_model_status(model_id, ModelStatus.UNAVAILABLE, "长时间无响应")
                    
                    # 如果成功率恢复，重新启用
                    elif model.status == ModelStatus.ERROR and metrics.success_rate > 0.7:
                        self.set_model_status(model_id, ModelStatus.AVAILABLE, "性能恢复")
                
            except Exception as e:
                logger.error(f"健康检查模型 {model_id} 失败: {str(e)}")
    
    def stop_health_check(self):
        """停止健康检查"""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
    
    def get_model_summary(self) -> Dict[str, Any]:
        """获取模型管理器摘要信息"""
        total_models = len(self.models)
        available_models = len(self.get_available_models())
        
        return {
            "total_models": total_models,
            "available_models": available_models,
            "load_balancing_strategy": self.load_balancing_strategy.value,
            "models": {
                model_id: {
                    "name": model.name,
                    "provider": model.provider.value,
                    "status": model.status.value,
                    "is_available": model.is_available,
                    "performance": self.performance_metrics[model_id].__dict__ if model_id in self.performance_metrics else None
                }
                for model_id, model in self.models.items()
            }
        }
    
    def __del__(self):
        """析构函数"""
        self.stop_health_check()