"""
Pytest configuration and fixtures for AuditCaseOS API tests.

This module provides shared fixtures for async testing with FastAPI,
including database sessions, test clients, and authentication helpers.

Source: https://fastapi.tiangolo.com/advanced/testing-database/
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services.auth_service import auth_service


# Test database URL - use in-memory SQLite for isolation
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session.

    Source: pytest-asyncio documentation
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create an async engine for each test function.

    Uses SQLite in-memory database with StaticPool for test isolation.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for each test.

    Rolls back all changes after each test for isolation.
    """
    async_session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with database dependency override.

    Source: https://fastapi.tiangolo.com/advanced/testing-dependencies/
    """
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> dict:
    """Create a test user for authentication tests.

    Returns:
        dict: User data including id, username, email, role
    """
    user = await auth_service.create_user(
        db=db_session,
        username="testuser",
        email="testuser@example.com",
        password="TestPassword123!",
        full_name="Test User",
        role="viewer",
    )
    return user


@pytest_asyncio.fixture(scope="function")
async def test_admin(db_session: AsyncSession) -> dict:
    """Create a test admin user.

    Returns:
        dict: Admin user data
    """
    admin = await auth_service.create_user(
        db=db_session,
        username="testadmin",
        email="testadmin@example.com",
        password="AdminPassword123!",
        full_name="Test Admin",
        role="admin",
    )
    return admin


@pytest_asyncio.fixture(scope="function")
async def auth_headers(test_user: dict) -> dict:
    """Get authentication headers for a test user.

    Returns:
        dict: Headers with Bearer token
    """
    token = auth_service.create_user_token(test_user)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def admin_auth_headers(test_admin: dict) -> dict:
    """Get authentication headers for a test admin.

    Returns:
        dict: Headers with Bearer token for admin
    """
    token = auth_service.create_user_token(test_admin)
    return {"Authorization": f"Bearer {token}"}


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
