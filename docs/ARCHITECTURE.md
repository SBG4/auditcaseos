# AuditCaseOS Architecture

## System Overview

AuditCaseOS is an internal audit case management system with AI-powered analysis, evidence vault, and smart report generation. A composed-from-existing-projects dockerized bundle designed to be forked and evolved.

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
│  │  (Collab)    │  │  (Editing)   │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 + pgvector |
| Storage | MinIO (S3-compatible) |
| AI/LLM | Ollama (local - llama3.2, nomic-embed-text) |
| OCR | Paperless-ngx |
| Frontend | React + Vite + TypeScript + TailwindCSS |
| Collaboration | Nextcloud + ONLYOFFICE |

## Service Ports

| Service | External Port | Internal Port | Description |
|---------|---------------|---------------|-------------|
| Frontend | 13000 | 80 | React SPA |
| API | 18000 | 8000 | FastAPI backend |
| PostgreSQL | 15432 | 5432 | PostgreSQL + pgvector |
| MinIO API | 19000 | 9000 | MinIO S3 API |
| MinIO Console | 19001 | 9001 | MinIO Web Console |
| Ollama | 21434 | 11434 | Ollama LLM API |
| Paperless | 18080 | 8000 | Paperless-ngx OCR |
| Nextcloud | 18081 | 80 | Nextcloud file collaboration |
| ONLYOFFICE | 18082 | 80 | ONLYOFFICE Document Server |

## URL Architecture

### Critical Rule: Internal vs External URLs

**INTERNAL URLs** - For server-to-server communication within Docker network:
- `postgres:5432`
- `minio:9000`
- `redis:6379`
- `http://ollama:11434`
- `http://paperless:8000`
- `http://nextcloud`
- `http://onlyoffice`
- `http://api:8000`

**EXTERNAL URLs** - For browser/user access from host machine:
- `localhost:15432` (PostgreSQL)
- `localhost:19000` (MinIO API)
- `localhost:19001` (MinIO Console)
- `localhost:21434` (Ollama)
- `localhost:18080` (Paperless)
- `localhost:18081` (Nextcloud)
- `localhost:18082` (ONLYOFFICE)
- `localhost:18000` (API)
- `localhost:13000` (Frontend)

### URL Rules

| Rule | Severity | Description |
|------|----------|-------------|
| URL-1 | CRITICAL | Backend services MUST use INTERNAL URLs for server-to-server communication |
| URL-2 | CRITICAL | URLs returned to browsers MUST use EXTERNAL URLs |
| URL-3 | HIGH | NEVER hardcode URLs in service code - use config/environment variables |
| URL-4 | HIGH | NEVER use string replacement to convert internal to external URLs |
| URL-5 | MEDIUM | Default values in config.py should use INTERNAL Docker URLs |

## ONLYOFFICE Configuration

ONLYOFFICE has THREE distinct URL configurations that MUST be correct:

| Setting | Type | Purpose | Correct Value |
|---------|------|---------|---------------|
| DocumentServerUrl | EXTERNAL | URL browsers use to load ONLYOFFICE editor | `http://localhost:18082` |
| DocumentServerInternalUrl | INTERNAL | URL Nextcloud uses to communicate with ONLYOFFICE | `http://onlyoffice` |
| StorageUrl | INTERNAL | URL ONLYOFFICE uses to fetch files from Nextcloud | `http://nextcloud/` |

**JWT Configuration**: JWT secret MUST match between ONLYOFFICE server and Nextcloud connector.

**Edit URL Format**: Use Nextcloud file ID (integer), not file path. Get ID via WebDAV PROPFIND.

## NGINX Guidelines

| Rule | Severity | Description |
|------|----------|-------------|
| NGINX-1 | CRITICAL | Set `client_max_body_size 100M` for file uploads |
| NGINX-2 | HIGH | Disable buffering for large uploads: `proxy_request_buffering off` |
| NGINX-3 | MEDIUM | Use internal Docker DNS for proxy_pass: `http://api:8000` |

## Common Failure Patterns

### 1. localhost-in-container (CRITICAL)
- **Symptom**: Service timeouts, connection refused errors
- **Cause**: localhost inside container refers to container itself
- **Fix**: Use Docker service names (e.g., `http://nextcloud`)

### 2. internal-url-to-browser (CRITICAL)
- **Symptom**: Browser shows "cannot connect" or DNS resolution failure
- **Cause**: Browsers cannot resolve Docker DNS names
- **Fix**: Return external URLs for browser consumption

### 3. string-replacement-urls (HIGH)
- **Symptom**: URLs break when format changes
- **Cause**: Fragile string manipulation
- **Fix**: Use separate config variables for internal and external URLs

