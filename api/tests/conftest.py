"""
Pytest configuration and fixtures for AuditCaseOS API tests.

This module provides shared fixtures for async testing with FastAPI,
including PostgreSQL database sessions (via testcontainers or CI service),
test clients, authentication helpers, and mock services.

Source: https://fastapi.tiangolo.com/advanced/testing-database/
        https://testcontainers.com/guides/getting-started-with-testcontainers-for-python/
"""

import asyncio
import json
import os
import uuid
from collections.abc import AsyncGenerator, Generator
from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import get_db
from app.main import app
from app.services.auth_service import auth_service
from app.utils.security import hash_password
from tests.fixtures.factories import (
    ADMIN_PASSWORD,
    DEFAULT_PASSWORD,
    create_case_data,
    create_evidence_data,
    create_finding_data,
)

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Check if PostgreSQL is provided via environment (CI) or use testcontainers
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_TESTCONTAINERS = DATABASE_URL is None


def get_test_database_url() -> str:
    """Get the test database URL from environment or testcontainers."""
    if DATABASE_URL:
        return DATABASE_URL
    # Fallback URL for testcontainers (will be overridden by fixture)
    return "postgresql+asyncpg://test:test@localhost:5432/test"


# =============================================================================
# POSTGRESQL TESTCONTAINER SETUP
# =============================================================================

if USE_TESTCONTAINERS:
    from testcontainers.postgres import PostgresContainer

    # Module-level container reference
    _postgres_container = None

    def get_postgres_container() -> PostgresContainer:
        """Get or create the PostgreSQL test container."""
        global _postgres_container
        if _postgres_container is None:
            _postgres_container = PostgresContainer(
                image="pgvector/pgvector:pg16",
                username="test",
                password="test",
                dbname="test_auditcaseos",
                driver=None,  # We'll use asyncpg
            )
            _postgres_container.start()
            # Run init.sql to set up schema
            _run_init_sql(_postgres_container)
        return _postgres_container

    def _run_init_sql(container: PostgresContainer) -> None:
        """Run init.sql to set up the database schema."""
        import psycopg2

        # Get connection params
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)

        # Read init.sql
        init_sql_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "configs",
            "postgres",
            "init.sql"
        )

        if os.path.exists(init_sql_path):
            with open(init_sql_path) as f:
                init_sql = f.read()

            # Execute init.sql
            conn = psycopg2.connect(
                host=host,
                port=port,
                user="test",
                password="test",
                database="test_auditcaseos",
            )
            conn.autocommit = True
            cur = conn.cursor()
            try:
                cur.execute(init_sql)
            except Exception as e:
                print(f"Warning: Error running init.sql: {e}")
            finally:
                cur.close()
                conn.close()

    def stop_postgres_container() -> None:
        """Stop the PostgreSQL test container."""
        global _postgres_container
        if _postgres_container is not None:
            _postgres_container.stop()
            _postgres_container = None


# =============================================================================
# DATABASE HELPER FUNCTIONS
# =============================================================================


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
    Create a test user directly in the database.
    """
    user_id = str(uuid.uuid4())
    password_hashed = hash_password(password)

    query = text("""
        INSERT INTO users (id, username, email, password_hash, full_name, role, department, is_active)
        VALUES (:id, :username, :email, :password_hash, :full_name, CAST(:role AS user_role), :department, true)
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


async def create_test_case(
    db: AsyncSession,
    owner_id: str,
    case_data: dict[str, Any] | None = None,
) -> dict:
    """Create a test case using the database's generate_case_id function."""
    case_data = case_data or create_case_data()
    case_uuid = str(uuid.uuid4())
    scope_code = case_data.get("scope_code", "IT")
    case_type = case_data.get("case_type", "USB")

    # Use PostgreSQL's generate_case_id function
    # Note: scope_code is VARCHAR, case_type/status/severity are enums
    query = text("""
        INSERT INTO cases (
            id, case_id, scope_code, case_type, status, severity,
            title, summary, description, subject_user, subject_computer,
            owner_id, tags, metadata
        ) VALUES (
            :id,
            generate_case_id(:scope_code, CAST(:case_type AS case_type)),
            :scope_code,
            CAST(:case_type AS case_type),
            CAST(:status AS case_status),
            CAST(:severity AS severity_level),
            :title, :summary, :description, :subject_user, :subject_computer,
            :owner_id, :tags, :metadata
        )
        RETURNING *
    """)

    result = await db.execute(query, {
        "id": case_uuid,
        "scope_code": scope_code,
        "case_type": case_type,
        "status": case_data.get("status", "OPEN"),
        "severity": case_data.get("severity", "MEDIUM"),
        "title": case_data.get("title", "Test Case"),
        "summary": case_data.get("summary"),
        "description": case_data.get("description"),
        "subject_user": case_data.get("subject_user"),
        "subject_computer": case_data.get("subject_computer"),
        "owner_id": owner_id,
        "tags": case_data.get("tags", []),  # text[] array, not JSON
        "metadata": json.dumps(case_data.get("metadata", {})),  # JSONB
    })
    await db.commit()

    row = result.fetchone()
    return dict(row._mapping)


