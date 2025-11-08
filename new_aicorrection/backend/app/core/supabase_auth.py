"""Supabase Authentication integration."""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone

from supabase import create_client, Client
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SupabaseUser(BaseModel):
    """Supabase user model."""
    id: str
    email: Optional[str] = None
    email_confirmed_at: Optional[datetime] = None
    phone: Optional[str] = None
    phone_confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    last_sign_in_at: Optional[datetime] = None
    app_metadata: Dict = {}
    user_metadata: Dict = {}
    aud: str = ""
    role: str = ""


class SupabaseAuthManager:
    """Supabase Authentication manager."""
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[Client] = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize Supabase client."""
        if self._initialized:
            return True

        try:
            # Get Supabase configuration from environment
            supabase_url = getattr(self.settings, 'SUPABASE_URL', None)
            supabase_key = getattr(self.settings, 'SUPABASE_SERVICE_ROLE_KEY', None)
            
            if not supabase_url or not supabase_key:
                logger.warning("Supabase configuration not found - Supabase features will be disabled")
                return False

            # Initialize Supabase client
            self._client = create_client(supabase_url, supabase_key)
            self._initialized = True

            logger.info("Supabase client initialized successfully")
            return True

        except Exception as e:
            logger.warning(f"Failed to initialize Supabase client: {e} - Supabase features will be disabled")
            return False

    async def verify_token(self, access_token: str) -> Optional[SupabaseUser]:
        """Verify Supabase access token and return user information."""
        if not self._initialized:
            if not self.initialize():
                return None
        
        try:
            # Get user from Supabase using the access token
            response = self._client.auth.get_user(access_token)
            
            if not response.user:
                logger.warning("Invalid Supabase access token")
                return None
            
            user = response.user
            
            # Create SupabaseUser object
            supabase_user = SupabaseUser(
                id=user.id,
                email=user.email,
                email_confirmed_at=user.email_confirmed_at,
                phone=user.phone,
                phone_confirmed_at=user.phone_confirmed_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_sign_in_at=user.last_sign_in_at,
                app_metadata=user.app_metadata or {},
                user_metadata=user.user_metadata or {},
                aud=user.aud or "",
                role=user.role or ""
            )
            
            return supabase_user
            
        except Exception as e:
            logger.error(f"Error verifying Supabase token: {e}")
            return None

    async def create_user(self, email: str, password: str, user_metadata: Optional[Dict] = None) -> Optional[SupabaseUser]:
        """Create a new user in Supabase."""
        if not self._initialized:
            if not self.initialize():
                return None
        
        try:
            response = self._client.auth.admin.create_user({
                "email": email,
                "password": password,
                "user_metadata": user_metadata or {},
                "email_confirm": True  # Auto-confirm email for admin creation
            })
            
            if not response.user:
                return None
            
            user = response.user
            return SupabaseUser(
                id=user.id,
                email=user.email,
                email_confirmed_at=user.email_confirmed_at,
                phone=user.phone,
                phone_confirmed_at=user.phone_confirmed_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_sign_in_at=user.last_sign_in_at,
                app_metadata=user.app_metadata or {},
                user_metadata=user.user_metadata or {},
                aud=user.aud or "",
                role=user.role or ""
            )
            
        except Exception as e:
            logger.error(f"Error creating Supabase user: {e}")
            return None

    async def update_user(self, user_id: str, updates: Dict) -> Optional[SupabaseUser]:
        """Update user in Supabase."""
        if not self._initialized:
            if not self.initialize():
                return None
        
        try:
            response = self._client.auth.admin.update_user_by_id(user_id, updates)
            
            if not response.user:
                return None
            
            user = response.user
            return SupabaseUser(
                id=user.id,
                email=user.email,
                email_confirmed_at=user.email_confirmed_at,
                phone=user.phone,
                phone_confirmed_at=user.phone_confirmed_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_sign_in_at=user.last_sign_in_at,
                app_metadata=user.app_metadata or {},
                user_metadata=user.user_metadata or {},
                aud=user.aud or "",
                role=user.role or ""
            )
            
        except Exception as e:
            logger.error(f"Error updating Supabase user: {e}")
            return None

    async def delete_user(self, user_id: str) -> bool:
        """Delete user from Supabase."""
        if not self._initialized:
            if not self.initialize():
                return False
        
        try:
            self._client.auth.admin.delete_user(user_id)
            return True
            
        except Exception as e:
            logger.error(f"Error deleting Supabase user: {e}")
            return False

    async def get_user_by_id(self, user_id: str) -> Optional[SupabaseUser]:
        """Get user by ID from Supabase."""
        if not self._initialized:
            if not self.initialize():
                return None
        
        try:
            response = self._client.auth.admin.get_user_by_id(user_id)
            
            if not response.user:
                return None
            
            user = response.user
            return SupabaseUser(
                id=user.id,
                email=user.email,
                email_confirmed_at=user.email_confirmed_at,
                phone=user.phone,
                phone_confirmed_at=user.phone_confirmed_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_sign_in_at=user.last_sign_in_at,
                app_metadata=user.app_metadata or {},
                user_metadata=user.user_metadata or {},
                aud=user.aud or "",
                role=user.role or ""
            )
            
        except Exception as e:
            logger.error(f"Error getting Supabase user: {e}")
            return None

    async def list_users(self, page: int = 1, per_page: int = 50) -> List[SupabaseUser]:
        """List users from Supabase."""
        if not self._initialized:
            if not self.initialize():
                return []
        
        try:
            response = self._client.auth.admin.list_users(page=page, per_page=per_page)
            
            users = []
            for user in response:
                users.append(SupabaseUser(
                    id=user.id,
                    email=user.email,
                    email_confirmed_at=user.email_confirmed_at,
                    phone=user.phone,
                    phone_confirmed_at=user.phone_confirmed_at,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                    last_sign_in_at=user.last_sign_in_at,
                    app_metadata=user.app_metadata or {},
                    user_metadata=user.user_metadata or {},
                    aud=user.aud or "",
                    role=user.role or ""
                ))
            
            return users
            
        except Exception as e:
            logger.error(f"Error listing Supabase users: {e}")
            return []


# Global Supabase auth manager instance
supabase_auth_manager = SupabaseAuthManager()