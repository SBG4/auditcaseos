# AuditCaseOS

Internal audit case management system with AI-powered analysis, evidence vault, document editing, real-time collaboration, and smart report generation.

**Version: 0.5.4** | **Progress: 37/38 features (97%)**

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

### Phase 3: Collaboration & Enterprise (13/14 features - 93%)
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
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  Nextcloud   │  │  ONLYOFFICE  │                             │
│  │   :18081     │  │   :18082     │                             │
│  │  (Collab)    │  │  (Editing)   │                             │
│  └──────────────┘  └──────────────┘                             │
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

Run all tests:
```bash
bash scripts/test-all.sh              # 19 core tests
bash scripts/test-evidence-sync.sh    # 24 sync tests
bash scripts/test-onlyoffice.sh       # 24 ONLYOFFICE tests
# Total: 67 tests
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
| `NEXTCLOUD_ADMIN_USER` | admin | Nextcloud admin |
| `NEXTCLOUD_ADMIN_PASSWORD` | admin123 | Nextcloud password |
| `ONLYOFFICE_JWT_SECRET` | auditcaseos-onlyoffice-secret | JWT for ONLYOFFICE |
| `NEXTCLOUD_EXTERNAL_URL` | http://localhost:18081 | Browser access to Nextcloud |
| `ONLYOFFICE_EXTERNAL_URL` | http://localhost:18082 | Browser access to ONLYOFFICE |

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

## Recent Updates (v0.5.4)

- **Advanced Search**: Hybrid keyword + semantic search across all content
- **Global Search Bar**: Header search with auto-suggestions
- **Workflow Automation**: Rule-based triggers with notifications
- **Analytics Dashboard**: Visual charts for metrics and trends
- **WebSocket Updates**: Real-time case collaboration
- **Notification Center**: In-app notifications with priorities

## Remaining Features

- **Feature 3.10**: Real-time Collaboration (presence, cursors)

## License

Proprietary - Internal Use Only
