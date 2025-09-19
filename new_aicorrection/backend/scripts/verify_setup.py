#!/usr/bin/env python3
"""Verify project setup without requiring dependencies."""

import sys
from pathlib import Path

def check_file_exists(file_path: Path, description: str) -> bool:
    """Check if a file exists and report the result."""
    if file_path.exists():
        print(f"✓ {description}: {file_path}")
        return True
    else:
        print(f"✗ {description}: {file_path} (missing)")
        return False

def check_directory_structure():
    """Check that all required directories and files exist."""
    base_dir = Path(__file__).parent.parent
    
    print("=== Checking Project Structure ===")
    
    required_files = [
        (base_dir / "pyproject.toml", "Project configuration"),
        (base_dir / "requirements.txt", "Production dependencies"),
        (base_dir / "requirements-dev.txt", "Development dependencies"),
        (base_dir / "README.md", "Project documentation"),
        (base_dir / ".gitignore", "Git ignore file"),
        (base_dir / ".env.example", "Environment template"),
        (base_dir / "Dockerfile", "Docker configuration"),
        (base_dir / "docker-compose.yml", "Docker Compose configuration"),
        (base_dir / ".pre-commit-config.yaml", "Pre-commit hooks"),
    ]
    
    required_dirs = [
        (base_dir / "app", "Main application directory"),
        (base_dir / "app" / "core", "Core modules"),
        (base_dir / "app" / "api", "API modules"),
        (base_dir / "app" / "api" / "v1", "API v1 modules"),
        (base_dir / "app" / "models", "Database models"),
        (base_dir / "app" / "schemas", "Pydantic schemas"),
        (base_dir / "app" / "services", "Business services"),
        (base_dir / "app" / "utils", "Utility functions"),
        (base_dir / "tests", "Test directory"),
        (base_dir / "scripts", "Utility scripts"),
        (base_dir / "config", "Configuration files"),
    ]
    
    all_good = True
    
    # Check files
    for file_path, description in required_files:
        if not check_file_exists(file_path, description):
            all_good = False
    
    # Check directories
    for dir_path, description in required_dirs:
        if not check_file_exists(dir_path, description):
            all_good = False
    
    print("\n=== Checking Key Application Files ===")
    
    app_files = [
        (base_dir / "app" / "__init__.py", "App package init"),
        (base_dir / "app" / "main.py", "FastAPI application"),
        (base_dir / "app" / "core" / "config.py", "Configuration settings"),
        (base_dir / "app" / "core" / "config_loader.py", "Configuration loader"),
        (base_dir / "app" / "core" / "logging.py", "Logging configuration"),
        (base_dir / "app" / "api" / "v1" / "router.py", "API router"),
    ]
    
    for file_path, description in app_files:
        if not check_file_exists(file_path, description):
            all_good = False
    
    print("\n=== Checking Configuration Files ===")
    
    config_files = [
        (base_dir / "config" / "development.env", "Development config"),
        (base_dir / "config" / "testing.env", "Testing config"),
        (base_dir / "config" / "production.env", "Production config"),
    ]
    
    for file_path, description in config_files:
        if not check_file_exists(file_path, description):
            all_good = False
    
    return all_good

def main():
    """Main verification function."""
    print("AI Education Backend - Project Setup Verification")
    print("=" * 50)
    
    if check_directory_structure():
        print("\n✓ Project setup verification passed!")
        print("\nNext steps:")
        print("1. Create a virtual environment: python -m venv venv")
        print("2. Activate it: venv\\Scripts\\activate (Windows) or source venv/bin/activate (Unix)")
        print("3. Install dependencies: pip install -r requirements-dev.txt")
        print("4. Copy .env.example to .env and configure your settings")
        print("5. Run the application: uvicorn app.main:app --reload")
        return 0
    else:
        print("\n✗ Project setup verification failed!")
        print("Some required files or directories are missing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())