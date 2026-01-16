# AuditCaseOS Features

**Version: 0.8.5** | **Last Updated: 2026-01-16**

## Progress Summary

| Phase | Name | Status | Features |
|-------|------|--------|----------|
| 1 | Core Platform | COMPLETED | 12/12 |
| 2 | Document Intelligence | COMPLETED | 12/12 |
| 3 | Frontend & Collaboration | COMPLETED | 14/14 |
| 4 | Production Hardening | COMPLETED | 21/21 (100%) |
| 5 | Future Enhancements | PLANNED | 0/8 |
| **Total** | | | **60/61 (98%)** |

---

## Phase 1: Core Platform (COMPLETED)

### 1.1 Docker Compose Setup
Multi-service orchestration with PostgreSQL, MinIO, Ollama, API.
- Files: `docker-compose.yml`, `.env.example`

### 1.2 PostgreSQL with pgvector
Database schema with vector extension for embeddings.
- Tables: users, scopes, cases, case_sequences, evidence, findings, timeline_events, audit_log, embeddings

### 1.3 MinIO Evidence Storage
S3-compatible object storage for evidence files.
- Bucket: `evidence`
- Path format: `cases/{case_id}/{filename}`

### 1.4 Ollama Integration
Local LLM service for AI features.
- Default model: llama3.2

### 1.5 FastAPI Application
Core API framework with CORS, health checks, lifespan management.
- Files: `api/app/main.py`, `api/app/config.py`, `api/app/database.py`

### 1.6 SQLAlchemy Models
ORM models for all database entities.
- Files: `api/app/models/`

### 1.7 Pydantic Schemas
Request/response validation schemas.
- Files: `api/app/schemas/`

### 1.8 API Routers
REST endpoints for all resources.
- Files: `api/app/routers/`

### 1.9 Service Layer
Business logic services.
- Files: `api/app/services/`

### 1.10 Case ID Generation
Auto-generate SCOPE-TYPE-SEQ format IDs.

### 1.11 README
Project documentation with setup instructions.

### 1.12 Bootstrap Script
Initial setup automation.

---

## Phase 2: Document Intelligence (COMPLETED)

### 2.1 Complete Database CRUD
Wire up all API endpoints to actual database operations.
- Tasks: Case creation, listing, updates, soft deletes, evidence storage, findings, timeline, audit logging

### 2.2 User Authentication
JWT-based authentication system.
- Endpoints: `POST /auth/login`, `POST /auth/register`, `GET /auth/me`
- Features: Password hashing (bcrypt), JWT tokens, role-based access control

### 2.3 Paperless Service Setup
Add Paperless-ngx to Docker Compose for OCR.
- Port: 18080
- Dependencies: PostgreSQL, Redis

### 2.4 Paperless Connector
API service to interact with Paperless.
- Methods: upload_document, get_document, get_document_content, search_documents, health_check

### 2.5 Evidence Sync Pipeline
Auto-sync evidence files to Paperless for OCR.
- Endpoints: `GET /sync/status`, `POST /sync/case/{case_id}`, `POST /sync/evidence/{evidence_id}`
- Supported types: PDF, images, text, Word documents

### 2.6 Entity Extraction Service
Extract structured entities from evidence text.
- Patterns: Employee IDs, IP addresses, emails, hostnames, MAC addresses, USB devices

### 2.7 Entity Storage
Store and query extracted entities.
- Endpoints: `POST /entities/extract`, `POST /entities/store`, `GET /entities/case/{case_id}`, `GET /entities/search`

### 2.8 Embedding Service
Generate and store vector embeddings using Ollama.
- Model: nomic-embed-text
- Dimension: 768

### 2.9 Similarity Search
Real vector similarity search for cases.
- Endpoints: `GET /ai/similar-cases/{case_id}`, `POST /ai/similar/{case_id}`

### 2.10 AI Case Summarization
Real AI summarization using Ollama.
- Endpoint: `POST /ai/summarize/{case_id}`
- Output: summary, key_points, risk_assessment, recommendations

### 2.11 DOCX Report Generator
Generate Word documents from case data.
- Endpoint: `GET /reports/case/{case_id}.docx`
- Sections: Cover page, executive summary, case details, timeline, findings, evidence, similar cases, entities

### 2.12 Report Templates
Configurable report templates.
- Templates: STANDARD, EXECUTIVE_SUMMARY, DETAILED, COMPLIANCE

