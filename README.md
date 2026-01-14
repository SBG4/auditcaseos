# AuditCaseOS

Internal audit case management system with AI-powered analysis, evidence vault, and smart report generation.

## Features

- **Unified Case ID System**: Automatic ID generation in `SCOPE-TYPE-SEQ` format (e.g., `FIN-USB-0001`)
- **Case Types**: USB, EMAIL, WEB, POLICY
- **Scopes**: FIN, HR, IT, SEC, OPS, CORP, LEGAL, RND
- **Evidence Vault**: Secure MinIO storage with audit trail
- **AI Analysis**: Local Ollama LLM for case summaries and insights
- **Full Audit Log**: Every action tracked

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
```

### 4. Access the System

| Service | URL |
|---------|-----|
| API Docs (Swagger) | http://localhost:18000/docs |
| API (OpenAPI JSON) | http://localhost:18000/openapi.json |
| MinIO Console | http://localhost:19001 |
| Health Check | http://localhost:18000/health |

## API Endpoints

### Cases
- `GET /api/v1/cases` - List all cases (with filters)
- `POST /api/v1/cases` - Create new case
- `GET /api/v1/cases/{case_id}` - Get case details
- `PATCH /api/v1/cases/{case_id}` - Update case
- `DELETE /api/v1/cases/{case_id}` - Archive case

### Evidence
- `POST /api/v1/evidence/cases/{case_id}/evidence` - Upload evidence
- `GET /api/v1/evidence/cases/{case_id}/evidence` - List case evidence
- `GET /api/v1/evidence/{evidence_id}/download` - Download file

### AI
- `POST /api/v1/ai/summarize/{case_id}` - Generate AI summary
- `POST /api/v1/ai/similar/{case_id}` - Find similar cases

### Scopes
- `GET /api/v1/scopes` - List all department scopes

## Case ID Format

Cases are automatically assigned IDs in the format:

```
SCOPE-TYPE-SEQ

Examples:
- FIN-USB-0001   (Finance dept, USB exfiltration, first case)
- HR-EMAIL-0003  (HR dept, Email incident, third case)
- SEC-POLICY-0012 (Security dept, Policy violation)
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AuditCaseOS                          │
├─────────────────────────────────────────────────────────┤
│  FastAPI Backend (:18000)                               │
│  ├── Cases, Evidence, Findings, Timeline                │
│  ├── AI-powered summaries (Ollama)                      │
│  └── Full audit logging                                 │
├─────────────────────────────────────────────────────────┤
│  PostgreSQL + pgvector (:15432)                         │
│  └── Cases, Users, Evidence metadata, Embeddings        │
├─────────────────────────────────────────────────────────┤
│  MinIO (:19000/:19001)                                  │
│  └── Evidence file storage                              │
├─────────────────────────────────────────────────────────┤
│  Ollama (:21434)                                        │
│  └── Local LLM for AI features                          │
└─────────────────────────────────────────────────────────┘
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

### Access Database

```bash
docker exec -it auditcaseos-db psql -U auditcaseos -d auditcaseos
```

### Stop Everything

```bash
docker compose down
```

### Reset Everything (including data)

```bash
docker compose down -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | auditcaseos | Database user |
| `POSTGRES_PASSWORD` | auditcaseos_secret | Database password |
| `POSTGRES_DB` | auditcaseos | Database name |
| `MINIO_ROOT_USER` | minioadmin | MinIO admin user |
| `MINIO_ROOT_PASSWORD` | minioadmin123 | MinIO admin password |
| `MINIO_BUCKET` | evidence | Evidence bucket name |
| `SECRET_KEY` | (set in .env) | API secret key |
| `OLLAMA_MODEL` | llama3.2 | Ollama model to use |

## Phase 2 (Planned)

- Paperless-ngx for OCR
- Entity extraction (employee IDs, hostnames)
- DOCX report generation
- Advanced RAG with vector search

## Phase 3 (Future)

- React frontend
- Nextcloud + ONLYOFFICE integration
- Advanced analytics dashboard
