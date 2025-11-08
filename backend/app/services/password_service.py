"""Password management service."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import auth_manager
from app.core.redis import get_redis
from app.services.user_service import UserService


class PasswordService:
    """Service for password management operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_service = UserService(db)
    
    async def generate_reset_token(self, email: str) -> Optional[str]:
        """Generate password reset token."""
        user = await self.user_service.get_user_by_email(email)
        if not user:
            return None
        
        # Generate secure random token
        reset_token = secrets.token_urlsafe(32)
        
        # Store token in Redis with expiration (15 minutes)
        redis_client = await get_redis()
        await redis_client.setex(
            f"password_reset:{reset_token}",
            900,  # 15 minutes
            str(user.id)
        )
        
        return reset_token
    
    async def verify_reset_token(self, token: str) -> Optional[UUID]:
        """Verify password reset token and return user ID."""
        try:
            redis_client = await get_redis()
            user_id_str = await redis_client.get(f"password_reset:{token}")
            
            if user_id_str is None:
                return None
            
            return UUID(user_id_str.decode() if isinstance(user_id_str, bytes) else user_id_str)
        
        except Exception:
            return None
    
    async def consume_reset_token(self, token: str) -> Optional[UUID]:
        """Consume password reset token (delete after use)."""
        user_id = await self.verify_reset_token(token)
        
        if user_id:
            # Delete token from Redis
            redis_client = await get_redis()
            await redis_client.delete(f"password_reset:{token}")
        
        return user_id
    
    async def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Reset password using reset token."""
        user_id = await self.consume_reset_token(token)
        
        if not user_id:
            return False
        
        return await self.user_service.reset_password(user_id, new_password)
    
    async def generate_email_verification_token(self, user_id: UUID) -> str:
        """Generate email verification token."""
        # Generate secure random token
        verification_token = secrets.token_urlsafe(32)
        
        # Store token in Redis with expiration (24 hours)
        redis_client = await get_redis()
        await redis_client.setex(
            f"email_verification:{verification_token}",
            86400,  # 24 hours
            str(user_id)
        )
        
        return verification_token
    
    async def verify_email_token(self, token: str) -> Optional[UUID]:
        """Verify email verification token and return user ID."""
        try:
            redis_client = await get_redis()
            user_id_str = await redis_client.get(f"email_verification:{token}")
            
            if user_id_str is None:
                return None
            
            return UUID(user_id_str.decode() if isinstance(user_id_str, bytes) else user_id_str)
        
        except Exception:
            return None
    
    async def consume_email_verification_token(self, token: str) -> Optional[UUID]:
        """Consume email verification token (delete after use)."""
        user_id = await self.verify_email_token(token)
        
        if user_id:
            # Delete token from Redis
            redis_client = await get_redis()
            await redis_client.delete(f"email_verification:{token}")
        
        return user_id
    
    async def verify_email_with_token(self, token: str) -> bool:
        """Verify email using verification token."""
        user_id = await self.consume_email_verification_token(token)
        
        if not user_id:
            return False
        
        return await self.user_service.verify_user_email(user_id)
    
    async def check_password_history(self, user_id: UUID, new_password: str) -> bool:
        """Check if password was used recently (prevent reuse)."""
        # Get password history from Redis
        redis_client = await get_redis()
        history_key = f"password_history:{user_id}"
        
        # Get last 5 password hashes
        password_hashes = await redis_client.lrange(history_key, 0, 4)
        
        # Check if new password matches any recent password
        for hash_bytes in password_hashes:
            hash_str = hash_bytes.decode() if isinstance(hash_bytes, bytes) else hash_bytes
            if auth_manager.verify_password(new_password, hash_str):
                return False  # Password was used recently
        
        return True  # Password is new
    
    async def add_password_to_history(self, user_id: UUID, password_hash: str) -> None:
        """Add password hash to history."""
        redis_client = await get_redis()
        history_key = f"password_history:{user_id}"
        
        # Add new password hash to the beginning of the list
        await redis_client.lpush(history_key, password_hash)
        
        # Keep only last 5 passwords
        await redis_client.ltrim(history_key, 0, 4)
        
        # Set expiration for the history (1 year)
        await redis_client.expire(history_key, 31536000)
    
    async def change_password_with_history(
        self,
        user_id: UUID,
        old_password: str,
        new_password: str
    ) -> bool:
        """Change password with history checking."""
        # Verify old password first
        user = await self.user_service.get_user_by_id(user_id)
        if not user or not auth_manager.verify_password(old_password, user.password_hash):
            return False
        
        # Check if new password was used recently
        if not await self.check_password_history(user_id, new_password):
            raise ValueError("不能使用最近使用过的密码")
        
        # Validate new password strength
        is_valid, message = auth_manager.validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(message)
        
        # Change password
        success = await self.user_service.change_password(user_id, old_password, new_password)
        
        if success:
            # Add old password to history
            await self.add_password_to_history(user_id, user.password_hash)
        
        return success
    
    async def get_password_strength_score(self, password: str) -> dict:
        """Get password strength score and recommendations."""
        score = 0
        recommendations = []
        
        # Length check
        if len(password) >= 8:
            score += 20
        else:
            recommendations.append("密码长度至少8位")
        
        if len(password) >= 12:
            score += 10
        
        # Character variety checks
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if has_upper:
            score += 15
        else:
            recommendations.append("添加大写字母")
        
        if has_lower:
            score += 15
        else:
            recommendations.append("添加小写字母")
        
        if has_digit:
            score += 15
        else:
            recommendations.append("添加数字")
        
        if has_special:
            score += 15
        else:
            recommendations.append("添加特殊字符")
        
        # Bonus for variety
        variety_count = sum([has_upper, has_lower, has_digit, has_special])
        if variety_count >= 3:
            score += 10
        
        # Common patterns penalty
        common_patterns = ["123", "abc", "password", "qwerty"]
        for pattern in common_patterns:
            if pattern.lower() in password.lower():
                score -= 10
                recommendations.append(f"避免使用常见模式: {pattern}")
        
        # Determine strength level
        if score >= 80:
            strength = "强"
        elif score >= 60:
            strength = "中等"
        elif score >= 40:
            strength = "弱"
        else:
            strength = "很弱"
        
        return {
            "score": max(0, min(100, score)),
            "strength": strength,
            "recommendations": recommendations
        }
    
    async def is_password_compromised(self, password: str) -> bool:
        """Check if password appears in known breach databases."""
        # This would integrate with services like HaveIBeenPwned
        # For now, just check against common passwords
        common_passwords = [
            "password", "123456", "password123", "admin", "qwerty",
            "letmein", "welcome", "monkey", "dragon", "master"
        ]
        
        return password.lower() in common_passwords
    
    async def generate_secure_password(self, length: int = 12) -> str:
        """Generate a secure random password."""
        import string
        
        # Ensure we have at least one character from each category
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        special = "!@#$%^&*()_+-="
        
        # Start with one character from each category
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # Fill the rest randomly
        all_chars = uppercase + lowercase + digits + special
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)