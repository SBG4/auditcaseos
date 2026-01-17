# AuditCaseOS Testing Guide

## Testing Philosophy

We follow the **Testing Pyramid** with emphasis on integration tests:

```
        /\
       /E2E\          10% - Critical user journeys only
      /------\
     /Integration\    30% - API + Database + Services
    /--------------\
   /     Unit       \ 60% - Business logic, utilities
  /------------------\
```

## Test Organization

### Backend (Python/FastAPI)

```
api/tests/
├── conftest.py          # Shared fixtures, PostgreSQL container
├── fixtures/
│   └── factories.py     # Test data factories
├── unit/                # Fast, isolated tests (60% of tests)
│   ├── services/        # Service layer tests
│   ├── schemas/         # Pydantic validation tests
│   └── utils/           # Utility function tests
├── integration/         # API + Database tests (30% of tests)
│   └── routers/         # Endpoint tests
├── security/            # OWASP compliance tests
│   ├── test_jwt_security.py
│   ├── test_bola.py
│   ├── test_injection.py
│   └── test_rate_limiting.py
└── contract/            # API contract tests
```

### Frontend (React/TypeScript)

```
frontend/
├── tests/
│   ├── setup/           # Test configuration
│   ├── unit/            # Component + hook tests
│   └── integration/     # Page-level tests
└── e2e/
    ├── specs/           # Playwright test specs
    ├── pages/           # Page Object Models
    └── fixtures/        # Test data
```

## Test Infrastructure

### PostgreSQL Test Container

Tests use real PostgreSQL (not SQLite) via:
- **CI**: GitHub Actions PostgreSQL service
- **Local**: testcontainers-python starts a Docker container

This ensures all PostgreSQL-specific features work correctly:
- `generate_case_id()` function
- Enum CAST operations
- pgvector for semantic search
- Proper OFFSET/LIMIT syntax

### Test Database Setup

```python
# Automatic database initialization
# - CI: database/init.sql is run before tests
# - Local: testcontainers runs init.sql on container start
```

### Transaction Rollback

Each test runs in a transaction that's rolled back after the test:
- Tests are isolated from each other
- No test data persists between tests
- Fast cleanup (no DELETE statements needed)

## Writing Tests

### Backend Unit Test Example

```python
# tests/unit/services/test_case_service.py
import pytest
from app.services.case_service import CaseService

@pytest.mark.unit
class TestCaseService:
    @pytest.mark.asyncio
    async def test_create_case_generates_id(self, db_session, test_user):
        """Case ID should follow SCOPE-TYPE-SEQ format."""
        service = CaseService()
        case = await service.create_case(
            db=db_session,
            user_id=test_user["id"],
            title="Test Case",
            scope_code="IT",
            case_type="USB"
        )
        assert case.case_id.startswith("IT-USB-")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scope", ["FIN", "HR", "IT", "SEC"])
    async def test_create_case_all_scopes(self, db_session, test_user, scope):
        """Should work with all scope codes."""
        # Parametrized test for all scope codes
        ...
```

### Backend Integration Test Example

```python
# tests/integration/routers/test_cases.py
import pytest

@pytest.mark.integration
class TestCasesRouter:
    @pytest.mark.asyncio
    async def test_create_case_endpoint(self, async_client, auth_headers, test_scope):
        """POST /cases should create case and return 201."""
        response = await async_client.post(
            "/api/v1/cases",
            json={
                "title": "Test Case",
                "scope_code": test_scope["code"],
                "case_type": "USB",
                "summary": "Test summary"
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        assert "case_id" in response.json()
```

### E2E Test Example

```typescript
// e2e/specs/case-creation.spec.ts
import { test, expect } from '@playwright/test';
import { loginAs } from '../pages/login.page';
import { CaseCreatePage } from '../pages/case-create.page';

test.describe('Case Creation', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test('should create case with all required fields', async ({ page }) => {
    const createPage = new CaseCreatePage(page);
    await createPage.goto();

    await createPage.createCase({
      scope: 'IT',
      type: 'USB',
      title: 'E2E Test Case',
      summary: 'Created via Playwright test'
    });

    await createPage.expectSuccess();
  });
});
```

## Test Fixtures

### Available Fixtures

| Fixture | Description | Scope |
|---------|-------------|-------|
| `db_session` | Async database session with rollback | function |
| `async_client` | HTTP test client with auth override | function |
| `test_user` | Standard viewer user | function |
| `test_admin` | Admin user | function |
| `test_auditor` | Auditor user | function |
| `auth_headers` | JWT auth headers for test_user | function |
| `admin_auth_headers` | JWT auth headers for admin | function |
| `test_case` | Sample case owned by test_user | function |
| `test_scope` | IT scope from database | function |
| `mock_minio_client` | Mocked MinIO client | function |
| `mock_redis_client` | Mocked Redis client | function |

### Factory Functions

