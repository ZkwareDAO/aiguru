#!/usr/bin/env python3
"""Database migration management script."""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.database import check_db_connection, init_db


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    
    # Set database URL from settings
    settings = get_settings()
    if settings.DATABASE_URL:
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    
    return alembic_cfg


async def check_database() -> bool:
    """Check if database connection is working."""
    print("Checking database connection...")
    if await check_db_connection():
        print("✓ Database connection successful")
        return True
    else:
        print("✗ Database connection failed")
        return False


def create_migration(message: str) -> None:
    """Create a new migration."""
    print(f"Creating migration: {message}")
    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, message=message, autogenerate=True)
    print("✓ Migration created successfully")


def upgrade_database(revision: str = "head") -> None:
    """Upgrade database to specified revision."""
    print(f"Upgrading database to revision: {revision}")
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, revision)
    print("✓ Database upgraded successfully")


def downgrade_database(revision: str) -> None:
    """Downgrade database to specified revision."""
    print(f"Downgrading database to revision: {revision}")
    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, revision)
    print("✓ Database downgraded successfully")


def show_current_revision() -> None:
    """Show current database revision."""
    alembic_cfg = get_alembic_config()
    command.current(alembic_cfg)


def show_migration_history() -> None:
    """Show migration history."""
    alembic_cfg = get_alembic_config()
    command.history(alembic_cfg)


def show_pending_migrations() -> None:
    """Show pending migrations."""
    alembic_cfg = get_alembic_config()
    command.show(alembic_cfg, "head")


async def init_database() -> None:
    """Initialize database with all tables."""
    print("Initializing database...")
    try:
        await init_db()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        raise


def stamp_database(revision: str = "head") -> None:
    """Stamp database with specified revision without running migrations."""
    print(f"Stamping database with revision: {revision}")
    alembic_cfg = get_alembic_config()
    command.stamp(alembic_cfg, revision)
    print("✓ Database stamped successfully")


async def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python migrate.py <command> [args]")
        print("Commands:")
        print("  check                    - Check database connection")
        print("  init                     - Initialize database tables")
        print("  create <message>         - Create new migration")
        print("  upgrade [revision]       - Upgrade to revision (default: head)")
        print("  downgrade <revision>     - Downgrade to revision")
        print("  current                  - Show current revision")
        print("  history                  - Show migration history")
        print("  pending                  - Show pending migrations")
        print("  stamp [revision]         - Stamp database with revision")
        return

    command_name = sys.argv[1]

    try:
        if command_name == "check":
            await check_database()
        
        elif command_name == "init":
            if await check_database():
                await init_database()
        
        elif command_name == "create":
            if len(sys.argv) < 3:
                print("Error: Migration message required")
                return
            message = " ".join(sys.argv[2:])
            create_migration(message)
        
        elif command_name == "upgrade":
            revision = sys.argv[2] if len(sys.argv) > 2 else "head"
            upgrade_database(revision)
        
        elif command_name == "downgrade":
            if len(sys.argv) < 3:
                print("Error: Revision required for downgrade")
                return
            revision = sys.argv[2]
            downgrade_database(revision)
        
        elif command_name == "current":
            show_current_revision()
        
        elif command_name == "history":
            show_migration_history()
        
        elif command_name == "pending":
            show_pending_migrations()
        
        elif command_name == "stamp":
            revision = sys.argv[2] if len(sys.argv) > 2 else "head"
            stamp_database(revision)
        
        else:
            print(f"Unknown command: {command_name}")
            return

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())