async def create_test_evidence(
    db: AsyncSession,
    case_id: str,
    uploaded_by: str,
    evidence_data: dict[str, Any] | None = None,
) -> dict:
    """Create test evidence directly in the database."""
    evidence_data = evidence_data or create_evidence_data()
    evidence_id = str(uuid.uuid4())

    query = text("""
        INSERT INTO evidence (
            id, case_id, file_name, file_path, file_size, mime_type,
            file_hash, description, uploaded_by, extracted_text, metadata
        ) VALUES (
            :id, :case_id, :file_name, :file_path, :file_size, :mime_type,
            :file_hash, :description, :uploaded_by, :extracted_text, :metadata
        )
        RETURNING *
    """)

    result = await db.execute(query, {
        "id": evidence_id,
        "case_id": case_id,
        "file_name": evidence_data.get("file_name", "test.pdf"),
        "file_path": evidence_data.get("file_path", "test/path.pdf"),
        "file_size": evidence_data.get("file_size", 1024),
        "mime_type": evidence_data.get("mime_type", "application/pdf"),
        "file_hash": evidence_data.get("file_hash", f"sha256:{uuid.uuid4().hex}"),
        "description": evidence_data.get("description"),
        "uploaded_by": uploaded_by,
        "extracted_text": evidence_data.get("extracted_text"),
        "metadata": json.dumps(evidence_data.get("metadata", {})),
    })
    await db.commit()

    row = result.fetchone()
    return dict(row._mapping)


async def create_test_finding(
    db: AsyncSession,
    case_id: str,
    created_by: str,
    finding_data: dict[str, Any] | None = None,
) -> dict:
    """Create test finding directly in the database."""
    finding_data = finding_data or create_finding_data()
    finding_id = str(uuid.uuid4())

    query = text("""
        INSERT INTO findings (
            id, case_id, title, description, severity, evidence_ids, created_by
        ) VALUES (
            :id, :case_id, :title, :description, CAST(:severity AS severity_level), :evidence_ids, :created_by
        )
        RETURNING *
    """)

    result = await db.execute(query, {
        "id": finding_id,
        "case_id": case_id,
        "title": finding_data.get("title", "Test Finding"),
        "description": finding_data.get("description"),
        "severity": finding_data.get("severity", "MEDIUM"),
        "evidence_ids": finding_data.get("evidence_ids", []),  # uuid[] array, not JSON
        "created_by": created_by,
    })
    await db.commit()

    row = result.fetchone()
    return dict(row._mapping)


# =============================================================================
# PYTEST FIXTURES - SESSION & DATABASE
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session.

    Source: pytest-asyncio documentation
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def postgres_url() -> Generator[str, None, None]:
    """
    Get PostgreSQL URL for tests.

    Uses environment variable (CI/Docker) or starts testcontainer (local).
    """
    if DATABASE_URL:
        # CI/Docker environment - use provided PostgreSQL
        yield DATABASE_URL
    else:
        # Local development - use testcontainers
        container = get_postgres_container()
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        yield f"postgresql+asyncpg://test:test@{host}:{port}/test_auditcaseos"
        # Container cleanup happens at end of test session


