"""Authentication utilities for JWT token management."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.redis import get_redis


class TokenData(BaseModel):
    """Token data model."""
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthManager:
    """Authentication manager for JWT tokens and password hashing."""
    
    def __init__(self):
        self.settings = get_settings()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.algorithm = self.settings.JWT_ALGORITHM
        self.secret_key = self.settings.JWT_SECRET_KEY
        self.access_token_expire_minutes = self.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = self.settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash."""
        return self.pwd_context.hash(password)
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.access_token_expire_minutes
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                days=self.refresh_token_expire_days
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_token_pair(
        self,
        user_id: Union[str, UUID],
        email: str,
        role: str
    ) -> TokenResponse:
        """Create access and refresh token pair."""
        user_id_str = str(user_id)
        
        # Create token data
        token_data = {
            "sub": user_id_str,
            "email": email,
            "role": role
        }
        
        # Create tokens
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token({"sub": user_id_str})
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60
        )
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[TokenData]:
        """Verify JWT token and return token data."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != token_type:
                return None
            
            # Check expiration
            exp = payload.get("exp")
            if exp is None or datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                return None
            
            # Extract user data
            user_id = payload.get("sub")
            if user_id is None:
                return None
            
            return TokenData(
                user_id=user_id,
                email=payload.get("email"),
                role=payload.get("role")
            )
        
        except JWTError:
            return None
    
    async def blacklist_token(self, token: str) -> bool:
        """Add token to blacklist."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            exp = payload.get("exp")
            
            if exp is None:
                return False
            
            # Calculate TTL for Redis (time until token expires)
            expire_time = datetime.fromtimestamp(exp, tz=timezone.utc)
            ttl = int((expire_time - datetime.now(timezone.utc)).total_seconds())
            
            if ttl > 0:
                redis_client = await get_redis()
                await redis_client.setex(f"blacklist:{token}", ttl, "1")
                return True
            
            return False
        
        except JWTError:
            return False
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        try:
            redis_client = await get_redis()
            result = await redis_client.get(f"blacklist:{token}")
            return result is not None
        except Exception:
            # If Redis is not available, assume token is not blacklisted
            return False
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Create new access token from refresh token."""
        token_data = self.verify_token(refresh_token, token_type="refresh")
        
        if token_data is None or token_data.user_id is None:
            return None
        
        # Check if refresh token is blacklisted
        if await self.is_token_blacklisted(refresh_token):
            return None
        
        # Create new access token (we'll need to get user data from database)
        # For now, create with minimal data - this will be enhanced in the service layer
        new_token_data = {"sub": token_data.user_id}
        return self.create_access_token(new_token_data)
    
    def validate_password_strength(self, password: str) -> tuple[bool, str]:
        """Validate password strength."""
        if len(password) < 8:
            return False, "密码长度至少8位"
        
        if not any(c.isupper() for c in password):
            return False, "密码必须包含至少一个大写字母"
        
        if not any(c.islower() for c in password):
            return False, "密码必须包含至少一个小写字母"
        
        if not any(c.isdigit() for c in password):
            return False, "密码必须包含至少一个数字"
        
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "密码必须包含至少一个特殊字符"
        
        return True, "密码强度符合要求"


# Global auth manager instance
auth_manager = AuthManager()