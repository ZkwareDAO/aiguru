"""Supabase Authentication middleware for FastAPI."""

import logging
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.supabase_auth import supabase_auth_manager, SupabaseUser

logger = logging.getLogger(__name__)


class SupabaseAuthBearer(HTTPBearer):
    """Supabase Authentication Bearer token handler."""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[SupabaseUser]:
        """Verify Supabase token and return user information."""
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        
        if credentials.scheme != "Bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        
        # Verify Supabase token
        supabase_user = await supabase_auth_manager.verify_token(credentials.credentials)
        
        if not supabase_user:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        
        return supabase_user


# Global Supabase auth dependency
supabase_auth = SupabaseAuthBearer()
supabase_auth_optional = SupabaseAuthBearer(auto_error=False)


async def get_current_supabase_user(
    supabase_user: SupabaseUser = supabase_auth
) -> SupabaseUser:
    """Dependency to get current authenticated Supabase user."""
    return supabase_user


async def get_current_supabase_user_optional(
    supabase_user: Optional[SupabaseUser] = supabase_auth_optional
) -> Optional[SupabaseUser]:
    """Dependency to get current authenticated Supabase user (optional)."""
    return supabase_user