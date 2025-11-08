"""Tests for Redis cache and session functionality."""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.core.redis import redis_manager, check_redis_connection
from app.core.cache import cache_manager
from app.core.session import session_manager
from app.core.cache_utils import cache_service, session_service


class TestRedisConnection:
    """Test Redis connection and basic operations."""
    
    @pytest.mark.asyncio
    async def test_redis_connection(self):
        """Test Redis connection health check."""
        is_healthy = await check_redis_connection()
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_redis_basic_operations(self):
        """Test basic Redis operations."""
        # Test SET and GET
        key = "test:basic:key"
        value = "test_value"
        
        result = await redis_manager.set(key, value, expire=60)
        assert result is True
        
        retrieved_value = await redis_manager.get(key)
        assert retrieved_value == value
        
        # Test EXISTS
        exists = await redis_manager.exists(key)
        assert exists is True
        
        # Test DELETE
        deleted = await redis_manager.delete(key)
        assert deleted is True
        
        # Verify deletion
        retrieved_value = await redis_manager.get(key)
        assert retrieved_value is None
    
    @pytest.mark.asyncio
    async def test_redis_complex_data(self):
        """Test Redis operations with complex data types."""
        key = "test:complex:data"
        data = {
            "user_id": "123",
            "name": "Test User",
            "scores": [85, 92, 78],
            "metadata": {"role": "student", "active": True}
        }
        
        # Set complex data
        result = await redis_manager.set(key, data, expire=60)
        assert result is True
        
        # Get and verify complex data
        retrieved_data = await redis_manager.get(key)
        assert retrieved_data is not None
        
        parsed_data = json.loads(retrieved_data)
        assert parsed_data == data
        
        # Cleanup
        await redis_manager.delete(key)
    
    @pytest.mark.asyncio
    async def test_redis_hash_operations(self):
        """Test Redis hash operations."""
        hash_name = "test:hash"
        
        # Set hash fields
        await redis_manager.hset(hash_name, "field1", "value1")
        await redis_manager.hset(hash_name, "field2", {"nested": "data"})
        
        # Get hash fields
        value1 = await redis_manager.hget(hash_name, "field1")
        assert value1 == "value1"
        
        value2 = await redis_manager.hget(hash_name, "field2")
        assert json.loads(value2) == {"nested": "data"}
        
        # Get all hash fields
        all_fields = await redis_manager.hgetall(hash_name)
        assert "field1" in all_fields
        assert "field2" in all_fields
        
        # Delete hash fields
        deleted_count = await redis_manager.hdel(hash_name, "field1", "field2")
        assert deleted_count == 2


