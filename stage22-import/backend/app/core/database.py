"""
Nexus ERP - Database Configuration Module
=========================================

This module provides database connection management with SQLAlchemy 2.0 async support.
Supports the ERP application's shared-database, row-level tenant model.

Features:
- Async database operations
- Connection pooling
- Tenant isolation through tenant_id-scoped data access
- Session management
- Reviewed Alembic migrations (no runtime create_all)
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from app.core.config import settings
from app.models.base import Base
import app.models  # noqa: F401 - register every model on Base.metadata

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database Manager Class
    
    Manages database connections and sessions.
    Tenant boundaries are enforced in application queries and authorization;
    this manager deliberately does not switch PostgreSQL schemas.
    """
    
    def __init__(self):
        self._engine = None
        self._session_factory = None
    
    async def init_db(self):
        """
        Initialize database connection and create session factory.
        
        Should be called during application startup.
        """
        self._engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            echo=settings.DEBUG,
            future=True,
        )
        
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        logger.info("Database connection initialized successfully")
    
    async def close_db(self):
        """
        Close database connection.
        
        Should be called during application shutdown.
        """
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connection closed")
    
    def set_tenant(self, tenant_schema: str):
        """Schema-per-tenant switching is intentionally disabled.

        Nexus ERP uses row-level tenant isolation (`tenant_id`) within its own
        application database. A mutable schema selector is unsafe with pooled
        async connections and is not part of the supported tenancy model.
        """
        raise RuntimeError(
            "Schema-based tenant switching is disabled; use tenant_id row-level isolation."
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with automatic transaction management.
        
        Yields:
            AsyncSession: Database session instance
            
        Usage:
            async with db_manager.get_session() as session:
                # Perform database operations
                pass
        """
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        
        session = self._session_factory()
        try:
            # Tenant isolation is enforced by tenant_id-scoped queries and
            # authorization checks, never by mutable connection search_path.
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()
    
    async def create_tenant_schema(self, schema_name: str):
        """Reject legacy schema provisioning; tenants are rows, not schemas."""
        raise RuntimeError(
            "Per-tenant schema creation is disabled; provision tenant records and tenant_id-scoped data."
        )

    async def drop_tenant_schema(self, schema_name: str):
        """Reject destructive legacy schema deletion."""
        raise RuntimeError(
            "Per-tenant schema deletion is disabled; use an explicit, reviewed tenant offboarding workflow."
        )


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI endpoints
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage in endpoints:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            # Use db session
            pass
    """
    async with db_manager.get_session() as session:
        yield session


async def init_models():
    """Reject runtime schema creation; database changes must use Alembic."""
    raise RuntimeError(
        "Runtime create_all is disabled. Apply reviewed Alembic migrations instead."
    )
