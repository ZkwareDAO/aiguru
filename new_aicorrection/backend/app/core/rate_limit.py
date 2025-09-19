"""Rate limiting utilities using Redis."""

import logging
import time
from typing import Optional, Tuple

from app.core.redis import redis_manager

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter."""
    
    def __init__(self):
        self.redis = redis_manager
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        identifier: Optional[str] = None
    ) -> Tuple[bool, dict]:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            key: Base key for rate limiting (e.g., 'api', 'login')
            limit: Maximum number of requests allowed
            window_seconds: Time window in seconds
            identifier: Additional identifier (e.g., user_id, ip_address)
        
        Returns:
            Tuple of (is_allowed, info_dict)
            info_dict contains: remaining, reset_time, retry_after
        """
        try:
            # Build the full key
            full_key = f"rate_limit:{key}"
            if identifier:
                full_key += f":{identifier}"
            
            current_time = int(time.time())
            window_start = current_time - window_seconds
            
            redis_client = self.redis.get_redis()
            
            # Use a pipeline for atomic operations
            pipe = redis_client.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(full_key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(full_key)
            
            # Add current request
            pipe.zadd(full_key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(full_key, window_seconds)
            
            # Execute pipeline
            results = await pipe.execute()
            
            current_count = results[1]  # Count after removing expired entries
            
            # Check if limit is exceeded
            is_allowed = current_count < limit
            remaining = max(0, limit - current_count - 1) if is_allowed else 0
            reset_time = current_time + window_seconds
            retry_after = window_seconds if not is_allowed else 0
            
            info = {
                "limit": limit,
                "remaining": remaining,
                "reset_time": reset_time,
                "retry_after": retry_after,
                "window_seconds": window_seconds
            }
            
            if not is_allowed:
                logger.warning(
                    f"Rate limit exceeded for key {full_key}: "
                    f"{current_count + 1}/{limit} requests in {window_seconds}s"
                )
            
            return is_allowed, info
        
        except Exception as e:
            logger.error(f"Error checking rate limit for key {key}: {e}")
            # On error, allow the request but log the issue
            return True, {
                "limit": limit,
                "remaining": limit - 1,
                "reset_time": int(time.time()) + window_seconds,
                "retry_after": 0,
                "window_seconds": window_seconds
            }
    
    async def reset_limit(self, key: str, identifier: Optional[str] = None) -> bool:
        """Reset rate limit for a key."""
        try:
            full_key = f"rate_limit:{key}"
            if identifier:
                full_key += f":{identifier}"
            
            result = await self.redis.delete(full_key)
            
            if result:
                logger.info(f"Reset rate limit for key {full_key}")
            
            return bool(result)
        
        except Exception as e:
            logger.error(f"Error resetting rate limit for key {key}: {e}")
            return False
    
    async def get_limit_info(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        identifier: Optional[str] = None
    ) -> dict:
        """Get current rate limit information without incrementing."""
        try:
            full_key = f"rate_limit:{key}"
            if identifier:
                full_key += f":{identifier}"
            
            current_time = int(time.time())
            window_start = current_time - window_seconds
            
            redis_client = self.redis.get_redis()
            
            # Count current requests in window
            current_count = await redis_client.zcount(full_key, window_start, current_time)
            
            remaining = max(0, limit - current_count)
            reset_time = current_time + window_seconds
            
            return {
                "limit": limit,
                "current": current_count,
                "remaining": remaining,
                "reset_time": reset_time,
                "window_seconds": window_seconds
            }
        
        except Exception as e:
            logger.error(f"Error getting rate limit info for key {key}: {e}")
            return {
                "limit": limit,
                "current": 0,
                "remaining": limit,
                "reset_time": int(time.time()) + window_seconds,
                "window_seconds": window_seconds
            }


# Global rate limiter instance
rate_limiter = RateLimiter()


# Common rate limit configurations
RATE_LIMITS = {
    "api_general": {"limit": 1000, "window": 3600},  # 1000 requests per hour
    "api_auth": {"limit": 10, "window": 300},        # 10 auth requests per 5 minutes
    "api_upload": {"limit": 50, "window": 3600},     # 50 uploads per hour
    "api_ai_grading": {"limit": 100, "window": 3600}, # 100 AI requests per hour
    "login_attempts": {"limit": 5, "window": 900},   # 5 login attempts per 15 minutes
    "password_reset": {"limit": 3, "window": 3600},  # 3 password resets per hour
    "email_send": {"limit": 10, "window": 3600},     # 10 emails per hour
}


async def check_rate_limit(
    limit_type: str,
    identifier: str,
    custom_limit: Optional[int] = None,
    custom_window: Optional[int] = None
) -> Tuple[bool, dict]:
    """
    Check rate limit for a specific type and identifier.
    
    Args:
        limit_type: Type of rate limit (from RATE_LIMITS)
        identifier: Unique identifier (user_id, ip_address, etc.)
        custom_limit: Override default limit
        custom_window: Override default window
    
    Returns:
        Tuple of (is_allowed, info_dict)
    """
    if limit_type not in RATE_LIMITS:
        logger.warning(f"Unknown rate limit type: {limit_type}")
        return True, {}
    
    config = RATE_LIMITS[limit_type]
    limit = custom_limit or config["limit"]
    window = custom_window or config["window"]
    
    return await rate_limiter.is_allowed(limit_type, limit, window, identifier)


async def reset_rate_limit(limit_type: str, identifier: str) -> bool:
    """Reset rate limit for a specific type and identifier."""
    return await rate_limiter.reset_limit(limit_type, identifier)


async def get_rate_limit_info(limit_type: str, identifier: str) -> dict:
    """Get rate limit information for a specific type and identifier."""
    if limit_type not in RATE_LIMITS:
        return {}
    
    config = RATE_LIMITS[limit_type]
    return await rate_limiter.get_limit_info(
        limit_type, config["limit"], config["window"], identifier
    )