---
name: build
description: Build and start all Docker services
---

Build and start all AuditCaseOS services.

## Commands

```bash
# Build all services and start
docker compose build && docker compose up -d

# Or rebuild a specific service
docker compose up -d --build api
docker compose up -d --build frontend
```

## Verify

After building, check service health:

```bash
# Check all containers are running
docker compose ps

# Check API health
curl http://localhost:18000/health

# Check frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:13000
```