```python
# tests/fixtures/factories.py
from faker import Faker

fake = Faker()

def create_case_data(**overrides):
    """Generate test case data with optional overrides."""
    return {
        "title": fake.sentence(nb_words=4),
        "summary": fake.paragraph(),
        "scope_code": "IT",
        "case_type": "USB",
        "severity": "MEDIUM",
        **overrides
    }
```

## CI/CD Quality Gates

| Gate | Job | Tests | Coverage | Blocks Merge |
|------|-----|-------|----------|--------------|
| 1 | lint | Static analysis | - | Yes |
| 2 | unit-tests | `tests/unit/` | 60% | Yes |
| 3 | integration-tests | `tests/integration/`, `tests/security/` | 50% | Yes |
| 4 | security | Dependency audit | - | Yes |
| 5 | docker | Image build | - | Yes |
| 6 | e2e-tests | Playwright | - | Yes (main only) |
| 7 | coverage | Full suite | 30% | No |

### Gate Dependencies

```
lint
 ├── unit-tests
 │    └── integration-tests
 │         └── e2e-tests
 └── security
      └── docker
           └── e2e-tests
```

## Coverage Requirements

| Module | Minimum | Target |
|--------|---------|--------|
| `app/services/` | 60% | 80% |
| `app/routers/` | 50% | 70% |
| `app/utils/` | 60% | 80% |
| Overall | 30% | 70% |

## Running Tests

### Local Development

```bash
# Start PostgreSQL testcontainer automatically
cd api && pytest tests/ -v

# Run with coverage
cd api && pytest tests/ --cov=app --cov-report=html

# Run specific markers
cd api && pytest tests/ -m unit        # Unit tests only
cd api && pytest tests/ -m integration # Integration only
cd api && pytest tests/ -m security    # Security only

# Run E2E tests (services must be running)
docker compose up -d
cd frontend && BASE_URL=http://localhost:13000 npx playwright test
```

### In Docker

```bash
# Rebuild and test API
docker compose up -d --build api
docker exec auditcaseos-api pytest tests/ -v

# Run specific tests
docker exec auditcaseos-api pytest tests/unit/ -v
docker exec auditcaseos-api pytest tests/integration/ -v

# Coverage report
docker exec auditcaseos-api pytest tests/ --cov=app --cov-report=html
```

### Test Environment

The `ENVIRONMENT=testing` setting configures:
- Lower rate limits (5/min auth, 20/min general) for rate limit testing
- Test-friendly timeouts
- Debug logging

## Debugging Tests

### Playwright Debug Mode

```bash
# Run with UI
npx playwright test --ui

# Run headed
npx playwright test --headed

# Debug specific test
npx playwright test --debug e2e/specs/auth.spec.ts

# Generate tests with codegen
npx playwright codegen http://localhost:13000
```

### pytest Debug Mode

```bash
# Stop on first failure
pytest tests/ -x

# Show print statements
pytest tests/ -s

# Verbose output
pytest tests/ -vvv

# Run specific test
pytest tests/unit/services/test_case_service.py::TestCreateCase::test_generates_id -v

# Debug with pdb
pytest tests/ --pdb
```

## Test Data Management

### Seeding Test Data

```python
# Use fixtures for repeatable test data
@pytest_asyncio.fixture
async def test_case_with_evidence(db_session, test_user):
    case = await create_test_case(db_session, test_user["id"])
    evidence = await create_test_evidence(db_session, case["id"], test_user["id"])
    return {**case, "evidence": [evidence]}
```

### Cleaning Up

Transaction rollback handles cleanup automatically. For E2E tests:

```typescript
// e2e/fixtures/cleanup.ts
test.afterEach(async ({ page }) => {
  // E2E tests may need manual cleanup
  // Use API calls to delete test data if necessary
});
```

## Security Testing

Security tests verify OWASP API Top 10 compliance:

| Test Class | OWASP | Description |
|------------|-------|-------------|
| `test_jwt_security.py` | API1 | Broken Object Level Authorization |
| `test_bola.py` | API1 | BOLA attacks |
| `test_injection.py` | API8 | SQL/NoSQL injection |
| `test_rate_limiting.py` | API4 | Unrestricted Resource Consumption |

## Adding New Tests

### When to Add Tests

1. **New service method**: Add unit test in `tests/unit/services/`
2. **New API endpoint**: Add integration test in `tests/integration/routers/`
3. **New UI page/feature**: Add E2E test in `frontend/e2e/specs/`
4. **Bug fix**: Add regression test that fails without fix

### Test Naming Convention

```python
# Pattern: test_<method>_<scenario>_<expected_result>
def test_create_case_with_valid_data_returns_201():
    ...

def test_create_case_with_invalid_scope_returns_400():
    ...

def test_get_case_unauthenticated_returns_401():
    ...
```

### Test Documentation

```python
@pytest.mark.asyncio
async def test_create_case_generates_case_id(self, db_session, test_user):
    """
    Case ID should follow SCOPE-TYPE-SEQ format.

    Given: Valid case data with IT scope and USB type
    When: Creating a new case
    Then: Case ID starts with IT-USB- and ends with sequence number
    """
    ...
```
