"""Configuration loader utilities."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from app.core.config import Settings


def load_environment_config(environment: Optional[str] = None) -> None:
    """Load environment-specific configuration files."""
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")
    
    # Base directory for config files
    config_dir = Path(__file__).parent.parent.parent / "config"
    
    # Load base .env file if it exists
    base_env_file = Path(".env")
    if base_env_file.exists():
        load_dotenv(base_env_file)
    
    # Load environment-specific config file
    env_file = config_dir / f"{environment}.env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
    
    # Load local overrides if they exist
    local_env_file = Path(f".env.{environment}.local")
    if local_env_file.exists():
        load_dotenv(local_env_file, override=True)


def get_config_for_environment(environment: str) -> Settings:
    """Get configuration for a specific environment."""
    # Save current environment
    original_env = os.environ.copy()
    
    try:
        # Load environment-specific config
        load_environment_config(environment)
        
        # Create settings instance
        settings = Settings()
        
        return settings
    
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def validate_required_settings() -> None:
    """Validate that all required settings are present."""
    settings = Settings()
    
    required_for_production = [
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "DATABASE_URL",
    ]
    
    if settings.is_production:
        missing_settings = []
        for setting in required_for_production:
            if not getattr(settings, setting, None):
                missing_settings.append(setting)
        
        if missing_settings:
            raise ValueError(
                f"Missing required production settings: {', '.join(missing_settings)}"
            )