---

## Phase 3: Frontend & Collaboration (COMPLETED)

### 3.1 Frontend Setup
React application with Vite, TypeScript, TailwindCSS.
- Tech: React 18, Vite, TypeScript, TailwindCSS, React Query, React Router v6

### 3.2 Dashboard Page
Main dashboard with case overview and statistics.
- Features: Case statistics, recent cases, critical cases

### 3.3 Case List Page
Searchable, filterable case list.
- Features: Search, filter by status/severity, sortable table, case detail with tabs

### 3.4 Case Detail Page Enhancements
Full case view with AI Analysis tab and report generation.
- Features: AI analysis, report generation, evidence upload, subject details

### 3.5 Case Create/Edit Form
Form for creating and editing cases with validation.
- Features: Required fields, validation, tags input, custom metadata

### 3.6 Reports Page
Dedicated page for report generation.
- Features: Template selection, case search, one-click generation

### 3.7 Admin Pages
User and system administration.
- Features: User listing, creation, editing, deactivation, statistics
- Endpoints: `GET /auth/users`, `PATCH /auth/users/{id}`, `DELETE /auth/users/{id}`

### 3.8 Nextcloud Integration
File storage and collaboration platform with WebDAV.
- Port: 18081
- Features: WebDAV operations, auto-create case folders, share links
- Endpoints: `/nextcloud/health`, `/nextcloud/case/{case_id}/folder`, `/nextcloud/case/{case_id}/files`

### 3.9 ONLYOFFICE Integration
In-browser document editing via ONLYOFFICE Document Server.
- Port: 18082
- Features: JWT authentication, document type detection, edit/view buttons
- Editable: .docx, .xlsx, .pptx, .odt, .ods, .odp
- Viewable: .pdf, .doc, .xls, .ppt, .txt, .rtf, .csv, .html

### 3.10 Real-time Updates
WebSocket-based live updates.
- Endpoint: `WS /ws/cases/{case_id}`
- Features: Presence tracking, real-time notifications, auto-reconnect, heartbeat

### 3.11 Analytics Dashboard
Visual analytics with charts.
- Endpoints: `/analytics/overview`, `/analytics/cases`, `/analytics/trends`, `/analytics/full`
- Features: Stat cards, trends, status/severity distribution, entity insights, user activity

### 3.12 Workflow Automation
Automated case state transitions and notifications.
- Triggers: STATUS_CHANGE, TIME_BASED, EVENT, CONDITION
- Actions: CHANGE_STATUS, ASSIGN_USER, ADD_TAG, SEND_NOTIFICATION, CREATE_TIMELINE
- Features: APScheduler, notification center, execution history

### 3.13 Advanced Search
Full-text and semantic search across all content.
- Endpoints: `GET /search`, `GET /search/suggest`
- Features: Hybrid search (keyword 40% + semantic 60%), entity filtering, debounced input

### 3.14 Evidence-Nextcloud Bidirectional Sync
Automatic sync between MinIO evidence storage and Nextcloud.
- Endpoints: `/evidence/cases/{case_id}/sync-to-nextcloud`, `/evidence/cases/{case_id}/import-from-nextcloud`
- Features: Auto-sync on upload, import from Nextcloud, deduplication

---

## Phase 4: Production Hardening (COMPLETED - 100%)

### Security Hardening

#### 4.1 Rate Limiting (COMPLETED)
API rate limiting with slowapi.
- Auth: 10/min, General: 60/min

#### 4.2 Security Headers (COMPLETED)
Security headers middleware (CSP, HSTS, X-Frame-Options).

#### 4.3 CORS Hardening (COMPLETED)
Specific origins instead of wildcard.

#### 4.4 Production API Configuration (COMPLETED)
Disable docs/redoc in production.

#### 4.5 Dependency Scanning (COMPLETED)
pip-audit, npm audit, Trivy in CI.

### Testing Infrastructure

#### 4.6 pytest Setup (COMPLETED)
pytest with fixtures, async support, coverage.

#### 4.7 API Endpoint Tests (COMPLETED)
18 auth tests, 35% coverage.

#### 4.8 CI/CD Pipeline (COMPLETED)
GitHub Actions with lint, test, build, security scanning.

#### 4.9 Pre-commit Hooks (COMPLETED)
ruff, mypy, detect-secrets.

### Observability

#### 4.10 Structured Logging (COMPLETED)
structlog with JSON output, correlation IDs.

