"""Cache and session utility functions for common operations."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from app.core.cache import cache_manager
from app.core.session import session_manager

logger = logging.getLogger(__name__)


class CacheKeys:
    """Centralized cache key management."""
    
    # User-related cache keys
    USER_PROFILE = "user:profile:{user_id}"
    USER_CLASSES = "user:classes:{user_id}"
    USER_ASSIGNMENTS = "user:assignments:{user_id}"
    USER_SUBMISSIONS = "user:submissions:{user_id}"
    USER_ANALYTICS = "user:analytics:{user_id}"
    
    # Class-related cache keys
    CLASS_INFO = "class:info:{class_id}"
    CLASS_STUDENTS = "class:students:{class_id}"
    CLASS_ASSIGNMENTS = "class:assignments:{class_id}"
    CLASS_STATS = "class:stats:{class_id}"
    
    # Assignment-related cache keys
    ASSIGNMENT_INFO = "assignment:info:{assignment_id}"
    ASSIGNMENT_SUBMISSIONS = "assignment:submissions:{assignment_id}"
    ASSIGNMENT_STATS = "assignment:stats:{assignment_id}"
    
    # Grading-related cache keys
    GRADING_TASK = "grading:task:{task_id}"
    GRADING_RESULT = "grading:result:{task_id}"
    GRADING_QUEUE = "grading:queue"
    
    # Analytics cache keys
    ANALYTICS_STUDENT_REPORT = "analytics:student:{student_id}:{period}"
    ANALYTICS_CLASS_PERFORMANCE = "analytics:class:{class_id}:{period}"
    ANALYTICS_ERROR_PATTERNS = "analytics:errors:{student_id}"
    
    # AI Agent cache keys
    AI_CHAT_CONTEXT = "ai:context:{user_id}"
    AI_LEARNING_ANALYSIS = "ai:analysis:{user_id}"
    AI_STUDY_PLAN = "ai:plan:{user_id}"


class CacheService:
    """High-level cache service for application-specific operations."""
    
    def __init__(self):
        self.cache = cache_manager
        self.keys = CacheKeys()
    
    # User caching methods
    async def cache_user_profile(self, user_id: str, profile_data: dict) -> bool:
        """Cache user profile data."""
        key = self.keys.USER_PROFILE.format(user_id=user_id)
        return await self.cache.redis.set(key, profile_data, expire=self.cache.DEFAULT_EXPIRE)
    
    async def get_user_profile(self, user_id: str) -> Optional[dict]:
        """Get cached user profile."""
        key = self.keys.USER_PROFILE.format(user_id=user_id)
        cached_data = await self.cache.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    async def invalidate_user_profile(self, user_id: str) -> bool:
        """Invalidate user profile cache."""
        key = self.keys.USER_PROFILE.format(user_id=user_id)
        return await self.cache.redis.delete(key)
    
    async def cache_user_classes(self, user_id: str, classes_data: list) -> bool:
        """Cache user's classes."""
        key = self.keys.USER_CLASSES.format(user_id=user_id)
        return await self.cache.redis.set(key, classes_data, expire=self.cache.DEFAULT_EXPIRE)
    
    async def get_user_classes(self, user_id: str) -> Optional[list]:
        """Get cached user classes."""
        key = self.keys.USER_CLASSES.format(user_id=user_id)
        cached_data = await self.cache.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    # Class caching methods
    async def cache_class_info(self, class_id: str, class_data: dict) -> bool:
        """Cache class information."""
        key = self.keys.CLASS_INFO.format(class_id=class_id)
        return await self.cache.redis.set(key, class_data, expire=self.cache.DEFAULT_EXPIRE)
    
    async def get_class_info(self, class_id: str) -> Optional[dict]:
        """Get cached class information."""
        key = self.keys.CLASS_INFO.format(class_id=class_id)
        cached_data = await self.cache.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    async def cache_class_students(self, class_id: str, students_data: list) -> bool:
        """Cache class students list."""
        key = self.keys.CLASS_STUDENTS.format(class_id=class_id)
        return await self.cache.redis.set(key, students_data, expire=self.cache.DEFAULT_EXPIRE)
    
    async def get_class_students(self, class_id: str) -> Optional[list]:
        """Get cached class students."""
        key = self.keys.CLASS_STUDENTS.format(class_id=class_id)
        cached_data = await self.cache.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    # Assignment caching methods
    async def cache_assignment_info(self, assignment_id: str, assignment_data: dict) -> bool:
        """Cache assignment information."""
        key = self.keys.ASSIGNMENT_INFO.format(assignment_id=assignment_id)
        return await self.cache.redis.set(key, assignment_data, expire=self.cache.DEFAULT_EXPIRE)
    
    async def get_assignment_info(self, assignment_id: str) -> Optional[dict]:
        """Get cached assignment information."""
        key = self.keys.ASSIGNMENT_INFO.format(assignment_id=assignment_id)
        cached_data = await self.cache.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    # Grading caching methods
    async def cache_grading_task(self, task_id: str, task_data: dict) -> bool:
        """Cache grading task information."""
        key = self.keys.GRADING_TASK.format(task_id=task_id)
        return await self.cache.redis.set(key, task_data, expire=self.cache.LONG_EXPIRE)
    
    async def get_grading_task(self, task_id: str) -> Optional[dict]:
        """Get cached grading task."""
        key = self.keys.GRADING_TASK.format(task_id=task_id)
        cached_data = await self.cache.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    async def cache_grading_result(self, task_id: str, result_data: dict) -> bool:
        """Cache grading result."""
        key = self.keys.GRADING_RESULT.format(task_id=task_id)
        return await self.cache.redis.set(key, result_data, expire=self.cache.LONG_EXPIRE)
    
    async def get_grading_result(self, task_id: str) -> Optional[dict]:
        """Get cached grading result."""
        key = self.keys.GRADING_RESULT.format(task_id=task_id)
        cached_data = await self.cache.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    # Analytics caching methods
    async def cache_student_report(self, student_id: str, period: str, report_data: dict) -> bool:
        """Cache student analytics report."""
        key = self.keys.ANALYTICS_STUDENT_REPORT.format(student_id=student_id, period=period)
        return await self.cache.redis.set(key, report_data, expire=self.cache.SHORT_EXPIRE)
    
    async def get_student_report(self, student_id: str, period: str) -> Optional[dict]:
        """Get cached student report."""
        key = self.keys.ANALYTICS_STUDENT_REPORT.format(student_id=student_id, period=period)
        cached_data = await self.cache.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    # AI Agent caching methods
    async def cache_ai_context(self, user_id: str, context_data: dict) -> bool:
        """Cache AI conversation context."""
        key = self.keys.AI_CHAT_CONTEXT.format(user_id=user_id)
        return await self.cache.redis.set(key, context_data, expire=self.cache.DEFAULT_EXPIRE)
    
    async def get_ai_context(self, user_id: str) -> Optional[dict]:
        """Get cached AI context."""
        key = self.keys.AI_CHAT_CONTEXT.format(user_id=user_id)
        cached_data = await self.cache.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    # Bulk invalidation methods
    async def invalidate_user_cache(self, user_id: str) -> int:
        """Invalidate all cache entries for a user."""
        patterns = [
            f"user:*:{user_id}",
            f"user:{user_id}:*",
            f"ai:*:{user_id}",
            f"analytics:*:{user_id}*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.cache.invalidate_pattern(pattern)
            total_deleted += deleted
        
        return total_deleted
    
    async def invalidate_class_cache(self, class_id: str) -> int:
        """Invalidate all cache entries for a class."""
        patterns = [
            f"class:*:{class_id}",
            f"class:{class_id}:*",
            f"analytics:class:{class_id}*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.cache.invalidate_pattern(pattern)
            total_deleted += deleted
        
        return total_deleted
    
    async def invalidate_assignment_cache(self, assignment_id: str) -> int:
        """Invalidate all cache entries for an assignment."""
        patterns = [
            f"assignment:*:{assignment_id}",
            f"assignment:{assignment_id}:*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.cache.invalidate_pattern(pattern)
            total_deleted += deleted
        
        return total_deleted


class SessionService:
    """High-level session service for application-specific operations."""
    
    def __init__(self):
        self.session = session_manager
    
    async def create_authenticated_session(
        self,
        user_id: UUID,
        user_role: str,
        additional_data: Optional[dict] = None
    ) -> str:
        """Create a session with authentication context."""
        session_data = {
            "role": user_role,
            "login_time": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            **(additional_data or {})
        }
        
        return await self.session.create_session(user_id, session_data)
    
    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp."""
        return await self.session.set_session_data(
            session_id,
            "last_activity",
            datetime.utcnow().isoformat()
        )
    
    async def get_session_user_role(self, session_id: str) -> Optional[str]:
        """Get user role from session."""
        return await self.session.get_session_data(session_id, "role")
    
    async def is_session_expired(self, session_id: str) -> bool:
        """Check if session is expired."""
        session_data = await self.session.get_session(session_id)
        if not session_data:
            return True
        
        try:
            expires_at = datetime.fromisoformat(session_data["expires_at"])
            return datetime.utcnow() > expires_at
        except (KeyError, ValueError):
            return True
    
    async def extend_user_session(self, session_id: str, minutes: int = 30) -> bool:
        """Extend session by specified minutes."""
        return await self.session.extend_session(session_id, minutes * 60)
    
    async def logout_all_user_sessions(self, user_id: UUID) -> int:
        """Log out all sessions for a user."""
        return await self.session.delete_user_sessions(user_id)


# Global service instances
cache_service = CacheService()
session_service = SessionService()


# Utility functions for easy access
async def cache_user_data(user_id: str, data_type: str, data: Any, expire: Optional[int] = None) -> bool:
    """Generic function to cache user-related data."""
    key = f"user:{data_type}:{user_id}"
    return await cache_manager.redis.set(key, data, expire=expire or cache_manager.DEFAULT_EXPIRE)


async def get_user_data(user_id: str, data_type: str) -> Optional[Any]:
    """Generic function to get cached user data."""
    key = f"user:{data_type}:{user_id}"
    cached_data = await cache_manager.redis.get(key)
    if cached_data:
        try:
            return json.loads(cached_data)
        except (json.JSONDecodeError, TypeError):
            return cached_data
    return None


async def invalidate_user_data(user_id: str, data_type: Optional[str] = None) -> int:
    """Invalidate user data cache."""
    if data_type:
        key = f"user:{data_type}:{user_id}"
        return await cache_manager.redis.delete(key)
    else:
        pattern = f"user:*:{user_id}"
        return await cache_manager.invalidate_pattern(pattern)


async def create_user_session_with_context(
    user_id: UUID,
    user_role: str,
    context: Optional[dict] = None
) -> str:
    """Create a user session with additional context."""
    return await session_service.create_authenticated_session(user_id, user_role, context)


async def validate_and_refresh_session(session_id: str) -> Optional[dict]:
    """Validate session and refresh activity timestamp."""
    session_data = await session_manager.get_session(session_id)
    if session_data:
        await session_service.update_session_activity(session_id)
    return session_data