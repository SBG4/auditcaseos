# AuditCaseOS Roadmap

## Current Status

| Metric | Value |
|--------|-------|
| Version | 0.7.3 |
| Total Features | 61 |
| Completed | 53 |
| In Progress | 0 |
| Pending | 8 |
| Completion | 87% |

## Phase Status

| Phase | Features | Status |
|-------|----------|--------|
| Phase 1: Core Platform | 12/12 | COMPLETED |
| Phase 2: Document Intelligence | 12/12 | COMPLETED |
| Phase 3: Frontend & Collaboration | 14/14 | COMPLETED |
| Phase 4: Production Hardening | 15/21 (71%) | IN PROGRESS |
| Phase 5: Future Enhancements | 0/8 | PLANNED |

---

## Phase 4: Production Hardening (Current)

### Priority 1 - Next Steps

| Feature | Status | Description |
|---------|--------|-------------|
| 4.16 | PENDING | Secret Management (SOPS + age) |
| 4.17 | PENDING | SSL/TLS (HTTPS) |

### Priority 2 - Remaining

| Feature | Status | Description |
|---------|--------|-------------|
| 4.12 | PENDING | Error Tracking (Sentry) |
| 4.14 | PENDING | Database Optimization (PgBouncer) |
| 4.15 | PENDING | Redis Caching |
| 4.20 | PENDING | Load Testing |
| 4.21 | PENDING | Monitoring/Alerting (Grafana) |

### Completed in Phase 4

| Feature | Description |
|---------|-------------|
| 4.1 | Rate Limiting (slowapi) |
| 4.2 | Security Headers (CSP, HSTS, X-Frame-Options) |
| 4.3 | CORS Hardening |
| 4.4 | Production API Config |
| 4.5 | Dependency Scanning |
| 4.6 | pytest Setup |
| 4.7 | API Endpoint Tests (18 tests) |
| 4.8 | CI/CD Pipeline (GitHub Actions) |
| 4.9 | Pre-commit Hooks |
| 4.10 | Structured Logging (structlog) |
| 4.11 | Prometheus Metrics |
| 4.13 | Docker Security (non-root, resource limits) |
| 4.18 | Database Migrations (Alembic) |
| 4.19 | Backup Strategy (42 test cases) |

---

## Phase 5: Future Enhancements

### Feature Enhancements

| Feature | Description |
|---------|-------------|
| 5.1 | Mobile Responsive Improvements |
| 5.2 | Email Notifications (SMTP) |
| 5.3 | Bulk Case Operations |
| 5.4 | Custom Report Templates |

### Kubernetes Migration (Deferred)

| Feature | Description |
|---------|-------------|
| 5.5 | Kubernetes Manifests |
| 5.6 | Helm Charts |

**Migration Triggers** (implement K8s only when needed):
- 99.9%+ uptime SLA requirements
- Multi-region deployment needs
- Auto-scaling requirements
- Team size exceeds 25 engineers
- Traffic spikes causing Docker Compose limits

**Recommended Path**:
1. K3s for lightweight Kubernetes (if self-hosting)
2. DigitalOcean Kubernetes (DOKS) for cost-sensitive
3. GKE/EKS/AKS for full managed Kubernetes

### Admin GUI Enhancements

| Feature | Description |
|---------|-------------|
| 5.7 | Remote Backup Storage (S3, NFS, SMB, rsync) |
| 5.8 | System Settings Admin Page |

---

## Decision Rationale

### Why Docker Compose First?

Based on research findings:
- Production improvements are platform-agnostic (transfer to K8s if needed)
- K8s operational overhead not justified for teams < 25 engineers
- 77% of K8s practitioners report ongoing issues (CNCF 2024)
- Self-managed K8s costs 3x more than alternatives
- Current 9-service setup well within Docker Compose capabilities

**Source**: https://www.cncf.io/blog/2025/11/18/top-5-hard-earned-lessons-from-the-experts-on-managing-kubernetes/

---

## Quick Commands

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f api

# Rebuild API
docker compose up -d --build api

# Rebuild Frontend
docker compose up -d --build frontend

# Stop services
docker compose down

# Reset all data
docker compose down -v

# Access database
docker exec -it auditcaseos-db psql -U auditcaseos -d auditcaseos

# Pull Ollama model
docker exec -it auditcaseos-ollama ollama pull llama3.2

# Run backup tests
./scripts/test-backup.sh

# Run full backup
./scripts/backup-all.sh
```

---

## Service URLs

| Service | URL |
|---------|-----|
| API Docs | http://localhost:18000/docs |
| Health Check | http://localhost:18000/health |
| Frontend | http://localhost:13000 |
| MinIO Console | http://localhost:19001 |
| Paperless | http://localhost:18080 |
| Nextcloud | http://localhost:18081 |
| ONLYOFFICE | http://localhost:18082 |

---

## Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| MinIO | minioadmin | minioadmin123 |
| PostgreSQL | auditcaseos | auditcaseos_secret |
| Paperless | admin | admin123 |
| Nextcloud | admin | admin123 |
| API (default admin) | admin@example.com | admin123 |
