"""
AI优化数据模型

定义提示词、API调用、质量控制等相关的数据模型。
"""

from .prompt_models import PromptTemplate, GeneratedPrompt, PromptParameter
from .api_models import ModelConfig, APIResponse, APICallContext
from .quality_models import QualityRule, QualityReport, QualityIssue

__all__ = [
    # 提示词模型
    "PromptTemplate",
    "GeneratedPrompt", 
    "PromptParameter",
    
    # API模型
    "ModelConfig",
    "APIResponse",
    "APICallContext",
    
    # 质量模型
    "QualityRule",
    "QualityReport",
    "QualityIssue"
]