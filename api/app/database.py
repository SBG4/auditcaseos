"""
Async SQLAlchemy database setup and session management.

Provides async engine, session factory, and database dependency for FastAPI.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import Settings, get_settings


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    All database models should inherit from this class to be included
    in migrations and table creation.
    """
    pass


def create_engine(settings: Settings):
    """
    Create an async SQLAlchemy engine.

    Args:
        settings: Application settings containing database URL.

    Returns:
        AsyncEngine: Configured async database engine.
    """
    return create_async_engine(
        settings.async_database_url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def create_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    """
    Create an async session factory.

    Args:
        engine: The async SQLAlchemy engine.

    Returns:
        async_sessionmaker: Factory for creating async database sessions.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# Create engine and session factory using default settings
_engine = create_engine(get_settings())
AsyncSessionLocal = create_session_factory(_engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Yields a database session and ensures it is properly closed after use,
    even if an exception occurs.

    Yields:
        AsyncSession: An async database session.

    Example:
        ```python
        @router.get("/items")
        async def get_items(db: Annotated[AsyncSession, Depends(get_db)]):
            result = await db.execute(select(Item))
            return result.scalars().all()
        ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Type alias for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