### 4. hardcoded-ports (HIGH)
- **Symptom**: App breaks with different port mappings
- **Fix**: All external ports should come from environment variables

### 5. missing-nginx-limits (HIGH)
- **Symptom**: 413 Request Entity Too Large
- **Cause**: nginx default client_max_body_size is 1MB
- **Fix**: Set client_max_body_size in both server and location blocks

## Implementation Checklist

Before completing any feature:

- [ ] All URLs in code come from configuration, not hardcoded
- [ ] Internal URLs use Docker service names (`http://service-name`)
- [ ] External URLs returned to browser use `localhost:PORT` or domain
- [ ] Environment variables added to docker-compose.yml for external URLs
- [ ] nginx configured with appropriate body size limits if uploading files
- [ ] Tests verify actual browser functionality, not just API responses
- [ ] Documentation updated with any new configuration requirements
- [ ] Tested with container restart to ensure config persists

## Directory Structure

```
auditcaseos/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── PROJECT_SPEC.xml
├── CLAUDE.md
│
├── api/                           # FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                   # Database migrations
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models/
│       ├── schemas/
│       ├── routers/
│       ├── services/
│       └── utils/
│
├── frontend/                      # React application
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/
│       ├── hooks/
│       ├── context/
│       └── types/
│
├── configs/
│   └── postgres/
│       ├── init.sql
│       ├── 00-create-paperless-db.sh
│       └── 02-create-nextcloud-db.sh
│
├── scripts/
│   ├── backup-all.sh
│   ├── backup-database.sh
│   ├── backup-minio.sh
│   ├── restore-database.sh
│   ├── restore-minio.sh
│   └── test-backup.sh
│
├── backups/                       # Backup storage (gitignored)
│   ├── postgres/
│   └── minio/
│
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md
│   ├── FEATURES.md
│   ├── CONVENTIONS.md
│   ├── ROADMAP.md
│   ├── CHANGELOG.md
│   └── AGENT_PATTERNS.md
│
└── .claude/
    └── commands/                  # Claude Code commands
```

## Case ID System

**Format**: `SCOPE-TYPE-SEQ` (e.g., FIN-USB-0001)

### Scopes
| Code | Name | Description |
|------|------|-------------|
| FIN | Finance | Financial operations, accounting |
| HR | Human Resources | Employee data, personnel |
| IT | Information Technology | IT systems, infrastructure |
| SEC | Security | Physical and information security |
| OPS | Operations | Business operations |
| CORP | Corporate | Corporate and executive matters |
| LEGAL | Legal | Legal compliance, contracts |
| RND | Research & Development | R&D, innovation |
| PRO | Procurement | Purchasing, vendor management |
| MKT | Marketing | Marketing activities |
| QA | Quality Assurance | Quality control, testing |
| ENV | Environmental | Environmental compliance |
| SAF | Health & Safety | Workplace safety |
| EXT | External | External partnerships |
| GOV | Governance | Corporate governance |
| GEN | General | General audits |

### Types
| Code | Description |
|------|-------------|
| USB | USB/removable media incidents |
| EMAIL | Email-related incidents |
| WEB | Web/internet-related incidents |
| POLICY | Policy violations |

## End-to-End Flow

1. **Case Creation**: Investigator creates a case → Gets unique ID (e.g., FIN-USB-0001)
2. **Evidence Upload**: Files uploaded to MinIO at `/cases/{case_id}/`
3. **OCR Processing**: Paperless-ngx ingests files for OCR, text becomes searchable
4. **RAG Indexing**: Case fields, OCR text stored in pgvector with embeddings
5. **Report Generation**: DOCX generated from case data + RAG context

## Database Schema

### Core Tables
- `users` - User accounts with roles
- `scopes` - Department/scope definitions
- `cases` - Case records with metadata
- `case_sequences` - Auto-increment sequence tracking
- `evidence` - Evidence file metadata
- `findings` - Case findings with severity
- `timeline_events` - Chronological events
- `case_entities` - Extracted entities (IPs, emails, etc.)
- `embeddings` - pgvector embeddings for RAG
- `audit_log` - Activity audit trail

### Workflow Tables
- `workflow_rules` - Automation rule definitions
- `workflow_actions` - Actions to execute
- `workflow_history` - Execution history
- `notifications` - User notifications

## Testing

| Test Script | Tests | Description |
|-------------|-------|-------------|
| `scripts/test-all.sh` | 19 | Comprehensive API tests |
| `scripts/test-evidence-sync.sh` | 24 | Evidence-Nextcloud sync |
| `scripts/test-onlyoffice.sh` | 24 | ONLYOFFICE integration |
| `scripts/test-backup.sh` | 42 | Backup scripts |
| `api/tests/` | 18+ | pytest API tests |

**Total**: 100+ tests
