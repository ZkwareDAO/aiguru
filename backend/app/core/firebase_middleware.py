"""Firebase Authentication middleware for FastAPI."""

import logging
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.firebase_auth import firebase_auth_manager, FirebaseUser

logger = logging.getLogger(__name__)


class FirebaseAuthBearer(HTTPBearer):
    """Firebase Authentication Bearer token handler."""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[FirebaseUser]:
        """Verify Firebase token and return user information."""
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
        
        # Verify Firebase token
        firebase_user = await firebase_auth_manager.verify_token(credentials.credentials)
        
        if not firebase_user:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        
        return firebase_user


# Global Firebase auth dependency
firebase_auth = FirebaseAuthBearer()
firebase_auth_optional = FirebaseAuthBearer(auto_error=False)


async def get_current_firebase_user(
    firebase_user: FirebaseUser = firebase_auth
) -> FirebaseUser:
    """Dependency to get current authenticated Firebase user."""
    return firebase_user


async def get_current_firebase_user_optional(
    firebase_user: Optional[FirebaseUser] = firebase_auth_optional
) -> Optional[FirebaseUser]:
    """Dependency to get current Firebase user (optional)."""
    return firebase_user


def require_firebase_role(required_role: str):
    """Decorator to require specific Firebase custom claim role."""
    def decorator(firebase_user: FirebaseUser = firebase_auth):
        user_role = firebase_user.custom_claims.get('role')
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}"
            )
        return firebase_user
    return decorator


def require_firebase_admin():
    """Decorator to require Firebase admin role."""
    return require_firebase_role('admin')


def require_firebase_teacher():
    """Decorator to require Firebase teacher role."""
    return require_firebase_role('teacher')


def require_firebase_student():
    """Decorator to require Firebase student role."""
    return require_firebase_role('student')
