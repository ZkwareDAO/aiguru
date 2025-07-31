"""
智能缓存模块

提供多级缓存策略和相似性匹配功能。
"""

from .intelligent_cache import IntelligentCache
from .cache_policies import TTLCachePolicy, LRUCachePolicy, SizeLimitedCachePolicy

__all__ = [
    "IntelligentCache",
    "TTLCachePolicy",
    "LRUCachePolicy",
    "SizeLimitedCachePolicy"
]