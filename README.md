# AuditCaseOS

Internal audit case management system with AI-powered analysis, evidence vault, document editing, real-time collaboration, and smart report generation.

**Version: 0.7.0** | **Phase 4: Production Hardening (57%)** | **Status: Active Development**

![CI](https://github.com/SBG4/auditcaseos/actions/workflows/ci.yml/badge.svg)

## Project Status

| Phase | Description | Features | Status |
|-------|-------------|----------|--------|
| Phase 1 | Core Platform | 12/12 | ✅ Complete |
| Phase 2 | Document Intelligence | 12/12 | ✅ Complete |
| Phase 3 | Collaboration & Enterprise | 14/14 | ✅ Complete |
| Phase 4 | Production Hardening | 12/21 | 🔄 57% Complete |
| **Total** | **All Features** | **50/59** | **85%** |

## Features

### Phase 1: Core Platform (12 features - Complete)
- **Unified Case ID System**: Automatic ID generation in `SCOPE-TYPE-SEQ` format (e.g., `FIN-USB-0001`)
- **Case Types**: USB, EMAIL, WEB, POLICY
- **Scopes**: FIN, HR, IT, SEC, OPS, CORP, LEGAL, RND, PRO, MKT, QA, ENV, SAF, EXT, GOV, GEN
- **Evidence Vault**: Secure MinIO storage with SHA-256 hash verification
- **AI Analysis**: Local Ollama LLM for case summaries and insights
- **Full Audit Log**: Every action tracked with user attribution
- **Case Timeline**: Chronological event tracking
- **Findings Management**: Document violations, observations, recommendations
- **User Management**: Role-based access (admin, auditor, reviewer, viewer)
- **JWT Authentication**: Secure token-based auth

### Phase 2: Document Intelligence (12 features - Complete)
- **OCR Processing**: Paperless-ngx for document text extraction
- **Entity Extraction**: Automatic detection of employee IDs, hostnames, IPs, emails
- **Report Generation**: DOCX reports from 4 templates (Standard, Executive, Detailed, Compliance)
- **Vector Search**: Semantic search with pgvector embeddings (768 dimensions)
- **Similar Case Detection**: AI-powered case matching
- **RAG Engine**: Retrieval-Augmented Generation for intelligent analysis

### Phase 3: Collaboration & Enterprise (14 features - Complete)
- **React Frontend**: Modern SPA with TypeScript and TailwindCSS
- **Nextcloud Integration**: File collaboration and case folders
- **ONLYOFFICE**: In-browser document editing (DOCX, XLSX, PPTX, ODS, ODP)
- **Bidirectional Sync**: Evidence syncs between API and Nextcloud
- **WebSocket Real-time Updates**: Live case updates and presence tracking
- **Analytics Dashboard**: Visual charts for case metrics, trends, and insights
- **Workflow Automation**: Rule-based triggers with 5 action types
- **Notification System**: In-app notifications with priority levels
- **Advanced Search**: Hybrid keyword + semantic search across all content
- **Global Search Bar**: Header search with auto-suggestions

### Phase 4: Production Hardening (12/15 features - 80%)

#### Completed
- **Rate Limiting**: slowapi with auth-specific limits (10/min login, 60/min general)
- **Security Headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **CORS Hardening**: Specific origins instead of wildcard
- **Production API Config**: Docs disabled in production
- **Dependency Scanning**: pip-audit, Trivy in CI
- **pytest Setup**: Async fixtures, SQLite test database
- **API Tests**: 18 auth tests passing (35% coverage)
- **CI/CD Pipeline**: GitHub Actions (lint, test, security, build)
- **Pre-commit Hooks**: ruff, mypy, detect-secrets
- **Structured Logging**: structlog with JSON output
- **Prometheus Metrics**: /metrics endpoint for monitoring
- **Docker Security**: Non-root users, resource limits, multi-stage builds

#### Remaining (43%)
- **Secret Management**: SOPS + age encrypted secrets (IN PROGRESS)
- **SSL/TLS (HTTPS)**: Let's Encrypt certificates
- **Database Migrations**: Alembic setup
- **Backup Strategy**: PostgreSQL and MinIO backups
- **Sentry Integration**: Error tracking and alerting
- **Database Optimization**: PgBouncer connection pooling
- **Redis Caching**: Response and query caching
- **Load Testing**: k6 performance testing
- **Monitoring/Alerting**: Grafana dashboards

## Quick Start

### 1. Setup Environment

```bash
cd auditcaseos
cp .env.example .env
# Edit .env if needed (defaults work for local dev)
```

### 2. Start Services

```bash
docker compose up -d
```

### 3. Pull Ollama Models (first time only)

```bash
docker exec -it auditcaseos-ollama ollama pull llama3.2
docker exec -it auditcaseos-ollama ollama pull nomic-embed-text
```

### 4. Access the System

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:13000 | admin@example.com / admin123 |
| API Docs (Swagger) | http://localhost:18000/docs | - |
| Prometheus Metrics | http://localhost:18000/metrics | - |
| MinIO Console | http://localhost:19001 | minioadmin / minioadmin123 |
| Paperless | http://localhost:18080 | admin / admin123 |
| Nextcloud | http://localhost:18081 | admin / admin123 |
| ONLYOFFICE | http://localhost:18082 | - |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AuditCaseOS                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   Frontend   │  │  API Gateway │  │    RAG Engine        │   │
│  │   (React)    │◄─►  (FastAPI)   │◄─► (Embeddings+Search)  │   │
│  │   :13000     │  │    :18000    │  │                      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│         │                 │                    │                 │
│         ▼                 ▼                    ▼                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                PostgreSQL + pgvector :15432               │   │
│  │  (Cases, Users, Evidence metadata, Embeddings, Audit)     │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                 │                    │                 │
│         ▼                 ▼                    ▼                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │    MinIO     │  │  Paperless   │  │       Ollama         │   │
│  │  :19000/01   │  │   :18080     │  │      :21434          │   │
│  │  (Evidence)  │  │    (OCR)     │  │   (Local LLM)        │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Nextcloud   │  │  ONLYOFFICE  │  │       Redis          │   │
│  │   :18081     │  │   :18082     │  │      (queue)         │   │
│  │  (Collab)    │  │  (Editing)   │  │                      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Cases
- `GET /api/v1/cases` - List all cases (with filters)
- `POST /api/v1/cases` - Create new case
- `GET /api/v1/cases/{case_id}` - Get case details
- `PATCH /api/v1/cases/{case_id}` - Update case
- `DELETE /api/v1/cases/{case_id}` - Archive case

### Evidence
- `POST /api/v1/evidence/cases/{case_id}/upload` - Upload evidence
- `GET /api/v1/evidence/cases/{case_id}` - List case evidence
- `GET /api/v1/evidence/{evidence_id}/download` - Download file
- `POST /api/v1/evidence/cases/{case_id}/sync-to-nextcloud` - Sync to Nextcloud
- `POST /api/v1/evidence/cases/{case_id}/import-from-nextcloud` - Import from Nextcloud

### Search
- `GET /api/v1/search` - Hybrid search (keyword + semantic)
- `GET /api/v1/search/suggest` - Auto-complete suggestions

### AI
- `POST /api/v1/ai/summarize/{case_id}` - Generate AI summary
- `GET /api/v1/ai/similar-cases/{case_id}` - Find similar cases
- `POST /api/v1/ai/embed/case/{case_id}` - Generate embeddings

### Analytics
- `GET /api/v1/analytics/overview` - Dashboard overview stats
- `GET /api/v1/analytics/cases` - Case statistics by status/severity/type
- `GET /api/v1/analytics/trends` - Case trends over time
- `GET /api/v1/analytics/full` - Complete analytics data

### Workflows
- `GET /api/v1/workflows/rules` - List workflow rules
- `POST /api/v1/workflows/rules` - Create workflow rule (admin)
- `POST /api/v1/workflows/rules/{id}/toggle` - Enable/disable rule
- `GET /api/v1/workflows/history` - Execution history

### Notifications
- `GET /api/v1/notifications` - List notifications
- `GET /api/v1/notifications/unread-count` - Unread count
- `POST /api/v1/notifications/mark-all-read` - Mark all as read

### ONLYOFFICE
- `GET /api/v1/onlyoffice/health` - ONLYOFFICE health check
- `GET /api/v1/onlyoffice/extensions` - Supported file types
- `GET /api/v1/onlyoffice/edit-url` - Get document edit URL

### WebSocket
- `WS /api/v1/ws/cases/{case_id}` - Real-time case updates

### Users & Auth
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Current user profile
- `POST /api/v1/auth/register` - Create user (admin only)
- `GET /api/v1/auth/users` - List users (admin only)

## Testing

### Run Unit Tests
```bash
# Inside API container
docker exec auditcaseos-api pytest tests/ -v

# With coverage
docker exec auditcaseos-api pytest tests/ --cov=app --cov-report=term-missing
```

### Run Integration Tests
```bash
bash scripts/test-all.sh              # Core tests
bash scripts/test-evidence-sync.sh    # Sync tests
bash scripts/test-onlyoffice.sh       # ONLYOFFICE tests
```

## Development

### View Logs
```bash
docker compose logs -f api
```

### Rebuild API
```bash
docker compose up -d --build api
```

### Rebuild Frontend
```bash
docker compose up -d --build frontend
```

### Access Database
```bash
docker exec -it auditcaseos-db psql -U auditcaseos -d auditcaseos
```

### Run Linting
```bash
docker exec auditcaseos-api ruff check /app/app --no-cache
```

### Reset Everything
```bash
docker compose down -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | auditcaseos | Database user |
| `POSTGRES_PASSWORD` | auditcaseos_secret | Database password |
| `MINIO_ROOT_USER` | minioadmin | MinIO admin user |
| `MINIO_ROOT_PASSWORD` | minioadmin123 | MinIO admin password |
| `SECRET_KEY` | (set in .env) | API secret key |
| `ENVIRONMENT` | development | Environment mode |
| `NEXTCLOUD_ADMIN_USER` | admin | Nextcloud admin |
| `NEXTCLOUD_ADMIN_PASSWORD` | admin123 | Nextcloud password |
| `ONLYOFFICE_JWT_SECRET` | auditcaseos-onlyoffice-secret | JWT for ONLYOFFICE |
| `NEXTCLOUD_EXTERNAL_URL` | http://localhost:18081 | Browser access to Nextcloud |
| `ONLYOFFICE_EXTERNAL_URL` | http://localhost:18082 | Browser access to ONLYOFFICE |

## Production Readiness Gaps

| Gap | Priority | Status |
|-----|----------|--------|
| SSL/TLS (HTTPS) | High | Not started |
| Secret Management | High | Using defaults |
| Database Migrations (Alembic) | High | Not started |
| Sentry Error Tracking | Medium | Not started |
| Backup Strategy | Medium | Not documented |
| Test Coverage (70%+) | Medium | 35% current |
| PgBouncer Connection Pooling | Medium | Not started |
| Load Testing | Medium | Not started |
| Monitoring/Alerting | Medium | Metrics only |

## Implementation Guidelines

See `PROJECT_SPEC.xml` for detailed implementation guidelines including:
- URL Architecture (Internal vs External URLs)
- ONLYOFFICE Configuration
- Common Failure Patterns to Avoid
- Implementation Checklist
- Development Best Practices (80+ rules from official sources)
- AI Agent Guidelines for multi-agent development

## Project Tracking

Full project specification is maintained in `PROJECT_SPEC.xml` including:
- Feature roadmap and status
- Database schemas
- API specifications
- Changelog

## Recent Updates (v0.6.2)

- **CI Pipeline**: All 4 jobs passing (Security, Backend, Frontend, Docker)
- **Linting**: All ruff errors resolved with proper configuration
- **Testing**: 18 auth tests passing with SQLite compatibility
- **Stable Dev**: Phase 4 at 80% - ready for gap prioritization

## License

Proprietary - Internal Use Only
