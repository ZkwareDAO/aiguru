"""Mock tests for Redis cache and session functionality."""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.redis import RedisManager
from app.core.cache import CacheManager
from app.core.session import SessionManager
from app.core.cache_utils import CacheService, SessionService


class TestRedisMock:
    """Test Redis functionality with mocked Redis client."""
    
    @pytest.mark.asyncio
    async def test_redis_manager_basic_operations(self):
        """Test Redis manager basic operations with mock."""
        redis_manager = RedisManager()
        
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True
        mock_redis.get.return_value = "test_value"
        mock_redis.delete.return_value = 1
        mock_redis.exists.return_value = 1
        mock_redis.ping.return_value = True
        
        with patch.object(redis_manager, 'get_redis', return_value=mock_redis):
            # Test SET
            result = await redis_manager.set("test_key", "test_value", expire=60)
            assert result is True
            mock_redis.set.assert_called_once_with("test_key", "test_value", ex=60)
            
            # Test GET
            value = await redis_manager.get("test_key")
            assert value == "test_value"
            mock_redis.get.assert_called_once_with("test_key")
            
            # Test DELETE
            deleted = await redis_manager.delete("test_key")
            assert deleted is True
            mock_redis.delete.assert_called_once_with("test_key")
            
            # Test EXISTS
            exists = await redis_manager.exists("test_key")
            assert exists is True
            mock_redis.exists.assert_called_once_with("test_key")
            
            # Test health check
            healthy = await redis_manager.health_check()
            assert healthy is True
            mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_redis_manager_complex_data(self):
        """Test Redis manager with complex data types."""
        redis_manager = RedisManager()
        
        test_data = {"user_id": "123", "scores": [85, 92, 78]}
        expected_json = json.dumps(test_data)
        
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True
        mock_redis.get.return_value = expected_json
        
        with patch.object(redis_manager, 'get_redis', return_value=mock_redis):
            # Test setting complex data
            result = await redis_manager.set("complex_key", test_data, expire=60)
            assert result is True
            mock_redis.set.assert_called_once_with("complex_key", expected_json, ex=60)
            
            # Test getting complex data
            value = await redis_manager.get("complex_key")
            assert value == expected_json
    
    @pytest.mark.asyncio
    async def test_redis_manager_hash_operations(self):
        """Test Redis hash operations with mock."""
        redis_manager = RedisManager()
        
        mock_redis = AsyncMock()
        mock_redis.hset.return_value = 1
        mock_redis.hget.return_value = "field_value"
        mock_redis.hgetall.return_value = {"field1": "value1", "field2": "value2"}
        mock_redis.hdel.return_value = 2
        
        with patch.object(redis_manager, 'get_redis', return_value=mock_redis):
            # Test HSET
            result = await redis_manager.hset("test_hash", "field1", "value1")
            assert result is True
            mock_redis.hset.assert_called_once_with("test_hash", "field1", "value1")
            
            # Test HGET
            value = await redis_manager.hget("test_hash", "field1")
            assert value == "field_value"
            mock_redis.hget.assert_called_once_with("test_hash", "field1")
            
            # Test HGETALL
            all_fields = await redis_manager.hgetall("test_hash")
            assert all_fields == {"field1": "value1", "field2": "value2"}
            mock_redis.hgetall.assert_called_once_with("test_hash")
            
            # Test HDEL
            deleted_count = await redis_manager.hdel("test_hash", "field1", "field2")
            assert deleted_count == 2
            mock_redis.hdel.assert_called_once_with("test_hash", "field1", "field2")