class TestCacheManager:
    """Test cache manager functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_get_or_set(self):
        """Test cache get_or_set functionality."""
        key = "test:cache:get_or_set"
        
        # Define a factory function
        def data_factory():
            return {"timestamp": datetime.utcnow().isoformat(), "data": "generated"}
        
        # First call should generate data
        result1 = await cache_manager.get_or_set(key, data_factory, expire=60)
        assert result1 is not None
        assert "timestamp" in result1
        assert result1["data"] == "generated"
        
        # Second call should return cached data
        result2 = await cache_manager.get_or_set(key, data_factory, expire=60)
        assert result2 == result1  # Should be identical (cached)
        
        # Cleanup
        await redis_manager.delete(key)
    
    @pytest.mark.asyncio
    async def test_cache_multi_operations(self):
        """Test cache multi get/set operations."""
        keys = ["test:multi:1", "test:multi:2", "test:multi:3"]
        data = {
            keys[0]: {"id": 1, "name": "Item 1"},
            keys[1]: {"id": 2, "name": "Item 2"},
            keys[2]: {"id": 3, "name": "Item 3"}
        }
        
        # Set multiple values
        result = await cache_manager.set_multi(data, expire=60)
        assert result is True
        
        # Get multiple values
        retrieved_data = await cache_manager.get_multi(keys)
        assert len(retrieved_data) == 3
        
        for key in keys:
            assert retrieved_data[key] is not None
            assert retrieved_data[key]["name"] in ["Item 1", "Item 2", "Item 3"]
        
        # Cleanup
        for key in keys:
            await redis_manager.delete(key)
    
    @pytest.mark.asyncio
    async def test_cache_specialized_methods(self):
        """Test specialized cache methods."""
        user_id = str(uuid4())
        class_id = str(uuid4())
        
        # Test user data caching
        user_data = {"name": "Test User", "email": "test@example.com"}
        result = await cache_manager.cache_user_data(user_id, user_data)
        assert result is True
        
        retrieved_user_data = await cache_manager.get_user_data(user_id)
        assert retrieved_user_data == user_data
        
        # Test class data caching
        class_data = {"name": "Test Class", "subject": "Math"}
        result = await cache_manager.cache_class_data(class_id, class_data)
        assert result is True
        
        retrieved_class_data = await cache_manager.get_class_data(class_id)
        assert retrieved_class_data == class_data
        
        # Test cache invalidation
        invalidated = await cache_manager.invalidate_user_cache(user_id)
        assert invalidated > 0
        
        # Verify invalidation
        retrieved_user_data = await cache_manager.get_user_data(user_id)
        assert retrieved_user_data is None


class TestSessionManager:
    """Test session manager functionality."""
    
    @pytest.mark.asyncio
    async def test_session_creation_and_retrieval(self):
        """Test session creation and retrieval."""
        user_id = uuid4()
        session_data = {"role": "student", "login_time": datetime.utcnow().isoformat()}
        
        # Create session
        session_id = await session_manager.create_session(user_id, session_data, expire_seconds=3600)
        assert session_id is not None
        assert len(session_id) > 0
        
        # Retrieve session
        retrieved_session = await session_manager.get_session(session_id)
        assert retrieved_session is not None
        assert retrieved_session["user_id"] == str(user_id)
        assert retrieved_session["data"]["role"] == "student"
        
        # Cleanup
        await session_manager.delete_session(session_id)
    
    @pytest.mark.asyncio
    async def test_session_update(self):
        """Test session data update."""
        user_id = uuid4()
        
        # Create session
        session_id = await session_manager.create_session(user_id, {"initial": "data"})
        
        # Update session
        update_data = {"new_field": "new_value", "updated": True}
        result = await session_manager.update_session(session_id, update_data)
        assert result is True
        
        # Verify update
        session_data = await session_manager.get_session(session_id)
        assert session_data["data"]["initial"] == "data"
        assert session_data["data"]["new_field"] == "new_value"
        assert session_data["data"]["updated"] is True
        
        # Cleanup
        await session_manager.delete_session(session_id)
    
    @pytest.mark.asyncio
    async def test_session_expiration(self):
        """Test session expiration handling."""
        user_id = uuid4()
        
        # Create session with short expiration
        session_id = await session_manager.create_session(user_id, {"test": "data"}, expire_seconds=1)
        
        # Verify session exists
        session_data = await session_manager.get_session(session_id)
        assert session_data is not None
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Verify session is expired/deleted
        session_data = await session_manager.get_session(session_id)
        assert session_data is None
    
    @pytest.mark.asyncio
    async def test_user_sessions_management(self):
        """Test user sessions management."""
        user_id = uuid4()
        
        # Create multiple sessions for user
        session_ids = []
        for i in range(3):
            session_id = await session_manager.create_session(user_id, {"session": i})
            session_ids.append(session_id)
        
        # Get user sessions
        user_sessions = await session_manager.get_user_sessions(user_id)
        assert len(user_sessions) == 3
        
        for session_id in session_ids:
            assert session_id in user_sessions
        
        # Delete all user sessions
        deleted_count = await session_manager.delete_user_sessions(user_id)
        assert deleted_count == 3
        
        # Verify all sessions are deleted
        user_sessions = await session_manager.get_user_sessions(user_id)
        assert len(user_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_session_extension(self):
        """Test session expiration extension."""
        user_id = uuid4()
        
        # Create session
        session_id = await session_manager.create_session(user_id, {"test": "data"}, expire_seconds=60)
        
        # Extend session
        result = await session_manager.extend_session(session_id, additional_seconds=120)
        assert result is True
        
        # Verify session still exists and has extended expiration
        session_data = await session_manager.get_session(session_id)
        assert session_data is not None
        
        # Check TTL is approximately 120 seconds (allowing for small timing differences)
        session_key = session_manager._get_session_key(session_id)
        ttl = await redis_manager.ttl(session_key)
        assert 110 <= ttl <= 120  # Allow for timing variations
        
        # Cleanup
        await session_manager.delete_session(session_id)


class TestCacheService:
    """Test high-level cache service."""
    
    @pytest.mark.asyncio
    async def test_user_profile_caching(self):
        """Test user profile caching."""
        user_id = str(uuid4())
        profile_data = {
            "name": "Test User",
            "email": "test@example.com",
            "role": "student"
        }
        
        # Cache user profile
        result = await cache_service.cache_user_profile(user_id, profile_data)
        assert result is True
        
        # Retrieve user profile
        retrieved_profile = await cache_service.get_user_profile(user_id)
        assert retrieved_profile == profile_data
        
        # Invalidate user profile
        invalidated = await cache_service.invalidate_user_profile(user_id)
        assert invalidated is True
        
        # Verify invalidation
        retrieved_profile = await cache_service.get_user_profile(user_id)
        assert retrieved_profile is None
    
    @pytest.mark.asyncio
    async def test_class_caching(self):
        """Test class information caching."""
        class_id = str(uuid4())
        class_data = {
            "name": "Mathematics 101",
            "teacher": "Dr. Smith",
            "students_count": 25
        }
        
        # Cache class info
        result = await cache_service.cache_class_info(class_id, class_data)
        assert result is True
        
        # Retrieve class info
        retrieved_class = await cache_service.get_class_info(class_id)
        assert retrieved_class == class_data
        
        # Test class students caching
        students_data = [
            {"id": "1", "name": "Student 1"},
            {"id": "2", "name": "Student 2"}
        ]
        
        result = await cache_service.cache_class_students(class_id, students_data)
        assert result is True
        
        retrieved_students = await cache_service.get_class_students(class_id)
        assert retrieved_students == students_data


class TestSessionService:
    """Test high-level session service."""
    
    @pytest.mark.asyncio
    async def test_authenticated_session_creation(self):
        """Test authenticated session creation."""
        user_id = uuid4()
        user_role = "teacher"
        additional_data = {"department": "Mathematics", "permissions": ["read", "write"]}
        
        # Create authenticated session
        session_id = await session_service.create_authenticated_session(
            user_id, user_role, additional_data
        )
        assert session_id is not None
        
        # Verify session data
        session_data = await session_manager.get_session(session_id)
        assert session_data is not None
        assert session_data["data"]["role"] == user_role
        assert session_data["data"]["department"] == "Mathematics"
        assert "login_time" in session_data["data"]
        
        # Test role retrieval
        role = await session_service.get_session_user_role(session_id)
        assert role == user_role
        
        # Test activity update
        result = await session_service.update_session_activity(session_id)
        assert result is True
        
        # Cleanup
        await session_manager.delete_session(session_id)
    
    @pytest.mark.asyncio
    async def test_session_expiration_check(self):
        """Test session expiration checking."""
        user_id = uuid4()
        
        # Create session with short expiration
        session_id = await session_manager.create_session(user_id, {"test": "data"}, expire_seconds=1)
        
        # Check if session is not expired initially
        is_expired = await session_service.is_session_expired(session_id)
        assert is_expired is False
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Check if session is expired
        is_expired = await session_service.is_session_expired(session_id)
        assert is_expired is True


# Cleanup function to run after all tests
@pytest.fixture(scope="session", autouse=True)
async def cleanup_redis():
    """Clean up Redis after all tests."""
    yield
    
    # Clean up any remaining test keys
    redis_client = redis_manager.get_redis()
    test_keys = await redis_client.keys("test:*")
    if test_keys:
        await redis_client.delete(*test_keys)
    
    # Close Redis connections
    await redis_manager.close()