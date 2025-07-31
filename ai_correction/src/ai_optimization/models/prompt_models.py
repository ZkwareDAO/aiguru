"""
提示词相关数据模型

定义提示词模板、生成的提示词和相关参数的数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
import hashlib
from enum import Enum


class PromptLayer(Enum):
    """提示词分层枚举"""
    SYSTEM = "system"      # 系统层：定义AI角色和基本行为
    TASK = "task"          # 任务层：定义具体任务和目标
    CONTEXT = "context"    # 上下文层：提供具体的上下文信息
    FORMAT = "format"      # 格式层：定义输出格式和约束
    QUALITY = "quality"    # 质量层：定义质量控制和验证规则


@dataclass
class PromptParameter:
    """提示词参数"""
    name: str
    type: str
    default_value: Any
    description: str
    validation_rules: List[str] = field(default_factory=list)
    is_required: bool = True
    
    def validate(self, value: Any) -> bool:
        """验证参数值"""
        if self.is_required and value is None:
            return False
            
        # 基本类型检查
        if self.type == "str" and not isinstance(value, str):
            return False
        elif self.type == "int" and not isinstance(value, int):
            return False
        elif self.type == "float" and not isinstance(value, (int, float)):
            return False
        elif self.type == "bool" and not isinstance(value, bool):
            return False
        elif self.type == "list" and not isinstance(value, list):
            return False
        elif self.type == "dict" and not isinstance(value, dict):
            return False
            
        # 自定义验证规则
        for rule in self.validation_rules:
            if not self._apply_validation_rule(rule, value):
                return False
                
        return True
    
    def _apply_validation_rule(self, rule: str, value: Any) -> bool:
        """应用验证规则"""
        try:
            if rule.startswith("min_length:"):
                min_len = int(rule.split(":")[1])
                return len(str(value)) >= min_len
            elif rule.startswith("max_length:"):
                max_len = int(rule.split(":")[1])
                return len(str(value)) <= max_len
            elif rule.startswith("min_value:"):
                min_val = float(rule.split(":")[1])
                return float(value) >= min_val
            elif rule.startswith("max_value:"):
                max_val = float(rule.split(":")[1])
                return float(value) <= max_val
            elif rule.startswith("regex:"):
                import re
                pattern = rule.split(":", 1)[1]
                return bool(re.match(pattern, str(value)))
            else:
                return True
        except Exception:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.type,
            "default_value": self.default_value,
            "description": self.description,
            "validation_rules": self.validation_rules,
            "is_required": self.is_required
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptParameter':
        """从字典创建实例"""
        return cls(
            name=data["name"],
            type=data["type"],
            default_value=data["default_value"],
            description=data["description"],
            validation_rules=data.get("validation_rules", []),
            is_required=data.get("is_required", True)
        )


@dataclass
class PerformanceMetrics:
    """性能指标"""
    avg_response_time: float = 0.0
    success_rate: float = 0.0
    quality_score: float = 0.0
    usage_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update(self, response_time: float, success: bool, quality: float):
        """更新性能指标"""
        self.usage_count += 1
        
        # 更新平均响应时间
        self.avg_response_time = (
            (self.avg_response_time * (self.usage_count - 1) + response_time) 
            / self.usage_count
        )
        
        # 更新成功率
        current_success_count = self.success_rate * (self.usage_count - 1)
        if success:
            current_success_count += 1
        self.success_rate = current_success_count / self.usage_count
        
        # 更新质量分数
        self.quality_score = (
            (self.quality_score * (self.usage_count - 1) + quality) 
            / self.usage_count
        )
        
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "avg_response_time": self.avg_response_time,
            "success_rate": self.success_rate,
            "quality_score": self.quality_score,
            "usage_count": self.usage_count,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class PromptTemplate:
    """提示词模板"""
    id: str
    name: str
    category: str
    layers: Dict[str, str]  # 分层提示词内容
    parameters: List[PromptParameter] = field(default_factory=list)
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        content = f"{self.name}_{self.category}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, List[str]]:
        """验证参数"""
        errors = {}
        
        for param in self.parameters:
            value = params.get(param.name)
            
            if not param.validate(value):
                if param.name not in errors:
                    errors[param.name] = []
                errors[param.name].append(f"参数 {param.name} 验证失败")
        
        return errors
    
    def get_layer_content(self, layer: PromptLayer) -> Optional[str]:
        """获取指定层的内容"""
        return self.layers.get(layer.value)
    
    def set_layer_content(self, layer: PromptLayer, content: str):
        """设置指定层的内容"""
        self.layers[layer.value] = content
        self.updated_at = datetime.now()
    
    def clone(self, new_name: str = None, new_version: str = None) -> 'PromptTemplate':
        """克隆模板"""
        cloned = PromptTemplate(
            id="",  # 将自动生成新ID
            name=new_name or f"{self.name}_copy",
            category=self.category,
            layers=self.layers.copy(),
            parameters=[param for param in self.parameters],
            version=new_version or self.version,
            tags=self.tags.copy()
        )
        return cloned
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "layers": self.layers,
            "parameters": [param.to_dict() for param in self.parameters],
            "performance_metrics": self.performance_metrics.to_dict(),
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptTemplate':
        """从字典创建实例"""
        parameters = [
            PromptParameter.from_dict(param_data) 
            for param_data in data.get("parameters", [])
        ]
        
        metrics_data = data.get("performance_metrics", {})
        performance_metrics = PerformanceMetrics(
            avg_response_time=metrics_data.get("avg_response_time", 0.0),
            success_rate=metrics_data.get("success_rate", 0.0),
            quality_score=metrics_data.get("quality_score", 0.0),
            usage_count=metrics_data.get("usage_count", 0),
            last_updated=datetime.fromisoformat(
                metrics_data.get("last_updated", datetime.now().isoformat())
            )
        )
        
        return cls(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            layers=data["layers"],
            parameters=parameters,
            performance_metrics=performance_metrics,
            version=data.get("version", "1.0.0"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            is_active=data.get("is_active", True),
            tags=data.get("tags", [])
        )


@dataclass
class GeneratedPrompt:
    """生成的提示词"""
    template_id: str
    content: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    context_hash: str = ""
    generated_at: datetime = field(default_factory=datetime.now)
    quality_score: Optional[float] = None
    usage_stats: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.context_hash:
            self.context_hash = self._generate_context_hash()
    
    def _generate_context_hash(self) -> str:
        """生成上下文哈希"""
        context_str = json.dumps(self.parameters, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(context_str.encode()).hexdigest()
    
    def get_token_count(self) -> int:
        """估算token数量"""
        # 简单估算：中文字符按1.5个token计算，英文单词按1个token计算
        chinese_chars = len([c for c in self.content if '\u4e00' <= c <= '\u9fff'])
        english_words = len(self.content.replace('\n', ' ').split()) - chinese_chars
        return int(chinese_chars * 1.5 + english_words)
    
    def update_quality_score(self, score: float):
        """更新质量分数"""
        self.quality_score = score
        if "quality_history" not in self.usage_stats:
            self.usage_stats["quality_history"] = []
        self.usage_stats["quality_history"].append({
            "score": score,
            "timestamp": datetime.now().isoformat()
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "template_id": self.template_id,
            "content": self.content,
            "parameters": self.parameters,
            "context_hash": self.context_hash,
            "generated_at": self.generated_at.isoformat(),
            "quality_score": self.quality_score,
            "usage_stats": self.usage_stats
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GeneratedPrompt':
        """从字典创建实例"""
        return cls(
            template_id=data["template_id"],
            content=data["content"],
            parameters=data.get("parameters", {}),
            context_hash=data.get("context_hash", ""),
            generated_at=datetime.fromisoformat(data["generated_at"]),
            quality_score=data.get("quality_score"),
            usage_stats=data.get("usage_stats", {})
        )


# 导出所有模型类
__all__ = [
    "PromptLayer",
    "PromptParameter", 
    "PerformanceMetrics",
    "PromptTemplate",
    "GeneratedPrompt"
]