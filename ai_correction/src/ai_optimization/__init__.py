"""
AI功能提示词优化与调用功能完善模块

本模块提供智能提示词管理、多模态内容处理、API调用管理和质量控制功能。
"""

__version__ = "1.0.0"
__author__ = "AI Optimization Team"

# 导出主要组件
from .prompt_engine import PromptEngine
from .api_manager import APIClient
from .quality_control import ConsistencyChecker
from .content_processor import ContentRecognizer

__all__ = [
    "PromptEngine",
    "APIClient", 
    "ConsistencyChecker",
    "ContentRecognizer"
]