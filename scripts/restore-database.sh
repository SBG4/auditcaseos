#!/bin/bash
# PostgreSQL Restore Script for AuditCaseOS
# Restores from pg_dump backup and runs ANALYZE for optimizer statistics
# Source: postgresql.org best practices

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
CONTAINER_NAME="${CONTAINER_NAME:-auditcaseos-db}"
POSTGRES_USER="${POSTGRES_USER:-auditcaseos}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

usage() {
    echo "Usage: $0 <backup_file> [database_name]"
    echo ""
    echo "Arguments:"
    echo "  backup_file     Path to the .dump backup file"
    echo "  database_name   Optional: Override database name (default: extracted from filename)"
    echo ""
    echo "Examples:"
    echo "  $0 ./backups/postgres/auditcaseos_20260116_120000.dump"
    echo "  $0 ./backups/postgres/auditcaseos_20260116_120000.dump my_test_db"
    echo ""
    echo "Available backups:"
    ls -lht "$BACKUP_DIR"/*.dump 2>/dev/null | head -10 || echo "  No backups found in $BACKUP_DIR"
    exit 1
}

# Check arguments
if [ $# -lt 1 ]; then
    usage
fi

BACKUP_FILE="$1"
DATABASE_NAME="${2:-}"

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Extract database name from filename if not provided
if [ -z "$DATABASE_NAME" ]; then
    FILENAME=$(basename "$BACKUP_FILE")
    DATABASE_NAME=$(echo "$FILENAME" | sed 's/_[0-9]\{8\}_[0-9]\{6\}\.dump$//')
    log_info "Extracted database name: $DATABASE_NAME"
fi

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_error "Container $CONTAINER_NAME is not running!"
    exit 1
fi

# Confirmation prompt
echo ""
log_warn "=== RESTORE CONFIRMATION ==="
log_warn "This will OVERWRITE the current database!"
echo ""
echo "Backup file: $BACKUP_FILE"
echo "Target database: $DATABASE_NAME"
echo "Container: $CONTAINER_NAME"
echo ""
read -p "Are you sure you want to proceed? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log_info "Restore cancelled."
    exit 0
fi

log_info "Starting PostgreSQL restore..."

# Stop services that might be using the database
log_warn "Note: You may need to stop dependent services (api, paperless) before restore"

# Drop and recreate database
log_info "Dropping existing database: $DATABASE_NAME"
docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS $DATABASE_NAME;" postgres 2>/dev/null || true

log_info "Creating fresh database: $DATABASE_NAME"
docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -c "CREATE DATABASE $DATABASE_NAME;" postgres

# Restore from backup
log_info "Restoring from backup..."
cat "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" pg_restore -U "$POSTGRES_USER" -d "$DATABASE_NAME" --no-owner --no-privileges 2>&1 | {
    while IFS= read -r line; do
        # Filter out non-critical warnings
        if [[ ! "$line" =~ "WARNING" ]] && [[ ! "$line" =~ "already exists" ]]; then
            echo "$line"
        fi
    done
}

# Run ANALYZE to update optimizer statistics
log_info "Running ANALYZE to update optimizer statistics..."
docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$DATABASE_NAME" -c "ANALYZE;" 2>/dev/null

# Verify restore
log_info "Verifying restore..."
TABLE_COUNT=$(docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$DATABASE_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')

echo ""
log_info "=== Restore Summary ==="
log_info "Database: $DATABASE_NAME"
log_info "Tables restored: $TABLE_COUNT"
log_info "Backup file: $BACKUP_FILE"
log_info "PostgreSQL restore completed successfully!"
log_info ""
log_warn "Remember to restart dependent services (docker compose restart api)"