#### 4.11 Prometheus Metrics (COMPLETED)
`/metrics` endpoint, custom business metrics.

#### 4.12 Error Tracking (COMPLETED)
Sentry integration with FastAPI, SQLAlchemy, and logging integrations.
- User context via JWT middleware
- Performance monitoring (10% sample rate)
- Environment variables: `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE`

### Infrastructure Hardening

#### 4.13 Docker Security (COMPLETED)
Non-root users, resource limits.

#### 4.14 Database Optimization (COMPLETED)
PgBouncer connection pooler for API database connections.
- Port: 16432 (external), 5432 (internal)
- Pool mode: transaction (best for async apps)
- Only API routes through PgBouncer (Paperless/Nextcloud use direct connections)
- SQLAlchemy uses NullPool, statement caching disabled
- Migrations bypass PgBouncer via POSTGRES_DIRECT_URL

#### 4.15 Redis Caching (COMPLETED)
Cache-aside pattern for frequently accessed data.
- Files: `api/app/services/cache_service.py`, `api/app/dependencies.py`
- Uses existing Redis (DB 1, Paperless uses DB 0)
- orjson for fast serialization
- Graceful degradation (cache failures don't break app)
- Cached endpoints: analytics (10-30 min TTL), scopes (24 hr TTL)
- Cache invalidation on case create/update/delete
- Health check at `/ready` shows cache status

### Production Security

#### 4.16 Secret Management (COMPLETED)
SOPS + age for encrypted secrets.
- Files: `.sops.yaml`, `secrets/`, `scripts/setup-secrets.sh`, `scripts/decrypt-secrets.sh`
- Docker Compose secrets section configured

#### 4.17 SSL/TLS (COMPLETED)
Caddy reverse proxy with automatic HTTPS.
- Port: 443 (HTTPS), 80 (HTTP redirect)
- TLS modes: "internal" (self-signed for dev), empty (Let's Encrypt for prod)
- HTTP/3 (QUIC) support
- Automatic certificate management
- Files: `configs/caddy/Caddyfile`, `configs/caddy/Caddyfile.prod`
- Environment: `DOMAIN`, `TLS_MODE`, `ACME_EMAIL`

#### 4.18 Database Migrations (COMPLETED)
Alembic for schema version control.

#### 4.19 Backup Strategy (COMPLETED)
pg_dump, mc mirror, 7-day retention.
- Scripts: `backup-all.sh`, `backup-database.sh`, `backup-minio.sh`, `restore-database.sh`, `restore-minio.sh`

#### 4.20 Load Testing (COMPLETED)
k6 load testing framework with Docker-based execution.
- Directory: `load-tests/` with config, thresholds, scenarios
- Test types: smoke (1 VU, 1 min), load (50 VUs, 8 min), stress (200 VUs, 10 min)
- Scenarios: Browse cases (40%), Analytics (20%), Search (20%), Create (15%), Profile (5%)
- SLOs: p95 latency thresholds, <1% error rate
- Runner: `./load-tests/run-tests.sh [smoke|load|stress]`

#### 4.21 Monitoring and Alerting (COMPLETED)
Grafana dashboards with Prometheus metrics collection.
- Prometheus: Port 19090, scrapes API /metrics, postgres_exporter, redis_exporter
- Grafana: Port 19091, pre-provisioned datasource
- Exporters: postgres_exporter (PostgreSQL metrics), redis_exporter (Redis metrics)
- Alert rules: HighErrorRate, HighLatency, APIDown, PostgreSQLDown, RedisDown, etc.
- Access: http://localhost:19091 (admin/admin123)

---

## Phase 5: Future Enhancements (PLANNED)

### Feature Enhancements

#### 5.1 Mobile Responsive Improvements
Optimize UI for mobile devices.

#### 5.2 Email Notifications
SMTP integration for email alerts.

#### 5.3 Bulk Case Operations
Select and operate on multiple cases.

#### 5.4 Custom Report Templates
User-uploaded DOCX templates.

### Kubernetes Migration

#### 5.5 Kubernetes Manifests
K8s deployment manifests (when scaling triggers are met).

#### 5.6 Helm Charts
Package application as Helm chart.

### Admin GUI Enhancements

#### 5.7 Remote Backup Storage
Support for S3, NFS, SMB, rsync backup destinations.

#### 5.8 System Settings Admin Page
Centralized GUI for all system configuration.
