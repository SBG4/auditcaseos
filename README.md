# AuditCaseOS

Internal audit case management system with AI-powered analysis, evidence vault, document editing, and smart report generation.

## Features

### Core (Phase 1)
- **Unified Case ID System**: Automatic ID generation in `SCOPE-TYPE-SEQ` format (e.g., `FIN-USB-0001`)
- **Case Types**: USB, EMAIL, WEB, POLICY
- **Scopes**: FIN, HR, IT, SEC, OPS, CORP, LEGAL, RND, PRO, MKT, QA, ENV, SAF, EXT, GOV, GEN
- **Evidence Vault**: Secure MinIO storage with audit trail
- **AI Analysis**: Local Ollama LLM for case summaries and insights
- **Full Audit Log**: Every action tracked

### Document Intelligence (Phase 2)
- **OCR Processing**: Paperless-ngx for document text extraction
- **Entity Extraction**: Automatic detection of employee IDs, hostnames, IPs
- **Report Generation**: DOCX reports from templates
- **Vector Search**: Semantic search with pgvector embeddings

### Collaboration (Phase 3) - Current
- **React Frontend**: Modern SPA with TypeScript and TailwindCSS
- **Nextcloud Integration**: File collaboration and case folders
- **ONLYOFFICE**: In-browser document editing (DOCX, XLSX, PPTX)
- **Bidirectional Sync**: Evidence syncs between API and Nextcloud

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

### 3. Pull Ollama Model (first time only)

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
- `POST /api/v1/evidence/cases/{case_id}` - Upload evidence
- `GET /api/v1/evidence/cases/{case_id}` - List case evidence
- `GET /api/v1/evidence/{evidence_id}/download` - Download file
- `POST /api/v1/evidence/cases/{case_id}/sync-to-nextcloud` - Sync to Nextcloud
- `POST /api/v1/evidence/cases/{case_id}/import-from-nextcloud` - Import from Nextcloud

### AI
- `POST /api/v1/ai/summarize/{case_id}` - Generate AI summary
- `POST /api/v1/ai/similar/{case_id}` - Find similar cases
- `POST /api/v1/ai/extract-entities` - Extract entities from text

### ONLYOFFICE
- `GET /api/v1/onlyoffice/health` - ONLYOFFICE health check
- `GET /api/v1/onlyoffice/extensions` - Supported file types
- `GET /api/v1/onlyoffice/edit-url` - Get document edit URL

### Users & Auth
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/users/me` - Current user profile
- `POST /api/v1/users` - Create user (admin only)

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

## Project Tracking

Full project specification is maintained in `PROJECT_SPEC.xml` including:
- Feature roadmap and status
- Database schemas
- API specifications
- Changelog

Current version: **0.4.8**
