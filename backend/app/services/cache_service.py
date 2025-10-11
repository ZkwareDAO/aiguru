"""Cache Service - 智能缓存服务."""

import json
import hashlib
import logging
from typing import Optional, Dict
from uuid import UUID

import redis.asyncio as redis

from app.core.config import settings
from app.agents.state import GradingState

logger = logging.getLogger(__name__)


class CacheService:
    """智能缓存服务
    
    功能:
    - 缓存批改结果
    - 基于内容相似度查找缓存
    - 自动过期管理
    
    成本优化:
    - 缓存命中率30%时,可节省30%成本
    """
    
    def __init__(self):
        """初始化缓存服务"""
        self.redis_client: Optional[redis.Redis] = None
        self.similarity_threshold = settings.CACHE_SIMILARITY_THRESHOLD
        self.ttl = 7 * 24 * 3600  # 7天
        self.enabled = settings.ENABLE_SMART_CACHE
        
        logger.info(
            f"CacheService initialized: enabled={self.enabled}, "
            f"threshold={self.similarity_threshold}"
        )
    
    async def _get_redis(self) -> redis.Redis:
        """获取Redis连接"""
        if self.redis_client is None:
            if settings.REDIS_URL:
                self.redis_client = await redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
            else:
                logger.warning("Redis URL not configured, cache disabled")
                self.enabled = False
        
        return self.redis_client
    
    async def get_similar(self, extracted_text: str) -> Optional[Dict]:
        """获取相似的缓存结果
        
        Args:
            extracted_text: 提取的文本内容
            
        Returns:
            缓存的批改结果,如果没有找到则返回None
        """
        if not self.enabled:
            return None
        
        try:
            # 计算内容哈希
            content_hash = self._compute_hash(extracted_text)
            
            # 查找缓存
            cache_key = f"grading_cache:{content_hash}"
            redis_client = await self._get_redis()
            
            if redis_client:
                cached_data = await redis_client.get(cache_key)
                
                if cached_data:
                    logger.info(f"Cache hit for hash: {content_hash[:16]}...")
                    result = json.loads(cached_data)
                    
                    # 添加缓存标记
                    result["from_cache"] = True
                    
                    return result
            
            logger.debug(f"Cache miss for hash: {content_hash[:16]}...")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cache: {e}")
            return None
    
    async def store(self, state: GradingState) -> None:
        """存储批改结果到缓存
        
        Args:
            state: 批改状态
        """
        if not self.enabled:
            return
        
        try:
            # 计算内容哈希
            content_hash = self._compute_hash(state["extracted_text"])
            
            # 准备缓存数据
            cache_data = {
                "score": state["score"],
                "confidence": state["confidence"],
                "errors": state["errors"],
                "feedback_text": state["feedback_text"],
                "suggestions": state["suggestions"],
                "knowledge_points": state["knowledge_points"],
                "grading_mode": state["grading_mode"],
                "cached_at": state["processing_end_time"].isoformat() if state.get("processing_end_time") else None,
            }
            
            # 存储到Redis
            cache_key = f"grading_cache:{content_hash}"
            redis_client = await self._get_redis()
            
            if redis_client:
                await redis_client.setex(
                    cache_key,
                    self.ttl,
                    json.dumps(cache_data, ensure_ascii=False)
                )
                
                logger.info(f"Cached result for hash: {content_hash[:16]}...")
            
        except Exception as e:
            logger.error(f"Failed to store cache: {e}")
    
    def _compute_hash(self, text: str) -> str:
        """计算文本哈希
        
        使用MD5快速哈希,用于缓存键
        
        Args:
            text: 文本内容
            
        Returns:
            哈希值
        """
        # 标准化文本 (去除多余空白)
        normalized_text = " ".join(text.split())
        
        # 计算MD5哈希
        return hashlib.md5(normalized_text.encode('utf-8')).hexdigest()
    
    async def get_cache_stats(self) -> Dict:
        """获取缓存统计信息
        
        Returns:
            缓存统计
        """
        try:
            redis_client = await self._get_redis()
            
            if redis_client:
                # 获取所有缓存键
                keys = await redis_client.keys("grading_cache:*")
                
                return {
                    "enabled": self.enabled,
                    "total_cached": len(keys),
                    "ttl_seconds": self.ttl,
                    "similarity_threshold": self.similarity_threshold,
                }
            
            return {
                "enabled": False,
                "error": "Redis not available"
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "enabled": self.enabled,
                "error": str(e)
            }
    
    async def clear_cache(self, pattern: str = "grading_cache:*") -> int:
        """清除缓存
        
        Args:
            pattern: 缓存键模式
            
        Returns:
            清除的键数量
        """
        try:
            redis_client = await self._get_redis()
            
            if redis_client:
                keys = await redis_client.keys(pattern)
                
                if keys:
                    deleted = await redis_client.delete(*keys)
                    logger.info(f"Cleared {deleted} cache entries")
                    return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0
    
    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")

