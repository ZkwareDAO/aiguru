"""Test configuration loader."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.config_loader import (
    get_config_for_environment,
    load_environment_config,
    validate_required_settings,
)


def test_load_environment_config():
    """Test loading environment-specific configuration."""
    with patch.dict(os.environ, {}, clear=True):
        # Set minimal required environment variables
        os.environ.update({
            "SECRET_KEY": "test-secret-key-32-characters-long",
            "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters"
        })
        
        load_environment_config("development")
        
        # Should load development environment
        assert os.getenv("ENVIRONMENT") == "development"


def test_get_config_for_environment():
    """Test getting configuration for specific environment."""
    with patch.dict(os.environ, {
        "SECRET_KEY": "test-secret-key-32-characters-long",
        "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters"
    }):
        config = get_config_for_environment("development")
        
        assert config.ENVIRONMENT == "development"
        assert config.DEBUG is True


def test_validate_required_settings_development():
    """Test validation passes for development environment."""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "development",
        "SECRET_KEY": "test-secret-key-32-characters-long",
        "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters"
    }):
        # Should not raise any exception
        validate_required_settings()


def test_validate_required_settings_production_missing():
    """Test validation fails for production with missing settings."""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "test-secret-key-32-characters-long",
        "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters"
        # Missing DATABASE_URL
    }):
        with pytest.raises(ValueError, match="Missing required production settings"):
            validate_required_settings()