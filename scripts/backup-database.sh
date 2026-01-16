#!/bin/bash
# PostgreSQL Backup Script for AuditCaseOS
# Uses pg_dump with custom format (-Fc) for compression and selective restore
# Source: postgresql.org best practices

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
CONTAINER_NAME="${CONTAINER_NAME:-auditcaseos-db}"
POSTGRES_USER="${POSTGRES_USER:-auditcaseos}"
DATE=$(date +%Y%m%d_%H%M%S)

# Databases to backup
DATABASES=("auditcaseos" "paperless" "nextcloud")

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

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

log_info "Starting PostgreSQL backup..."
log_info "Backup directory: $BACKUP_DIR"
log_info "Retention: $RETENTION_DAYS days"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_error "Container $CONTAINER_NAME is not running!"
    exit 1
fi

# Backup each database
BACKUP_SUCCESS=true
for db in "${DATABASES[@]}"; do
    BACKUP_FILE="${BACKUP_DIR}/${db}_${DATE}.dump"
    log_info "Backing up database: $db"

    if docker exec "$CONTAINER_NAME" pg_dump -U "$POSTGRES_USER" -Fc "$db" > "$BACKUP_FILE" 2>/dev/null; then
        # Verify backup file was created and has content
        if [ -s "$BACKUP_FILE" ]; then
            SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            log_info "Successfully backed up $db ($SIZE)"
        else
            log_error "Backup file for $db is empty!"
            rm -f "$BACKUP_FILE"
            BACKUP_SUCCESS=false
        fi
    else
        log_error "Failed to backup database: $db"
        rm -f "$BACKUP_FILE"
        BACKUP_SUCCESS=false
    fi
done

# Cleanup old backups
log_info "Cleaning up backups older than $RETENTION_DAYS days..."
DELETED_COUNT=0
while IFS= read -r -d '' file; do
    rm -f "$file"
    ((DELETED_COUNT++))
done < <(find "$BACKUP_DIR" -name "*.dump" -type f -mtime +$RETENTION_DAYS -print0 2>/dev/null)

if [ $DELETED_COUNT -gt 0 ]; then
    log_info "Deleted $DELETED_COUNT old backup(s)"
fi

# Summary
echo ""
log_info "=== Backup Summary ==="
log_info "Date: $(date)"
log_info "Location: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"/*_${DATE}.dump 2>/dev/null || true

if [ "$BACKUP_SUCCESS" = true ]; then
    log_info "PostgreSQL backup completed successfully!"
    exit 0
else
    log_error "PostgreSQL backup completed with errors!"
    exit 1
fi
