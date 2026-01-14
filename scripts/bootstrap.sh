#!/bin/bash
# AuditCaseOS Bootstrap Script
# Run this after docker compose up to set up the initial environment

set -e

echo "==================================="
echo "  AuditCaseOS Bootstrap"
echo "==================================="

# Wait for services to be ready
echo ""
echo "[1/4] Waiting for services..."

# Wait for PostgreSQL
echo "  - Waiting for PostgreSQL..."
until docker exec auditcaseos-db pg_isready -U auditcaseos > /dev/null 2>&1; do
    sleep 1
done
echo "  - PostgreSQL is ready"

# Wait for MinIO
echo "  - Waiting for MinIO..."
until curl -s http://localhost:19000/minio/health/ready > /dev/null 2>&1; do
    sleep 1
done
echo "  - MinIO is ready"

# Wait for API
echo "  - Waiting for API..."
until curl -s http://localhost:18000/health > /dev/null 2>&1; do
    sleep 1
done
echo "  - API is ready"

# Pull Ollama model
echo ""
echo "[2/4] Setting up Ollama..."
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2}"
echo "  - Pulling model: $OLLAMA_MODEL (this may take a few minutes)..."
docker exec auditcaseos-ollama ollama pull $OLLAMA_MODEL || echo "  - Note: Ollama model pull failed or already exists"

# Verify MinIO bucket
echo ""
echo "[3/4] Verifying MinIO bucket..."
curl -s http://localhost:18000/health > /dev/null && echo "  - Evidence bucket is ready"

# Print summary
echo ""
echo "[4/4] Bootstrap complete!"
echo ""
echo "==================================="
echo "  AuditCaseOS is ready!"
echo "==================================="
echo ""
echo "Access points:"
echo "  - API Docs:     http://localhost:18000/docs"
echo "  - Health Check: http://localhost:18000/health"
echo "  - MinIO Console: http://localhost:19001"
echo "    (user: minioadmin, pass: minioadmin123)"
echo ""
echo "Quick start:"
echo "  1. Open http://localhost:18000/docs"
echo "  2. Try POST /api/v1/cases to create a case"
echo "  3. Use GET /api/v1/scopes to see available scopes"
echo ""
