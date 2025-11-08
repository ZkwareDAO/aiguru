# Redis Cache and Session Management

This document describes the Redis-based caching and session management implementation for the AI Education Backend.

## Overview

The system implements a comprehensive Redis-based solution for:
- **Caching**: High-performance data caching with specialized cache managers
- **Session Management**: Secure user session storage with expiration handling
- **Connection Management**: Robust Redis connection pooling and health monitoring

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │    │  Cache Service  │    │ Session Service │
│     Layer       │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴───────────┐
                    │    Cache Manager        │
                    │  - Specialized Methods  │
                    │  - Multi Operations     │
                    │  - Pattern Invalidation │
                    └─────────────┬───────────┘
                                  │
                    ┌─────────────┴───────────┐
                    │   Session Manager       │
                    │  - User Sessions        │
                    │  - Expiration Handling  │
                    │  - Activity Tracking    │
                    └─────────────┬───────────┘
                                  │
                    ┌─────────────┴───────────┐
                    │    Redis Manager        │
                    │  - Connection Pool      │
                    │  - Basic Operations     │
                    │  - Health Monitoring    │
                    └─────────────┬───────────┘
                                  │
                    ┌─────────────┴───────────┐
                    │      Redis Server       │
                    └─────────────────────────┘
```

## Core Components

### 1. Redis Manager (`app/core/redis.py`)

The foundational Redis connection and operation manager.

**Key Features:**
- Async Redis connection with connection pooling
- Basic Redis operations (GET, SET, DELETE, etc.)
- Hash, List, and Set operations
- Health monitoring and error handling
- Automatic JSON serialization for complex data types

**Usage Example:**
```python
from app.core.redis import redis_manager

# Basic operations
await redis_manager.set("key", "value", expire=3600)
value = await redis_manager.get("key")
await redis_manager.delete("key")

# Complex data
data = {"user_id": "123", "scores": [85, 92, 78]}
await redis_manager.set("user_data", data, expire=1800)
```

### 2. Cache Manager (`app/core/cache.py`)

High-level caching utilities with specialized methods for different data types.

**Key Features:**
- Get-or-set pattern with factory functions
- Multi-key operations (get/set multiple values)
- Pattern-based cache invalidation
- Specialized methods for user, class, assignment data
- Configurable expiration times

**Cache Key Prefixes:**
- `user:` - User-related data
- `class:` - Class-related data  
- `assignment:` - Assignment-related data
- `grading:` - AI grading results
- `analytics:` - Analytics and reports

**Usage Example:**
```python
from app.core.cache import cache_manager

# Get-or-set pattern
async def expensive_operation():
    return {"computed": "data"}

result = await cache_manager.get_or_set(
    "expensive_key", 
    expensive_operation, 
    expire=3600
)

# Specialized caching
await cache_manager.cache_user_data(user_id, user_profile)
profile = await cache_manager.get_user_data(user_id)
```

### 3. Session Manager (`app/core/session.py`)

Comprehensive user session management with security features.

**Key Features:**
- Secure session creation with unique tokens
- Session expiration and automatic cleanup
- User activity tracking
- Multi-session support per user
- Session extension and invalidation

**Session Data Structure:**
```json
{
  "user_id": "uuid",
  "created_at": "2024-01-01T00:00:00",
  "last_accessed": "2024-01-01T12:00:00", 
  "expires_at": "2024-01-02T00:00:00",
  "data": {
    "role": "student",
    "permissions": ["read", "write"],
    "custom_field": "value"
  }
}
```

**Usage Example:**
```python
from app.core.session import session_manager

# Create session
session_id = await session_manager.create_session(
    user_id=user.id,
    data={"role": "teacher", "department": "Math"},
    expire_seconds=86400
)

# Retrieve session
session_data = await session_manager.get_session(session_id)

# Update session
await session_manager.update_session(session_id, {"last_login": "2024-01-01"})
```

### 4. Cache Service (`app/core/cache_utils.py`)

Application-specific cache operations with standardized key management.

**Key Features:**
- Centralized cache key management
- Domain-specific cache methods
- Bulk invalidation operations
- Type-safe cache operations

**Cache Key Templates:**
```python
class CacheKeys:
    USER_PROFILE = "user:profile:{user_id}"
    USER_CLASSES = "user:classes:{user_id}"
    CLASS_STUDENTS = "class:students:{class_id}"
    ASSIGNMENT_INFO = "assignment:info:{assignment_id}"
    GRADING_RESULT = "grading:result:{task_id}"
    AI_CHAT_CONTEXT = "ai:context:{user_id}"
```

### 5. Session Service (`app/core/cache_utils.py`)

High-level session operations for authentication workflows.

**Key Features:**
- Authenticated session creation with context
- Session validation and expiration checking
- Activity tracking and session extension
- Bulk session management

## Configuration

### Environment Variables

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Session Configuration (optional, defaults provided)
SESSION_EXPIRE_SECONDS=86400  # 24 hours
SESSION_CLEANUP_INTERVAL=3600 # 1 hour

# Cache Configuration (optional, defaults provided)
CACHE_DEFAULT_EXPIRE=3600     # 1 hour
CACHE_SHORT_EXPIRE=300        # 5 minutes
CACHE_LONG_EXPIRE=86400       # 24 hours
```

### Redis Connection Settings

The Redis manager automatically configures:
- **Connection Pool**: Max 20 connections
- **Retry Policy**: Retry on timeout
- **Keep-Alive**: Socket keep-alive enabled
- **Health Checks**: Every 30 seconds
- **Timeouts**: 5 seconds for connect/socket operations

## Usage Patterns

### 1. User Data Caching

