# AuditCaseOS - Claude Code Memory

## Quick Reference

| Metric | Value |
|--------|-------|
| Version | 0.8.4 |
| Phase | 4 (Production Hardening) - 95% complete |
| Features | 59/61 (97%) |
| Repo | https://github.com/SBG4/auditcaseos |
| Stack | FastAPI + React + PostgreSQL + MinIO + Ollama + Paperless + Nextcloud + ONLYOFFICE + Redis |

## Commands

```bash
# Start services
docker compose up -d

# Run backup tests (42 tests)
./scripts/test-backup.sh

# Full backup
./scripts/backup-all.sh

# Rebuild API
docker compose up -d --build api

# Access database
docker exec -it auditcaseos-db psql -U auditcaseos -d auditcaseos
```

## Ports

| Service | Port | Internal URL |
|---------|------|--------------|
| API | 18000 | http://api:8000 |
| Frontend | 13000 | http://frontend:80 |
| Postgres | 15432 | postgres:5432 |
| PgBouncer | 16432 | pgbouncer:5432 |
| MinIO | 19000 | minio:9000 |
| Paperless | 18080 | http://paperless:8000 |
| Nextcloud | 18081 | http://nextcloud |
| ONLYOFFICE | 18082 | http://onlyoffice |
| Prometheus | 19090 | http://prometheus:9090 |
| Grafana | 19091 | http://grafana:3000 |

## CRITICAL: URL Architecture

| Type | When | Example |
|------|------|---------|
| INTERNAL | Container-to-container | `http://nextcloud` |
| EXTERNAL | Browser access | `http://localhost:18081` |

**Rules**:
- NEVER use localhost inside containers
- ALWAYS use service names for inter-container communication
- URLs returned to browser MUST use external format

## Case ID Format

`SCOPE-TYPE-SEQ` (e.g., FIN-USB-0001)

**Scopes**: FIN, HR, IT, SEC, OPS, CORP, LEGAL, RND, PRO, MKT, QA, ENV, SAF, EXT, GOV, GEN

## Failure Patterns (AVOID THESE)

| Pattern | Fix |
|---------|-----|
| localhost-in-container | Use service names |
| internal-url-to-browser | Use external URLs for frontend |
| string-replacement-urls | Use config, not string manipulation |
| hardcoded-ports | Use environment variables |
| missing-nginx-limits | Set client_max_body_size |

## Documentation

| File | Content |
|------|---------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, diagrams, URL rules |
| [docs/FEATURES.md](docs/FEATURES.md) | All 61 features by phase |
| [docs/CONVENTIONS.md](docs/CONVENTIONS.md) | Code style, patterns |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Progress tracking |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Version history |
| [docs/AGENT_PATTERNS.md](docs/AGENT_PATTERNS.md) | AI agent guidelines |
| [PROJECT_SPEC.xml](PROJECT_SPEC.xml) | Full spec (archived) |

## Mandatory Rules

1. **Commit and push before ending session** - No exceptions
2. **Update version** in PROJECT_SPEC.xml when features complete
3. **Run tests** before committing
4. **Read relevant docs** before implementing features

## Default Credentials

| Service | User | Password |
|---------|------|----------|
| MinIO | minioadmin | minioadmin123 |
| PostgreSQL | auditcaseos | auditcaseos_secret |
| Paperless | admin | admin123 |
| Nextcloud | admin | admin123 |
| API Admin | admin@example.com | admin123 |

## Implementation Checklist

Before completing any feature:
- [ ] URLs from config, not hardcoded
- [ ] Internal URLs use Docker service names
- [ ] External URLs use localhost:PORT
- [ ] nginx body size limits configured
- [ ] Tests verify browser functionality
- [ ] Documentation updated

## CI Status

All 4 jobs passing: Security, Backend, Frontend, Docker
