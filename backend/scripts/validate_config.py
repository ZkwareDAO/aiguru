#!/usr/bin/env python3
"""Configuration validation script."""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config_loader import get_config_for_environment, validate_required_settings


def main():
    """Validate configuration for all environments."""
    environments = ["development", "testing", "production"]
    
    for env in environments:
        print(f"\n=== Validating {env} environment ===")
        
        try:
            config = get_config_for_environment(env)
            print(f"✓ Configuration loaded successfully")
            print(f"  - Environment: {config.ENVIRONMENT}")
            print(f"  - Debug: {config.DEBUG}")
            print(f"  - Log Level: {config.LOG_LEVEL}")
            print(f"  - Database URL: {'Set' if config.DATABASE_URL else 'Not set'}")
            print(f"  - Redis URL: {'Set' if config.REDIS_URL else 'Not set'}")
            
            if env == "production":
                # Additional production validations
                if config.DEBUG:
                    print("✗ WARNING: DEBUG is enabled in production")
                if "*" in config.ALLOWED_HOSTS:
                    print("✗ WARNING: ALLOWED_HOSTS contains wildcard in production")
                if "*" in config.CORS_ORIGINS:
                    print("✗ WARNING: CORS_ORIGINS contains wildcard in production")
            
        except Exception as e:
            print(f"✗ Configuration validation failed: {e}")
            return 1
    
    print("\n=== Configuration validation complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())