"""Application configuration settings."""

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Environment
    ENVIRONMENT: str = Field(default="development", description="Application environment")
    
    # Application settings
    APP_NAME: str = "AI Education Backend"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Security settings
    SECRET_KEY: str = Field(..., min_length=32, description="Application secret key")
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: str = "*"
    
    # Database settings
    DATABASE_URL: Optional[str] = None
    DATABASE_ECHO: bool = False
    
    # Redis settings
    REDIS_URL: Optional[str] = None
    
    # JWT settings
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # AI service settings
    OPENAI_API_KEY: Optional[str] = None
    AI_GRADING_API_URL: Optional[str] = None
    AI_GRADING_API_KEY: Optional[str] = None
    
    # File storage settings
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # Email settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True

    # Firebase settings
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_CLIENT_EMAIL: Optional[str] = None
    FIREBASE_PRIVATE_KEY: Optional[str] = None
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> str:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return v
        elif isinstance(v, list):
            return ",".join(v)
        return "*"
        raise ValueError(v)
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_allowed_hosts(cls, v: Any) -> List[str]:
        """Parse allowed hosts from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @model_validator(mode="after")
    def validate_environment_config(self) -> "Settings":
        """Validate environment-specific configuration."""
        if self.ENVIRONMENT == "production":
            # Production environment validations
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
            if self.SECRET_KEY == "your-super-secret-key-change-this-in-production":
                raise ValueError("SECRET_KEY must be changed in production")
            if self.JWT_SECRET_KEY == "your-jwt-secret-key-change-this-in-production":
                raise ValueError("JWT_SECRET_KEY must be changed in production")
        
        return self
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT == "testing"


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()