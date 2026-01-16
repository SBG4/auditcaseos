"""
Pytest configuration and fixtures for AuditCaseOS API tests.

This module provides shared fixtures for async testing with FastAPI,
including database sessions, test clients, and authentication helpers.

Source: https://fastapi.tiangolo.com/advanced/testing-database/
"""

import asyncio
import uuid
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.services.auth_service import auth_service
from app.utils.security import hash_password


# Test database URL - use in-memory SQLite for isolation
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Minimal schema for auth tests (raw SQL to avoid ORM model conflicts)
CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT DEFAULT 'viewer',
    department TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""


async def create_test_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    full_name: str,
    role: str = "viewer",
    department: str | None = None,
) -> dict:
    """
    Create a test user directly in SQLite.

    Unlike auth_service.create_user(), this generates UUIDs in Python
    since SQLite doesn't have gen_random_uuid().
    """
    user_id = str(uuid.uuid4())
    password_hashed = hash_password(password)

    query = text("""
        INSERT INTO users (id, username, email, password_hash, full_name, role, department, is_active)
        VALUES (:id, :username, :email, :password_hash, :full_name, :role, :department, 1)
    """)

    await db.execute(query, {
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": password_hashed,
        "full_name": full_name,
        "role": role,
        "department": department,
    })
    await db.commit()

    # Fetch the created user
    result = await db.execute(
        text("SELECT * FROM users WHERE id = :id"),
        {"id": user_id}
    )
    row = result.fetchone()
    return dict(row._mapping)


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

    # Create minimal tables using raw SQL
    async with engine.begin() as conn:
        await conn.execute(text(CREATE_USERS_TABLE))

    yield engine

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
    user = await create_test_user(
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
    admin = await create_test_user(
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
