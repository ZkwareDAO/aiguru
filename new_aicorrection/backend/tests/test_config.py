"""Test configuration settings."""

import os
from unittest.mock import patch

import pytest

from app.core.config import Settings, get_settings


def test_settings_default_values():
    """Test default configuration values."""
    with patch.dict(os.environ, {
        "SECRET_KEY": "test-secret-key-32-characters-long",
        "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters"
    }):
        settings = Settings()
        assert settings.APP_NAME == "AI Education Backend"
        assert settings.DEBUG is False
        assert settings.LOG_LEVEL == "INFO"
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 8000
        assert settings.ENVIRONMENT == "development"


def test_settings_from_env():
    """Test configuration from environment variables."""
    env_vars = {
        "SECRET_KEY": "test-secret-key-32-characters-long",
        "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters",
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
        "PORT": "9000"
    }
    
    with patch.dict(os.environ, env_vars):
        settings = Settings()
        assert settings.DEBUG is True
        assert settings.LOG_LEVEL == "DEBUG"
        assert settings.PORT == 9000


def test_cors_origins_parsing():
    """Test CORS origins parsing from string."""
    env_vars = {
        "SECRET_KEY": "test-secret-key-32-characters-long",
        "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters",
        "CORS_ORIGINS": "http://localhost:3000,https://example.com"
    }
    
    with patch.dict(os.environ, env_vars):
        settings = Settings()
        assert settings.CORS_ORIGINS == ["http://localhost:3000", "https://example.com"]


def test_get_settings_cached():
    """Test that get_settings returns cached instance."""
    with patch.dict(os.environ, {
        "SECRET_KEY": "test-secret-key-32-characters-long",
        "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters"
    }):
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2