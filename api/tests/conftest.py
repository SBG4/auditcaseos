"""
Pytest configuration and fixtures for AuditCaseOS API tests.

This module provides shared fixtures for async testing with FastAPI,
including database sessions, test clients, authentication helpers,
and mock services.

Source: https://fastapi.tiangolo.com/advanced/testing-database/
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.services.auth_service import auth_service
from app.utils.security import hash_password

from tests.fixtures.factories import (
    create_user_data,
    create_admin_data,
    create_case_data,
    create_evidence_data,
    create_finding_data,
    create_timeline_event_data,
    DEFAULT_PASSWORD,
    ADMIN_PASSWORD,
)

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Test database URL - use in-memory SQLite for isolation
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Minimal schema for tests (raw SQL to avoid ORM model conflicts)
SCHEMA_SQL = """
-- Users table
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
);

-- Scopes table
CREATE TABLE IF NOT EXISTS scopes (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT
);

-- Cases table
CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    case_id TEXT UNIQUE NOT NULL,
    scope_code TEXT NOT NULL,
    case_type TEXT NOT NULL,
    status TEXT DEFAULT 'OPEN',
    severity TEXT DEFAULT 'MEDIUM',
    title TEXT NOT NULL,
    summary TEXT,
    description TEXT,
    subject_user TEXT,
    subject_computer TEXT,
    subject_devices TEXT,
    related_users TEXT,
    owner_id TEXT NOT NULL,
    assigned_to TEXT,
    incident_date TEXT,
    tags TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

-- Evidence table
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    case_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    mime_type TEXT,
    file_hash TEXT,
    description TEXT,
    uploaded_by TEXT NOT NULL,
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    extracted_text TEXT,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (case_id) REFERENCES cases(id),
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
);

-- Findings table
CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    case_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT DEFAULT 'MEDIUM',
    evidence_ids TEXT DEFAULT '[]',
    created_by TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Timeline events table
CREATE TABLE IF NOT EXISTS timeline_events (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    case_id TEXT NOT NULL,
    event_time TEXT NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT,
    source TEXT DEFAULT 'user',
    evidence_id TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Entities table
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    case_id TEXT NOT NULL,
    evidence_id TEXT,
    entity_type TEXT NOT NULL,
    value TEXT NOT NULL,
    context TEXT,
    confidence REAL DEFAULT 0.95,
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id)
);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details TEXT DEFAULT '{}',
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    notification_type TEXT DEFAULT 'INFO',
    priority TEXT DEFAULT 'NORMAL',
    is_read INTEGER DEFAULT 0,
    related_case_id TEXT,
    related_entity_type TEXT,
    related_entity_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Workflow rules table
CREATE TABLE IF NOT EXISTS workflow_rules (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name TEXT NOT NULL,
    description TEXT,
    trigger_type TEXT NOT NULL,
    trigger_config TEXT DEFAULT '{}',
    is_enabled INTEGER DEFAULT 1,
    created_by TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Workflow actions table
CREATE TABLE IF NOT EXISTS workflow_actions (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    rule_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_config TEXT DEFAULT '{}',
    action_order INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rule_id) REFERENCES workflow_rules(id)
);

-- Workflow history table
CREATE TABLE IF NOT EXISTS workflow_history (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    rule_id TEXT NOT NULL,
    case_id TEXT,
    status TEXT DEFAULT 'PENDING',
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    error_message TEXT,
    FOREIGN KEY (rule_id) REFERENCES workflow_rules(id)
);

-- Insert default scopes
INSERT OR IGNORE INTO scopes (code, name, description) VALUES
    ('FIN', 'Finance', 'Financial department investigations'),
    ('HR', 'Human Resources', 'HR related investigations'),
    ('IT', 'Information Technology', 'IT security incidents'),
    ('SEC', 'Security', 'Physical and cybersecurity'),
    ('OPS', 'Operations', 'Operational incidents'),
    ('GEN', 'General', 'General investigations');
"""


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


async def create_test_case(
    db: AsyncSession,
    owner_id: str,
    case_data: dict[str, Any] | None = None,
) -> dict:
    """Create a test case directly in SQLite."""
    case_data = case_data or create_case_data()
    case_uuid = str(uuid.uuid4())
    case_id = f"{case_data['scope_code']}-{case_data['case_type']}-{uuid.uuid4().hex[:4].upper()}"

    query = text("""
        INSERT INTO cases (
            id, case_id, scope_code, case_type, status, severity,
            title, summary, description, subject_user, subject_computer,
            owner_id, tags, metadata
        ) VALUES (
            :id, :case_id, :scope_code, :case_type, :status, :severity,
            :title, :summary, :description, :subject_user, :subject_computer,
            :owner_id, :tags, :metadata
        )
    """)

    import json
    await db.execute(query, {
        "id": case_uuid,
        "case_id": case_id,
        "scope_code": case_data.get("scope_code", "IT"),
        "case_type": case_data.get("case_type", "USB"),
        "status": case_data.get("status", "OPEN"),
        "severity": case_data.get("severity", "MEDIUM"),
        "title": case_data.get("title", "Test Case"),
        "summary": case_data.get("summary"),
        "description": case_data.get("description"),
        "subject_user": case_data.get("subject_user"),
        "subject_computer": case_data.get("subject_computer"),
        "owner_id": owner_id,
        "tags": json.dumps(case_data.get("tags", [])),
        "metadata": json.dumps(case_data.get("metadata", {})),
    })
    await db.commit()

    result = await db.execute(
        text("SELECT * FROM cases WHERE id = :id"),
        {"id": case_uuid}
    )
    row = result.fetchone()
    return dict(row._mapping)


async def create_test_evidence(
    db: AsyncSession,
    case_id: str,
    uploaded_by: str,
    evidence_data: dict[str, Any] | None = None,
) -> dict:
    """Create test evidence directly in SQLite."""
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
    """)

    import json
    await db.execute(query, {
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

    result = await db.execute(
        text("SELECT * FROM evidence WHERE id = :id"),
        {"id": evidence_id}
    )
    row = result.fetchone()
    return dict(row._mapping)


async def create_test_finding(
    db: AsyncSession,
    case_id: str,
    created_by: str,
    finding_data: dict[str, Any] | None = None,
) -> dict:
    """Create test finding directly in SQLite."""
    finding_data = finding_data or create_finding_data()
    finding_id = str(uuid.uuid4())

    query = text("""
        INSERT INTO findings (
            id, case_id, title, description, severity, evidence_ids, created_by
        ) VALUES (
            :id, :case_id, :title, :description, :severity, :evidence_ids, :created_by
        )
    """)

    import json
    await db.execute(query, {
        "id": finding_id,
        "case_id": case_id,
        "title": finding_data.get("title", "Test Finding"),
        "description": finding_data.get("description"),
        "severity": finding_data.get("severity", "MEDIUM"),
        "evidence_ids": json.dumps(finding_data.get("evidence_ids", [])),
        "created_by": created_by,
    })
    await db.commit()

    result = await db.execute(
        text("SELECT * FROM findings WHERE id = :id"),
        {"id": finding_id}
    )
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

    # Create schema using raw SQL
    async with engine.begin() as conn:
        for statement in SCHEMA_SQL.split(";"):
            statement = statement.strip()
            if statement:
                await conn.execute(text(statement))

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

    The scopes are pre-populated by the schema SQL.

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