@pytest_asyncio.fixture(scope="function")
async def async_engine(postgres_url: str):
    """Create an async engine for each test function.

    Uses PostgreSQL (from CI service, Docker, or testcontainers).
    """
    engine = create_async_engine(
        postgres_url,
        poolclass=NullPool,  # Required for testcontainers compatibility
        echo=False,
    )

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for each test.

    Uses transaction rollback for test isolation.
    """
    async with async_engine.connect() as connection:
        # Start a transaction that we'll roll back after the test
        transaction = await connection.begin()

        async_session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield async_session
        finally:
            await async_session.close()
            await transaction.rollback()


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


# =============================================================================
# PYTEST FIXTURES - USERS
# =============================================================================


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
        password=DEFAULT_PASSWORD,
        full_name="Test User",
        role="viewer",
    )
    return user


@pytest_asyncio.fixture(scope="function")
async def test_auditor(db_session: AsyncSession) -> dict:
    """Create a test auditor user.

    Returns:
        dict: Auditor user data
    """
    auditor = await create_test_user(
        db=db_session,
        username="testauditor",
        email="testauditor@example.com",
        password=DEFAULT_PASSWORD,
        full_name="Test Auditor",
        role="auditor",
    )
    return auditor


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
        password=ADMIN_PASSWORD,
        full_name="Test Admin",
        role="admin",
    )
    return admin


# =============================================================================
# PYTEST FIXTURES - AUTHENTICATION
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def auth_headers(test_user: dict) -> dict:
    """Get authentication headers for a test user.

    Returns:
        dict: Headers with Bearer token
    """
    token = auth_service.create_user_token(test_user)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def auditor_auth_headers(test_auditor: dict) -> dict:
    """Get authentication headers for a test auditor.

    Returns:
        dict: Headers with Bearer token for auditor
    """
    token = auth_service.create_user_token(test_auditor)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def admin_auth_headers(test_admin: dict) -> dict:
    """Get authentication headers for a test admin.

    Returns:
        dict: Headers with Bearer token for admin
    """
    token = auth_service.create_user_token(test_admin)
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# PYTEST FIXTURES - CASES
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def test_case(db_session: AsyncSession, test_user: dict) -> dict:
    """Create a test case.

    Returns:
        dict: Case data
    """
    case = await create_test_case(
        db=db_session,
        owner_id=test_user["id"],
        case_data=create_case_data(
            title="Test Investigation Case",
            summary="A test case for unit testing",
        ),
    )
    return case


@pytest_asyncio.fixture(scope="function")
async def test_case_with_evidence(
    db_session: AsyncSession,
    test_case: dict,
    test_user: dict,
) -> dict:
    """Create a test case with evidence attached.

    Returns:
        dict: Case data with evidence_items key
    """
    evidence = await create_test_evidence(
        db=db_session,
        case_id=test_case["id"],
        uploaded_by=test_user["id"],
    )
    return {**test_case, "evidence_items": [evidence]}


@pytest_asyncio.fixture(scope="function")
async def test_case_with_findings(
    db_session: AsyncSession,
    test_case: dict,
    test_user: dict,
) -> dict:
    """Create a test case with findings attached.

    Returns:
        dict: Case data with findings key
    """
    finding = await create_test_finding(
        db=db_session,
        case_id=test_case["id"],
        created_by=test_user["id"],
    )
    return {**test_case, "findings": [finding]}


# =============================================================================
# PYTEST FIXTURES - MOCK SERVICES
# =============================================================================


@pytest.fixture
def mock_minio_client():
    """Create a mock MinIO client for unit tests.

    Returns:
        MagicMock: Mocked MinIO client
    """
    mock = MagicMock()
    mock.bucket_exists.return_value = True
    mock.put_object.return_value = None
    mock.get_object.return_value = MagicMock(
        read=lambda: b"test file content",
        close=lambda: None,
    )
    mock.remove_object.return_value = None
    mock.stat_object.return_value = MagicMock(
        size=1024,
        content_type="application/pdf",
        etag="abc123",
    )
    return mock


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client for unit tests.

    Returns:
        AsyncMock: Mocked async Redis client
    """
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = 1
    mock.exists.return_value = False
    mock.scan.return_value = (0, [])
    mock.ping.return_value = True
    return mock


@pytest.fixture
def mock_ollama_client(httpx_mock):
    """Create mock responses for Ollama API.

    Use with pytest-httpx fixture.
    """
    def _mock_ollama(
        response_text: str = "This is a test summary.",
        embeddings: list[float] | None = None,
    ):
        # Mock generate endpoint
        httpx_mock.add_response(
            url="http://ollama:11434/api/generate",
            json={"response": response_text},
        )
        # Mock embeddings endpoint
        httpx_mock.add_response(
            url="http://ollama:11434/api/embeddings",
            json={"embedding": embeddings or [0.1] * 768},
        )
    return _mock_ollama


@pytest.fixture
def mock_paperless_client(httpx_mock):
    """Create mock responses for Paperless API.

    Use with pytest-httpx fixture.
    """
    def _mock_paperless(
        documents: list[dict] | None = None,
        correspondents: list[dict] | None = None,
    ):
        # Mock documents endpoint
        httpx_mock.add_response(
            url="http://paperless:8000/api/documents/",
            json={
                "count": len(documents or []),
                "results": documents or [],
            },
        )
        # Mock correspondents endpoint
        httpx_mock.add_response(
            url="http://paperless:8000/api/correspondents/",
            json={
                "count": len(correspondents or []),
                "results": correspondents or [],
            },
        )
    return _mock_paperless


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing uploads.

    Returns:
        tuple: (filename, BytesIO, content_type)
    """
    # Minimal PDF content
    pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer << /Size 4 /Root 1 0 R >>
startxref
197
%%EOF"""
    return ("test.pdf", BytesIO(pdf_content), "application/pdf")


@pytest.fixture
def sample_text_file():
    """Create a sample text file for testing uploads.

    Returns:
        tuple: (filename, BytesIO, content_type)
    """
    content = b"This is test content for evidence upload testing."
    return ("test.txt", BytesIO(content), "text/plain")


# =============================================================================
# PYTEST FIXTURES - ADDITIONAL
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def async_client(client: AsyncClient) -> AsyncClient:
    """Alias for client fixture - for compatibility with different test naming conventions.

    Returns:
        AsyncClient: The async HTTP test client
    """
    return client


@pytest_asyncio.fixture(scope="function")
async def test_scope(db_session: AsyncSession) -> dict:
    """Get a test scope from the database.

    The scopes are pre-populated by init.sql.

    Returns:
        dict: Scope data with code, name, description
    """
    result = await db_session.execute(
        text("SELECT * FROM scopes WHERE code = 'IT'")
    )
    row = result.fetchone()
    if row:
        return dict(row._mapping)
    return {"code": "IT", "name": "Information Technology", "description": "IT security incidents"}


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "contract: marks tests as contract tests"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )


def pytest_sessionfinish(session, exitstatus):
    """Clean up testcontainers after test session."""
    if USE_TESTCONTAINERS:
        stop_postgres_container()
