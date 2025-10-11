"""Session management utilities."""

import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from app.core.config import get_settings
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)


class SessionManager:
    """Session management for user authentication and state."""
    
    def __init__(self):
        self.redis = redis_manager
        self.settings = get_settings()
        self.session_prefix = "session:"
        self.user_sessions_prefix = "user_sessions:"
        self.default_expire = 86400  # 24 hours
    
    def _get_session_key(self, session_id: str) -> str:
        """Get Redis key for session."""
        return f"{self.session_prefix}{session_id}"
    
    def _get_user_sessions_key(self, user_id: str) -> str:
        """Get Redis key for user's active sessions."""
        return f"{self.user_sessions_prefix}{user_id}"
    
    async def create_session(
        self,
        user_id: UUID,
        data: Optional[Dict[str, Any]] = None,
        expire_seconds: Optional[int] = None
    ) -> str:
        """Create a new session for user."""
        session_id = secrets.token_urlsafe(32)
        expire_time = expire_seconds or self.default_expire
        
        # Session data
        session_data = {
            "user_id": str(user_id),
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(seconds=expire_time)).isoformat(),
            "data": data or {}
        }
        
        try:
            # Store session
            session_key = self._get_session_key(session_id)
            await self.redis.set(session_key, json.dumps(session_data), expire=expire_time)
            
            # Add to user's active sessions
            user_sessions_key = self._get_user_sessions_key(str(user_id))
            await self.redis.sadd(user_sessions_key, session_id)
            await self.redis.expire(user_sessions_key, expire_time)
            
            logger.info(f"Created session {session_id} for user {user_id}")
            return session_id
        
        except Exception as e:
            logger.error(f"Error creating session for user {user_id}: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by session ID."""
        try:
            session_key = self._get_session_key(session_id)
            session_data = await self.redis.get(session_key)
            
            if session_data:
                data = json.loads(session_data)
                
                # Check if session is expired
                expires_at = datetime.fromisoformat(data["expires_at"])
                if datetime.utcnow() > expires_at:
                    await self.delete_session(session_id)
                    return None
                
                # Update last accessed time
                data["last_accessed"] = datetime.utcnow().isoformat()
                await self.redis.set(session_key, json.dumps(data), expire=self.default_expire)
                
                return data
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    async def update_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        extend_expiry: bool = True
    ) -> bool:
        """Update session data."""
        try:
            session_key = self._get_session_key(session_id)
            session_data = await self.redis.get(session_key)
            
            if not session_data:
                return False
            
            current_data = json.loads(session_data)
            
            # Update data
            current_data["data"].update(data)
            current_data["last_accessed"] = datetime.utcnow().isoformat()
            
            # Extend expiry if requested
            expire_time = self.default_expire
            if extend_expiry:
                current_data["expires_at"] = (
                    datetime.utcnow() + timedelta(seconds=expire_time)
                ).isoformat()
            
            await self.redis.set(session_key, json.dumps(current_data), expire=expire_time)
            return True
        
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        try:
            session_key = self._get_session_key(session_id)
            
            # Get session data to find user ID
            session_data = await self.redis.get(session_key)
            if session_data:
                data = json.loads(session_data)
                user_id = data.get("user_id")
                
                # Remove from user's active sessions
                if user_id:
                    user_sessions_key = self._get_user_sessions_key(user_id)
                    await self.redis.srem(user_sessions_key, session_id)
            
            # Delete session
            result = await self.redis.delete(session_key)
            
            if result:
                logger.info(f"Deleted session {session_id}")
            
            return bool(result)
        
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    async def delete_user_sessions(self, user_id: UUID) -> int:
        """Delete all sessions for a user."""
        try:
            user_sessions_key = self._get_user_sessions_key(str(user_id))
            session_ids = await self.redis.smembers(user_sessions_key)
            
            deleted_count = 0
            for session_id in session_ids:
                if await self.delete_session(session_id):
                    deleted_count += 1
            
            # Clean up user sessions set
            await self.redis.delete(user_sessions_key)
            
            logger.info(f"Deleted {deleted_count} sessions for user {user_id}")
            return deleted_count
        
        except Exception as e:
            logger.error(f"Error deleting sessions for user {user_id}: {e}")
            return 0
    
    async def get_user_sessions(self, user_id: UUID) -> list[str]:
        """Get all active session IDs for a user."""
        try:
            user_sessions_key = self._get_user_sessions_key(str(user_id))
            session_ids = await self.redis.smembers(user_sessions_key)
            return list(session_ids)
        
        except Exception as e:
            logger.error(f"Error getting sessions for user {user_id}: {e}")
            return []
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (should be run periodically)."""
        try:
            redis_client = self.redis.get_redis()
            
            # Get all session keys
            session_keys = await redis_client.keys(f"{self.session_prefix}*")
            
            expired_count = 0
            for session_key in session_keys:
                session_data = await redis_client.get(session_key)
                if session_data:
                    try:
                        data = json.loads(session_data)
                        expires_at = datetime.fromisoformat(data["expires_at"])
                        
                        if datetime.utcnow() > expires_at:
                            session_id = session_key.replace(self.session_prefix, "")
                            await self.delete_session(session_id)
                            expired_count += 1
                    
                    except (json.JSONDecodeError, KeyError, ValueError):
                        # Invalid session data, delete it
                        await redis_client.delete(session_key)
                        expired_count += 1
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
            
            return expired_count
        
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0
    
    async def get_session_stats(self) -> Dict[str, int]:
        """Get session statistics."""
        try:
            redis_client = self.redis.get_redis()
            
            # Count total sessions
            session_keys = await redis_client.keys(f"{self.session_prefix}*")
            total_sessions = len(session_keys)
            
            # Count active sessions (not expired)
            active_sessions = 0
            for session_key in session_keys:
                session_data = await redis_client.get(session_key)
                if session_data:
                    try:
                        data = json.loads(session_data)
                        expires_at = datetime.fromisoformat(data["expires_at"])
                        if datetime.utcnow() <= expires_at:
                            active_sessions += 1
                    except (json.JSONDecodeError, KeyError, ValueError):
                        pass
            
            # Count unique users with sessions
            user_session_keys = await redis_client.keys(f"{self.user_sessions_prefix}*")
            unique_users = len(user_session_keys)
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "expired_sessions": total_sessions - active_sessions,
                "unique_users": unique_users
            }
        
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {
                "total_sessions": 0,
                "active_sessions": 0,
                "expired_sessions": 0,
                "unique_users": 0
            }
    
    async def extend_session(self, session_id: str, additional_seconds: int = None) -> bool:
        """Extend session expiration time."""
        try:
            session_key = self._get_session_key(session_id)
            session_data = await self.redis.get(session_key)
            
            if not session_data:
                return False
            
            data = json.loads(session_data)
            
            # Calculate new expiration time
            extend_by = additional_seconds or self.default_expire
            new_expires_at = datetime.utcnow() + timedelta(seconds=extend_by)
            data["expires_at"] = new_expires_at.isoformat()
            data["last_accessed"] = datetime.utcnow().isoformat()
            
            # Update session with new expiration
            await self.redis.set(session_key, json.dumps(data), expire=extend_by)
            
            # Update user sessions set expiration
            user_id = data.get("user_id")
            if user_id:
                user_sessions_key = self._get_user_sessions_key(user_id)
                await self.redis.expire(user_sessions_key, extend_by)
            
            logger.info(f"Extended session {session_id} by {extend_by} seconds")
            return True
        
        except Exception as e:
            logger.error(f"Error extending session {session_id}: {e}")
            return False
    
    async def is_session_valid(self, session_id: str) -> bool:
        """Check if session exists and is not expired."""
        session_data = await self.get_session(session_id)
        return session_data is not None
    
    async def get_session_user_id(self, session_id: str) -> Optional[str]:
        """Get user ID from session without full session data."""
        try:
            session_key = self._get_session_key(session_id)
            session_data = await self.redis.get(session_key)
            
            if session_data:
                data = json.loads(session_data)
                
                # Check if session is expired
                expires_at = datetime.fromisoformat(data["expires_at"])
                if datetime.utcnow() <= expires_at:
                    return data.get("user_id")
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting user ID from session {session_id}: {e}")
            return None
    
    async def set_session_data(self, session_id: str, key: str, value: Any) -> bool:
        """Set a specific data field in session."""
        try:
            session_key = self._get_session_key(session_id)
            session_data = await self.redis.get(session_key)
            
            if not session_data:
                return False
            
            data = json.loads(session_data)
            data["data"][key] = value
            data["last_accessed"] = datetime.utcnow().isoformat()
            
            # Keep existing expiration
            ttl = await self.redis.ttl(session_key)
            expire_time = ttl if ttl > 0 else self.default_expire
            
            await self.redis.set(session_key, json.dumps(data), expire=expire_time)
            return True
        
        except Exception as e:
            logger.error(f"Error setting session data for {session_id}: {e}")
            return False
    
    async def get_session_data(self, session_id: str, key: str) -> Any:
        """Get a specific data field from session."""
        session_data = await self.get_session(session_id)
        if session_data and "data" in session_data:
            return session_data["data"].get(key)
        return None


# Global session manager instance
session_manager = SessionManager()


# Utility functions
async def create_user_session(
    user_id: UUID,
    data: Optional[Dict[str, Any]] = None,
    expire_seconds: Optional[int] = None
) -> str:
    """Create a new session for user."""
    return await session_manager.create_session(user_id, data, expire_seconds)


async def get_user_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data by session ID."""
    return await session_manager.get_session(session_id)


async def update_user_session(
    session_id: str,
    data: Dict[str, Any],
    extend_expiry: bool = True
) -> bool:
    """Update session data."""
    return await session_manager.update_session(session_id, data, extend_expiry)


async def delete_user_session(session_id: str) -> bool:
    """Delete a session."""
    return await session_manager.delete_session(session_id)


async def logout_user(user_id: UUID) -> int:
    """Log out user by deleting all their sessions."""
    return await session_manager.delete_user_sessions(user_id)