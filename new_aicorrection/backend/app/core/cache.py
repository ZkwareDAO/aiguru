"""Cache utilities and decorators."""

import functools
import json
import logging
from typing import Any, Callable, Optional, Union

from app.core.redis import redis_manager

logger = logging.getLogger(__name__)


class CacheManager:
    """High-level cache management utilities."""
    
    def __init__(self):
        self.redis = redis_manager
        # Cache key prefixes for different data types
        self.USER_PREFIX = "user:"
        self.CLASS_PREFIX = "class:"
        self.ASSIGNMENT_PREFIX = "assignment:"
        self.GRADING_PREFIX = "grading:"
        self.ANALYTICS_PREFIX = "analytics:"
        
        # Default expiration times (in seconds)
        self.DEFAULT_EXPIRE = 3600  # 1 hour
        self.SHORT_EXPIRE = 300     # 5 minutes
        self.LONG_EXPIRE = 86400    # 24 hours
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable,
        expire: Optional[int] = 3600,
        *args,
        **kwargs
    ) -> Any:
        """Get value from cache or set it using factory function."""
        # Try to get from cache first
        cached_value = await self.redis.get(key)
        if cached_value is not None:
            try:
                return json.loads(cached_value)
            except (json.JSONDecodeError, TypeError):
                return cached_value
        
        # Generate value using factory function
        try:
            if asyncio.iscoroutinefunction(factory):
                value = await factory(*args, **kwargs)
            else:
                value = factory(*args, **kwargs)
            
            # Cache the value
            await self.redis.set(key, value, expire=expire)
            return value
        
        except Exception as e:
            logger.error(f"Error in cache factory for key {key}: {e}")
            raise
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern."""
        try:
            redis_client = self.redis.get_redis()
            keys = await redis_client.keys(pattern)
            if keys:
                return await redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
            return 0
    
    async def get_multi(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values from cache."""
        try:
            redis_client = self.redis.get_redis()
            values = await redis_client.mget(keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = value
                else:
                    result[key] = None
            
            return result
        except Exception as e:
            logger.error(f"Error getting multiple cache keys: {e}")
            return {key: None for key in keys}
    
    async def set_multi(
        self,
        mapping: dict[str, Any],
        expire: Optional[int] = 3600
    ) -> bool:
        """Set multiple values in cache."""
        try:
            redis_client = self.redis.get_redis()
            
            # Prepare data for mset
            data = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    data[key] = json.dumps(value)
                else:
                    data[key] = value
            
            # Set all values
            await redis_client.mset(data)
            
            # Set expiration for each key if specified
            if expire:
                for key in data.keys():
                    await redis_client.expire(key, expire)
            
            return True
        except Exception as e:
            logger.error(f"Error setting multiple cache values: {e}")
            return False
    
    # Specialized cache methods for different data types
    async def cache_user_data(self, user_id: str, data: dict, expire: Optional[int] = None) -> bool:
        """Cache user-specific data."""
        key = f"{self.USER_PREFIX}{user_id}"
        return await self.redis.set(key, data, expire=expire or self.DEFAULT_EXPIRE)
    
    async def get_user_data(self, user_id: str) -> Optional[dict]:
        """Get cached user data."""
        key = f"{self.USER_PREFIX}{user_id}"
        cached_data = await self.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    async def invalidate_user_cache(self, user_id: str) -> bool:
        """Invalidate all cache entries for a user."""
        pattern = f"{self.USER_PREFIX}{user_id}*"
        return await self.invalidate_pattern(pattern) > 0
    
    async def cache_class_data(self, class_id: str, data: dict, expire: Optional[int] = None) -> bool:
        """Cache class-specific data."""
        key = f"{self.CLASS_PREFIX}{class_id}"
        return await self.redis.set(key, data, expire=expire or self.DEFAULT_EXPIRE)
    
    async def get_class_data(self, class_id: str) -> Optional[dict]:
        """Get cached class data."""
        key = f"{self.CLASS_PREFIX}{class_id}"
        cached_data = await self.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    async def invalidate_class_cache(self, class_id: str) -> bool:
        """Invalidate all cache entries for a class."""
        pattern = f"{self.CLASS_PREFIX}{class_id}*"
        return await self.invalidate_pattern(pattern) > 0
    
    async def cache_assignment_data(self, assignment_id: str, data: dict, expire: Optional[int] = None) -> bool:
        """Cache assignment-specific data."""
        key = f"{self.ASSIGNMENT_PREFIX}{assignment_id}"
        return await self.redis.set(key, data, expire=expire or self.DEFAULT_EXPIRE)
    
    async def get_assignment_data(self, assignment_id: str) -> Optional[dict]:
        """Get cached assignment data."""
        key = f"{self.ASSIGNMENT_PREFIX}{assignment_id}"
        cached_data = await self.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    async def cache_grading_result(self, task_id: str, result: dict, expire: Optional[int] = None) -> bool:
        """Cache grading result with longer expiration."""
        key = f"{self.GRADING_PREFIX}{task_id}"
        return await self.redis.set(key, result, expire=expire or self.LONG_EXPIRE)
    
    async def get_grading_result(self, task_id: str) -> Optional[dict]:
        """Get cached grading result."""
        key = f"{self.GRADING_PREFIX}{task_id}"
        cached_data = await self.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    async def cache_analytics_data(self, analytics_key: str, data: dict, expire: Optional[int] = None) -> bool:
        """Cache analytics data with shorter expiration."""
        key = f"{self.ANALYTICS_PREFIX}{analytics_key}"
        return await self.redis.set(key, data, expire=expire or self.SHORT_EXPIRE)
    
    async def get_analytics_data(self, analytics_key: str) -> Optional[dict]:
        """Get cached analytics data."""
        key = f"{self.ANALYTICS_PREFIX}{analytics_key}"
        cached_data = await self.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None


# Global cache manager instance
cache_manager = CacheManager()


def cache_result(
    key_template: str,
    expire: int = 3600,
    key_args: Optional[list[str]] = None
):
    """Decorator to cache function results.
    
    Args:
        key_template: Template for cache key (e.g., "user:{user_id}")
        expire: Expiration time in seconds
        key_args: List of argument names to use in key template
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            key_data = {}
            if key_args:
                # Get function signature
                import inspect
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                # Extract specified arguments for key
                for arg_name in key_args:
                    if arg_name in bound_args.arguments:
                        key_data[arg_name] = bound_args.arguments[arg_name]
            
            cache_key = key_template.format(**key_data)
            
            # Try to get from cache
            try:
                cached_value = await cache_manager.redis.get(cache_key)
                if cached_value is not None:
                    try:
                        return json.loads(cached_value)
                    except (json.JSONDecodeError, TypeError):
                        return cached_value
            except Exception as e:
                logger.warning(f"Cache get error for key {cache_key}: {e}")
            
            # Execute function and cache result
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Cache the result
                await cache_manager.redis.set(cache_key, result, expire=expire)
                return result
            
            except Exception as e:
                logger.error(f"Function execution error: {e}")
                raise
        
        return wrapper
    return decorator


def invalidate_cache(key_template: str, key_args: Optional[list[str]] = None):
    """Decorator to invalidate cache after function execution.
    
    Args:
        key_template: Template for cache key to invalidate
        key_args: List of argument names to use in key template
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function first
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Build cache key and invalidate
            try:
                key_data = {}
                if key_args:
                    import inspect
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()
                    
                    for arg_name in key_args:
                        if arg_name in bound_args.arguments:
                            key_data[arg_name] = bound_args.arguments[arg_name]
                
                cache_key = key_template.format(**key_data)
                await cache_manager.redis.delete(cache_key)
            
            except Exception as e:
                logger.warning(f"Cache invalidation error: {e}")
            
            return result
        
        return wrapper
    return decorator


# Import asyncio at the end to avoid circular imports
import asyncio