```python
from app.core.cache_utils import cache_service

# Cache user profile
await cache_service.cache_user_profile(user_id, profile_data)

# Get cached profile
profile = await cache_service.get_user_profile(user_id)

# Invalidate user cache
await cache_service.invalidate_user_cache(user_id)
```

### 2. Session Management

```python
from app.core.cache_utils import session_service

# Create authenticated session
session_id = await session_service.create_authenticated_session(
    user_id=user.id,
    user_role="teacher",
    additional_data={"department": "Mathematics"}
)

# Validate session
is_expired = await session_service.is_session_expired(session_id)

# Extend session
await session_service.extend_user_session(session_id, minutes=30)
```

### 3. Cache Decorators

```python
from app.core.cache import cache_result, invalidate_cache

@cache_result("user:assignments:{user_id}", expire=1800, key_args=["user_id"])
async def get_user_assignments(user_id: str):
    # Expensive database operation
    return await db.query_user_assignments(user_id)

@invalidate_cache("user:assignments:{user_id}", key_args=["user_id"])
async def create_assignment(user_id: str, assignment_data: dict):
    # Create assignment and invalidate cache
    return await db.create_assignment(user_id, assignment_data)
```

### 4. Bulk Operations

```python
from app.core.cache import cache_manager

# Set multiple values
data = {
    "key1": {"data": "value1"},
    "key2": {"data": "value2"},
    "key3": {"data": "value3"}
}
await cache_manager.set_multi(data, expire=3600)

# Get multiple values
keys = ["key1", "key2", "key3"]
results = await cache_manager.get_multi(keys)
```

## Performance Considerations

### Cache Expiration Strategy

- **User Data**: 1 hour (frequently accessed, moderate change rate)
- **Class Data**: 1 hour (moderate access, low change rate)
- **Assignment Data**: 1 hour (moderate access, moderate change rate)
- **Grading Results**: 24 hours (infrequent access, rarely changes)
- **Analytics Data**: 5 minutes (expensive to compute, acceptable staleness)

### Memory Management

- **Key Patterns**: Use consistent prefixes for easy pattern matching
- **Data Size**: Compress large objects before caching
- **TTL**: Always set expiration to prevent memory leaks
- **Cleanup**: Regular cleanup of expired sessions and cache entries

### Connection Pooling

- **Pool Size**: 20 connections (configurable)
- **Connection Reuse**: Automatic connection recycling
- **Health Monitoring**: Automatic unhealthy connection replacement
- **Timeout Handling**: Graceful timeout and retry logic

## Error Handling

### Redis Connection Failures

```python
# Graceful degradation
try:
    cached_data = await cache_manager.get_user_data(user_id)
    if cached_data is None:
        # Fallback to database
        data = await database.get_user_data(user_id)
        # Try to cache for next time (may fail silently)
        await cache_manager.cache_user_data(user_id, data)
        return data
except Exception as e:
    logger.warning(f"Cache error, falling back to database: {e}")
    return await database.get_user_data(user_id)
```

### Session Validation

```python
# Always validate sessions
session_data = await session_manager.get_session(session_id)
if not session_data:
    raise HTTPException(status_code=401, detail="Invalid or expired session")

# Check expiration
if await session_service.is_session_expired(session_id):
    await session_manager.delete_session(session_id)
    raise HTTPException(status_code=401, detail="Session expired")
```

## Monitoring and Maintenance

### Health Checks

```python
from app.core.redis import check_redis_connection

# Health check endpoint
@app.get("/health/redis")
async def redis_health():
    is_healthy = await check_redis_connection()
    return {"redis": "healthy" if is_healthy else "unhealthy"}
```

### Session Statistics

```python
from app.core.session import session_manager

# Get session statistics
stats = await session_manager.get_session_stats()
# Returns: {
#   "total_sessions": 150,
#   "active_sessions": 120,
#   "expired_sessions": 30,
#   "unique_users": 85
# }
```

### Cache Statistics

```python
from app.core.redis import redis_manager

# Monitor Redis memory usage
redis_client = redis_manager.get_redis()
info = await redis_client.info("memory")
memory_usage = info["used_memory_human"]
```

## Security Considerations

### Session Security

- **Token Generation**: Cryptographically secure random tokens
- **Session Isolation**: User sessions stored separately
- **Automatic Cleanup**: Expired sessions automatically removed
- **Activity Tracking**: Last access time updated on each request

### Cache Security

- **Data Isolation**: User-specific cache keys prevent data leakage
- **Sensitive Data**: Avoid caching sensitive information (passwords, tokens)
- **Access Control**: Cache operations respect user permissions
- **Data Encryption**: Consider encrypting sensitive cached data

## Testing

The implementation includes comprehensive test coverage:

- **Unit Tests**: Mock-based tests for all components
- **Integration Tests**: Real Redis integration tests
- **Performance Tests**: Load testing for cache operations
- **Security Tests**: Session security and isolation tests

Run tests:
```bash
# Mock tests (no Redis required)
pytest tests/test_redis_mock.py -v

# Integration tests (requires Redis)
pytest tests/test_redis_cache_session.py -v
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure Redis server is running
2. **Memory Issues**: Monitor Redis memory usage and set appropriate limits
3. **Performance**: Check connection pool size and timeout settings
4. **Session Expiry**: Verify session expiration times are appropriate

### Debug Commands

```python
# Check Redis connection
await redis_manager.health_check()

# List all keys (development only)
redis_client = redis_manager.get_redis()
keys = await redis_client.keys("*")

# Get session info
session_data = await session_manager.get_session(session_id)

# Check cache hit/miss
cached_value = await cache_manager.get_user_data(user_id)
```

This Redis cache and session implementation provides a robust, scalable foundation for the AI Education Backend's data management needs.