"""Authentication API endpoints."""

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import auth_manager, TokenData
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_user_token
from app.core.firebase_auth import firebase_auth_manager, FirebaseUser
from app.models.user import User
from app.schemas.user import (
    UserLogin,
    UserRegister,
    TokenResponse,
    TokenRefresh,
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
    UserResponse,
    EmailVerification,
    FirebaseAuthRequest,
    FirebaseAuthResponse
)
from app.services.user_service import UserService
from app.services.password_service import PasswordService


router = APIRouter(prefix="/auth", tags=["认证"])
security = HTTPBearer()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """用户注册."""
    user_service = UserService(db)
    
    try:
        # Create user
        user = await user_service.create_user(user_data)
        
        # Generate tokens
        token_response = auth_manager.create_token_pair(
            user_id=user.id,
            email=user.email,
            role=user.role.value
        )
        
        # Return response with user data
        return TokenResponse(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            token_type=token_response.token_type,
            expires_in=token_response.expires_in,
            user=UserResponse.model_validate(user)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """用户登录."""
    user_service = UserService(db)
    
    # Authenticate user
    user = await user_service.authenticate_user(
        email=login_data.email,
        password=login_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate tokens
    token_response = auth_manager.create_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.role.value
    )
    
    return TokenResponse(
        access_token=token_response.access_token,
        refresh_token=token_response.refresh_token,
        token_type=token_response.token_type,
        expires_in=token_response.expires_in,
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    refresh_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """刷新访问令牌."""
    # Verify refresh token
    token_data = auth_manager.verify_token(
        refresh_data.refresh_token,
        token_type="refresh"
    )
    
    if not token_data or not token_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if refresh token is blacklisted
    if await auth_manager.is_token_blacklisted(refresh_data.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已失效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user data
    user_service = UserService(db)
    try:
        from uuid import UUID
        user_id = UUID(token_data.user_id)
        user = await user_service.get_user_by_id(user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被禁用",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Generate new token pair
        new_token_response = auth_manager.create_token_pair(
            user_id=user.id,
            email=user.email,
            role=user.role.value
        )
        
        # Blacklist old refresh token
        await auth_manager.blacklist_token(refresh_data.refresh_token)
        
        return {
            "access_token": new_token_response.access_token,
            "refresh_token": new_token_response.refresh_token,
            "token_type": new_token_response.token_type,
            "expires_in": new_token_response.expires_in
        }
    
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的用户ID",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, str]:
    """用户登出."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Blacklist the token
    success = await auth_manager.blacklist_token(token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="登出失败"
        )
    
    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """获取当前用户信息."""
    return UserResponse.model_validate(current_user)


@router.put("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """修改密码."""
    password_service = PasswordService(db)
    
    try:
        success = await password_service.change_password_with_history(
            user_id=current_user.id,
            old_password=password_data.old_password,
            new_password=password_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="原密码错误"
            )
        
        return {"message": "密码修改成功"}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/forgot-password")
async def forgot_password(
    reset_data: PasswordReset,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """忘记密码 - 发送重置邮件."""
    password_service = PasswordService(db)
    
    # Generate reset token
    reset_token = await password_service.generate_reset_token(reset_data.email)
    
    # Always return success to prevent email enumeration
    # In a real implementation, you would send an email with the reset_token here
    # For now, we'll just return a success message
    
    return {"message": "如果该邮箱已注册，您将收到密码重置邮件"}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """重置密码确认."""
    password_service = PasswordService(db)
    
    try:
        success = await password_service.reset_password_with_token(
            token=reset_data.token,
            new_password=reset_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效或已过期的重置令牌"
            )
        
        return {"message": "密码重置成功"}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/verify-email")
async def verify_email(
    verification_data: EmailVerification,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """验证邮箱."""
    password_service = PasswordService(db)
    
    success = await password_service.verify_email_with_token(verification_data.token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效或已过期的验证令牌"
        )
    
    return {"message": "邮箱验证成功"}


@router.get("/validate-token")
async def validate_token(
    token_data: TokenData = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """验证令牌有效性."""
    return {
        "valid": True,
        "user_id": token_data.user_id,
        "email": token_data.email,
        "role": token_data.role
    }


@router.post("/check-password-strength")
async def check_password_strength(
    password_data: Dict[str, str],
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """检查密码强度."""
    password = password_data.get("password", "")
    
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码不能为空"
        )
    
    password_service = PasswordService(db)
    
    strength_info = await password_service.get_password_strength_score(password)
    is_compromised = await password_service.is_password_compromised(password)
    
    return {
        **strength_info,
        "is_compromised": is_compromised,
        "compromised_warning": "此密码可能已在数据泄露中出现" if is_compromised else None
    }


@router.post("/generate-password")
async def generate_secure_password(
    length_data: Dict[str, int] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """生成安全密码."""
    length = 12
    if length_data and "length" in length_data:
        length = max(8, min(32, length_data["length"]))
    
    password_service = PasswordService(db)
    secure_password = await password_service.generate_secure_password(length)
    
    return {"password": secure_password}


@router.post("/send-verification-email")
async def send_verification_email(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """发送邮箱验证邮件."""
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已经验证过了"
        )
    
    password_service = PasswordService(db)
    
    verification_token = await password_service.generate_email_verification_token(
        current_user.id
    )
    
    # In a real implementation, you would send an email with the verification_token here
    # For now, we'll just return a success message

    return {"message": "验证邮件已发送，请检查您的邮箱"}


@router.post("/firebase", response_model=FirebaseAuthResponse)
async def firebase_auth(
    auth_request: FirebaseAuthRequest,
    db: AsyncSession = Depends(get_db)
) -> FirebaseAuthResponse:
    """Firebase认证登录/注册."""
    try:
        # 验证Firebase token
        firebase_user = await firebase_auth_manager.verify_token(auth_request.firebase_token)

        if not firebase_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的Firebase令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_service = UserService(db)

        # 检查用户是否已存在
        user = await user_service.get_user_by_firebase_uid(firebase_user.uid)
        is_new_user = False

        if not user:
            # 创建新用户
            user = await user_service.create_firebase_user(firebase_user)
            is_new_user = True
        else:
            # 更新用户信息（如果需要）
            if user.email != firebase_user.email or user.name != firebase_user.name:
                user = await user_service.update_firebase_user(user, firebase_user)

        # 生成JWT令牌
        token_response = auth_manager.create_token_pair(
            user_id=user.id,
            email=user.email,
            role=user.role.value
        )

        return FirebaseAuthResponse(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            token_type=token_response.token_type,
            expires_in=token_response.expires_in,
            user=UserResponse.model_validate(user),
            is_new_user=is_new_user
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Firebase认证失败，请稍后重试"
        )