class TestCacheManagerMock:
    """Test cache manager with mocked Redis."""
    
    @pytest.mark.asyncio
    async def test_cache_get_or_set(self):
        """Test cache get_or_set functionality with mock."""
        cache_manager = CacheManager()
        
        # Mock Redis manager
        mock_redis_manager = AsyncMock()
        mock_redis_manager.get.return_value = None  # First call returns None (cache miss)
        mock_redis_manager.set.return_value = True
        
        with patch.object(cache_manager, 'redis', mock_redis_manager):
            # Define factory function
            def data_factory():
                return {"generated": True, "timestamp": "2024-01-01T00:00:00"}
            
            # Test cache miss scenario
            result = await cache_manager.get_or_set("test_key", data_factory, expire=60)
            
            assert result == {"generated": True, "timestamp": "2024-01-01T00:00:00"}
            mock_redis_manager.get.assert_called_once_with("test_key")
            mock_redis_manager.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_specialized_methods(self):
        """Test specialized cache methods with mock."""
        cache_manager = CacheManager()
        
        mock_redis_manager = AsyncMock()
        mock_redis_manager.set.return_value = True
        mock_redis_manager.get.return_value = json.dumps({"name": "Test User"})
        mock_redis_manager.delete.return_value = True
        
        with patch.object(cache_manager, 'redis', mock_redis_manager):
            user_id = str(uuid4())
            user_data = {"name": "Test User", "email": "test@example.com"}
            
            # Test cache user data
            result = await cache_manager.cache_user_data(user_id, user_data)
            assert result is True
            
            # Test get user data
            retrieved_data = await cache_manager.get_user_data(user_id)
            assert retrieved_data == {"name": "Test User"}
            
            # Test invalidate user cache
            with patch.object(cache_manager, 'invalidate_pattern', return_value=5):
                invalidated = await cache_manager.invalidate_user_cache(user_id)
                assert invalidated is True


class TestSessionManagerMock:
    """Test session manager with mocked Redis."""
    
    @pytest.mark.asyncio
    async def test_session_creation_and_retrieval(self):
        """Test session creation and retrieval with mock."""
        session_manager = SessionManager()
        
        user_id = uuid4()
        session_data = {"role": "student"}
        
        # Mock Redis manager
        mock_redis_manager = AsyncMock()
        mock_redis_manager.set.return_value = True
        mock_redis_manager.sadd.return_value = 1
        mock_redis_manager.expire.return_value = True
        
        # Mock session data for retrieval
        stored_session_data = {
            "user_id": str(user_id),
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(seconds=86400)).isoformat(),
            "data": session_data
        }
        mock_redis_manager.get.return_value = json.dumps(stored_session_data)
        
        with patch.object(session_manager, 'redis', mock_redis_manager):
            # Test session creation
            session_id = await session_manager.create_session(user_id, session_data)
            
            assert session_id is not None
            assert len(session_id) > 0
            
            # Verify Redis calls for session creation
            assert mock_redis_manager.set.call_count >= 1
            assert mock_redis_manager.sadd.call_count >= 1
            
            # Test session retrieval
            retrieved_session = await session_manager.get_session(session_id)
            
            assert retrieved_session is not None
            assert retrieved_session["user_id"] == str(user_id)
            assert retrieved_session["data"]["role"] == "student"
    
    @pytest.mark.asyncio
    async def test_session_update(self):
        """Test session update with mock."""
        session_manager = SessionManager()
        
        session_id = "test_session_id"
        existing_data = {
            "user_id": "test_user",
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(seconds=86400)).isoformat(),
            "data": {"initial": "data"}
        }
        
        mock_redis_manager = AsyncMock()
        mock_redis_manager.get.return_value = json.dumps(existing_data)
        mock_redis_manager.set.return_value = True
        
        with patch.object(session_manager, 'redis', mock_redis_manager):
            # Test session update
            update_data = {"new_field": "new_value"}
            result = await session_manager.update_session(session_id, update_data)
            
            assert result is True
            
            # Verify Redis set was called with updated data
            mock_redis_manager.set.assert_called_once()
            call_args = mock_redis_manager.set.call_args
            updated_session_json = call_args[0][1]
            updated_session = json.loads(updated_session_json)
            
            assert updated_session["data"]["initial"] == "data"
            assert updated_session["data"]["new_field"] == "new_value"
    
    @pytest.mark.asyncio
    async def test_session_deletion(self):
        """Test session deletion with mock."""
        session_manager = SessionManager()
        
        session_id = "test_session_id"
        session_data = {
            "user_id": "test_user",
            "data": {"role": "student"}
        }
        
        mock_redis_manager = AsyncMock()
        mock_redis_manager.get.return_value = json.dumps(session_data)
        mock_redis_manager.delete.return_value = 1
        mock_redis_manager.srem.return_value = 1
        
        with patch.object(session_manager, 'redis', mock_redis_manager):
            # Test session deletion
            result = await session_manager.delete_session(session_id)
            
            assert result is True
            
            # Verify Redis operations
            mock_redis_manager.get.assert_called_once()
            mock_redis_manager.delete.assert_called_once()
            mock_redis_manager.srem.assert_called_once()


