---
name: test
description: Run all test suites
---

Run the complete test suite for AuditCaseOS.

## Test Suites

| Suite | Tests | Command |
|-------|-------|---------|
| Backup Tests | 42 | `./scripts/test-backup.sh` |
| API Tests | 18+ | `cd api && pytest` |
| Evidence Sync | 24 | `./scripts/test-evidence-sync.sh` |
| ONLYOFFICE | 24 | `./scripts/test-onlyoffice.sh` |

## Run All Tests

```bash
# Backup tests (standalone, no Docker required for syntax/permission checks)
./scripts/test-backup.sh

# API tests (requires running services)
docker exec -it auditcaseos-api pytest

# Integration tests (requires running services)
./scripts/test-evidence-sync.sh
./scripts/test-onlyoffice.sh
```

## Quick Smoke Test

```bash
# Health checks
curl http://localhost:18000/health
curl http://localhost:18000/api/v1/sync/status
curl http://localhost:18000/api/v1/nextcloud/health
curl http://localhost:18000/api/v1/onlyoffice/health
```

## CI Pipeline

CI runs automatically on push:
- Backend: lint (ruff), type check (mypy), tests with coverage
- Frontend: type check, lint, build
- Security: pip-audit, Trivy
- Docker: build validation
