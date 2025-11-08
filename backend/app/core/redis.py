"""Redis connection and cache management."""

import json
import logging
from typing import Any, Optional, Union

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis connection and cache manager."""
    
    def __init__(self):
        self._redis: Optional[Redis] = None
        self._pool: Optional[ConnectionPool] = None
        self.settings = get_settings()
    
    def create_connection_pool(self) -> ConnectionPool:
        """Create Redis connection pool."""
        if not self.settings.REDIS_URL:
            raise ValueError("REDIS_URL is not configured")
        
        pool = ConnectionPool.from_url(
            self.settings.REDIS_URL,
            max_connections=20,
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30,
        )
        
        return pool
    
    def get_redis(self) -> Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            if self._pool is None:
                self._pool = self.create_connection_pool()
            
            self._redis = Redis(
                connection_pool=self._pool,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        
        return self._redis
    
    async def close(self) -> None:
        """Close Redis connections."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        
        logger.info("Redis connections closed")
    
    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            redis_client = self.get_redis()
            await redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    # Cache operations
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        try:
            redis_client = self.get_redis()
            return await redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Union[str, int, float, dict, list],
        expire: Optional[int] = None,
    ) -> bool:
        """Set value in Redis with optional expiration."""
        try:
            redis_client = self.get_redis()
            
            # Convert complex types to JSON
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            result = await redis_client.set(key, value, ex=expire)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        try:
            redis_client = self.get_redis()
            result = await redis_client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            redis_client = self.get_redis()
            result = await redis_client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for key."""
        try:
            redis_client = self.get_redis()
            result = await redis_client.expire(key, seconds)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        try:
            redis_client = self.get_redis()
            return await redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error for key {key}: {e}")
            return -1
    
    # Hash operations
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get field value from hash."""
        try:
            redis_client = self.get_redis()
            return await redis_client.hget(name, key)
        except Exception as e:
            logger.error(f"Redis HGET error for hash {name}, key {key}: {e}")
            return None
    
    async def hset(self, name: str, key: str, value: Any) -> bool:
        """Set field value in hash."""
        try:
            redis_client = self.get_redis()
            
            # Convert complex types to JSON
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            result = await redis_client.hset(name, key, value)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis HSET error for hash {name}, key {key}: {e}")
            return False
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete fields from hash."""
        try:
            redis_client = self.get_redis()
            return await redis_client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Redis HDEL error for hash {name}: {e}")
            return 0
    
    async def hgetall(self, name: str) -> dict:
        """Get all fields and values from hash."""
        try:
            redis_client = self.get_redis()
            return await redis_client.hgetall(name)
        except Exception as e:
            logger.error(f"Redis HGETALL error for hash {name}: {e}")
            return {}
    
    # List operations
    async def lpush(self, name: str, *values: Any) -> int:
        """Push values to the left of list."""
        try:
            redis_client = self.get_redis()
            # Convert complex types to JSON
            json_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    json_values.append(json.dumps(value))
                else:
                    json_values.append(value)
            
            return await redis_client.lpush(name, *json_values)
        except Exception as e:
            logger.error(f"Redis LPUSH error for list {name}: {e}")
            return 0
    
    async def rpop(self, name: str) -> Optional[str]:
        """Pop value from the right of list."""
        try:
            redis_client = self.get_redis()
            return await redis_client.rpop(name)
        except Exception as e:
            logger.error(f"Redis RPOP error for list {name}: {e}")
            return None
    
    async def llen(self, name: str) -> int:
        """Get length of list."""
        try:
            redis_client = self.get_redis()
            return await redis_client.llen(name)
        except Exception as e:
            logger.error(f"Redis LLEN error for list {name}: {e}")
            return 0
    
    # Set operations
    async def sadd(self, name: str, *values: Any) -> int:
        """Add values to set."""
        try:
            redis_client = self.get_redis()
            # Convert complex types to JSON
            json_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    json_values.append(json.dumps(value))
                else:
                    json_values.append(value)
            
            return await redis_client.sadd(name, *json_values)
        except Exception as e:
            logger.error(f"Redis SADD error for set {name}: {e}")
            return 0
    
    async def srem(self, name: str, *values: Any) -> int:
        """Remove values from set."""
        try:
            redis_client = self.get_redis()
            # Convert complex types to JSON
            json_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    json_values.append(json.dumps(value))
                else:
                    json_values.append(value)
            
            return await redis_client.srem(name, *json_values)
        except Exception as e:
            logger.error(f"Redis SREM error for set {name}: {e}")
            return 0
    
    async def smembers(self, name: str) -> set:
        """Get all members of set."""
        try:
            redis_client = self.get_redis()
            return await redis_client.smembers(name)
        except Exception as e:
            logger.error(f"Redis SMEMBERS error for set {name}: {e}")
            return set()


# Global Redis manager instance
redis_manager = RedisManager()


# Utility functions
async def get_redis() -> Redis:
    """Get Redis connection."""
    return redis_manager.get_redis()


async def check_redis_connection() -> bool:
    """Check if Redis connection is working."""
    return await redis_manager.health_check()