"""Middleware for authentication and authorization."""

import time
from typing import Callable, Optional
from uuid import UUID

from fastapi import Request, Response, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.auth import auth_manager
from app.core.database import get_db_session
from app.core.permissions import PermissionManager, Permission
from app.models.user import User
from app.services.user_service import UserService


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication."""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/auth/login",
            "/auth/register",
            "/auth/forgot-password",
            "/auth/reset-password",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through authentication middleware."""
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Extract token from Authorization header
        authorization = request.headers.get("Authorization")
        scheme, token = get_authorization_scheme_param(authorization)
        
        if not authorization or scheme.lower() != "bearer":
            return Response(
                content='{"detail": "缺少认证令牌"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
                media_type="application/json"
            )
        
        # Verify token
        if await auth_manager.is_token_blacklisted(token):
            return Response(
                content='{"detail": "令牌已失效"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
                media_type="application/json"
            )
        
        token_data = auth_manager.verify_token(token)
        if not token_data or not token_data.user_id:
            return Response(
                content='{"detail": "无效的认证令牌"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
                media_type="application/json"
            )
        
        # Add user info to request state
        request.state.user_id = token_data.user_id
        request.state.user_email = token_data.email
        request.state.user_role = token_data.role
        request.state.token = token
        
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""
    
    def __init__(self, app, calls_per_minute: int = 60):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.window_size = 60  # 1 minute
        self.request_counts = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through rate limiting middleware."""
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean old entries
        cutoff_time = current_time - self.window_size
        self.request_counts = {
            ip: [(timestamp, count) for timestamp, count in requests 
                 if timestamp > cutoff_time]
            for ip, requests in self.request_counts.items()
        }
        
        # Count requests for this IP
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        # Add current request
        self.request_counts[client_ip].append((current_time, 1))
        
        # Check rate limit
        total_requests = sum(count for _, count in self.request_counts[client_ip])
        
        if total_requests > self.calls_per_minute:
            return Response(
                content='{"detail": "请求过于频繁，请稍后重试"}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json"
            )
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request details."""
        start_time = time.time()
        
        # Log request
        print(f"Request: {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        print(f"Response: {response.status_code} - {process_time:.3f}s")
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class PermissionMiddleware(BaseHTTPMiddleware):
    """Middleware for permission checking."""
    
    def __init__(self, app, permission_config: Optional[dict] = None):
        super().__init__(app)
        self.permission_config = permission_config or {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check permissions for protected endpoints."""
        # Skip if no user authenticated
        if not hasattr(request.state, "user_id"):
            return await call_next(request)
        
        # Check if this endpoint requires specific permissions
        path = request.url.path
        method = request.method.lower()
        
        required_permission = self.permission_config.get(f"{method}:{path}")
        if not required_permission:
            return await call_next(request)
        
        # Get user and check permission
        try:
            async for db in get_db_session():
                user_service = UserService(db)
                user_id = UUID(request.state.user_id)
                user = await user_service.get_user_by_id(user_id)
                
                if not user:
                    return Response(
                        content='{"detail": "用户不存在"}',
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        media_type="application/json"
                    )
                
                permission_manager = PermissionManager(db)
                
                if not permission_manager.has_permission(user, required_permission):
                    return Response(
                        content='{"detail": "权限不足"}',
                        status_code=status.HTTP_403_FORBIDDEN,
                        media_type="application/json"
                    )
                
                break
        
        except Exception as e:
            return Response(
                content='{"detail": "权限验证失败"}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="application/json"
            )
        
        return await call_next(request)


class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware."""
    
    def __init__(
        self,
        app,
        allow_origins: list = None,
        allow_methods: list = None,
        allow_headers: list = None,
        allow_credentials: bool = True
    ):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle CORS headers."""
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)
        
        # Add CORS headers
        origin = request.headers.get("origin")
        if origin and (origin in self.allow_origins or "*" in self.allow_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response