class TestCacheServiceMock:
    """Test cache service with mocked dependencies."""
    
    @pytest.mark.asyncio
    async def test_user_profile_caching(self):
        """Test user profile caching with mock."""
        cache_service = CacheService()
        
        user_id = str(uuid4())
        profile_data = {"name": "Test User", "email": "test@example.com"}
        
        # Mock cache manager
        mock_cache_manager = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True
        mock_redis.get.return_value = json.dumps(profile_data)
        mock_redis.delete.return_value = True
        mock_cache_manager.redis = mock_redis
        
        with patch.object(cache_service, 'cache', mock_cache_manager):
            # Test cache user profile
            result = await cache_service.cache_user_profile(user_id, profile_data)
            assert result is True
            
            # Test get user profile
            retrieved_profile = await cache_service.get_user_profile(user_id)
            assert retrieved_profile == profile_data
            
            # Test invalidate user profile
            invalidated = await cache_service.invalidate_user_profile(user_id)
            assert invalidated is True


class TestSessionServiceMock:
    """Test session service with mocked dependencies."""
    
    @pytest.mark.asyncio
    async def test_authenticated_session_creation(self):
        """Test authenticated session creation with mock."""
        session_service = SessionService()
        
        user_id = uuid4()
        user_role = "teacher"
        
        # Mock session manager
        mock_session_manager = AsyncMock()
        mock_session_manager.create_session.return_value = "test_session_id"
        
        with patch.object(session_service, 'session', mock_session_manager):
            # Test authenticated session creation
            session_id = await session_service.create_authenticated_session(
                user_id, user_role, {"department": "Math"}
            )
            
            assert session_id == "test_session_id"
            
            # Verify session manager was called with correct data
            mock_session_manager.create_session.assert_called_once()
            call_args = mock_session_manager.create_session.call_args
            
            assert call_args[0][0] == user_id  # user_id
            session_data = call_args[0][1]  # session_data
            assert session_data["role"] == user_role
            assert session_data["department"] == "Math"
            assert "login_time" in session_data
    
    @pytest.mark.asyncio
    async def test_session_validation(self):
        """Test session validation with mock."""
        session_service = SessionService()
        
        session_id = "test_session_id"
        
        # Mock session manager for valid session
        mock_session_manager = AsyncMock()
        valid_session_data = {
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        mock_session_manager.get_session.return_value = valid_session_data
        
        with patch.object(session_service, 'session', mock_session_manager):
            # Test valid session
            is_expired = await session_service.is_session_expired(session_id)
            assert is_expired is False
        
        # Mock session manager for expired session
        expired_session_data = {
            "expires_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        }
        mock_session_manager.get_session.return_value = expired_session_data
        
        with patch.object(session_service, 'session', mock_session_manager):
            # Test expired session
            is_expired = await session_service.is_session_expired(session_id)
            assert is_expired is True
        
        # Mock session manager for non-existent session
        mock_session_manager.get_session.return_value = None
        
        with patch.object(session_service, 'session', mock_session_manager):
            # Test non-existent session
            is_expired = await session_service.is_session_expired(session_id)
            assert is_expired is True


# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])