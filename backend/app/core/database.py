"""Database connection and session management."""

import logging
from typing import AsyncGenerator, Optional

from sqlalchemy import MetaData, event, pool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Create metadata with naming convention
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

# Create declarative base
Base = declarative_base(metadata=metadata)


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self.settings = get_settings()
    
    def create_engine(self) -> AsyncEngine:
        """Create async database engine with connection pooling."""
        if not self.settings.DATABASE_URL:
            raise ValueError("DATABASE_URL is not configured")
        
        # Configure connection pool settings for async
        pool_settings = {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
            "pool_recycle": 3600,  # 1 hour
        }
        
        # Create async engine
        engine = create_async_engine(
            self.settings.DATABASE_URL,
            echo=self.settings.DATABASE_ECHO,
            future=True,
            **pool_settings,
        )
        
        # Add connection event listeners
        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas if using SQLite."""
            if "sqlite" in str(engine.url):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        
        @event.listens_for(engine.sync_engine, "connect")
        def log_connection(dbapi_connection, connection_record):
            """Log database connections."""
            logger.info("Database connection established")
        
        return engine
    
    def get_engine(self) -> AsyncEngine:
        """Get or create database engine."""
        if self._engine is None:
            self._engine = self.create_engine()
        return self._engine
    
    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get or create session factory."""
        if self._session_factory is None:
            engine = self.get_engine()
            self._session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
        return self._session_factory
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with automatic cleanup."""
        session_factory = self.get_session_factory()
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connections closed")
    
    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session."""
    async for session in db_manager.get_session():
        yield session


# Utility functions
async def init_db() -> None:
    """Initialize database tables."""
    # Import all models to ensure they are registered
    import app.models  # noqa: F401
    
    engine = db_manager.get_engine()
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def drop_db() -> None:
    """Drop all database tables (use with caution)."""
    engine = db_manager.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")


async def check_db_connection() -> bool:
    """Check if database connection is working."""
    return await db_manager.health_check()