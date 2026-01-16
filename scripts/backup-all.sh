#!/bin/bash
# Combined Backup Script for AuditCaseOS
# Runs both PostgreSQL and MinIO backups
# Can be scheduled via cron or APScheduler

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
export BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
export RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Create main backup directory
mkdir -p "$BACKUP_DIR"

START_TIME=$(date +%s)
POSTGRES_STATUS="SKIPPED"
MINIO_STATUS="SKIPPED"

log_header "AuditCaseOS Full Backup"
log_info "Backup directory: $BACKUP_DIR"
log_info "Retention: $RETENTION_DAYS days"

# Run PostgreSQL backup
log_header "PostgreSQL Backup"
export BACKUP_DIR="$BACKUP_DIR/postgres"
if "$SCRIPT_DIR/backup-database.sh"; then
    POSTGRES_STATUS="SUCCESS"
else
    POSTGRES_STATUS="FAILED"
    log_error "PostgreSQL backup failed!"
fi

# Run MinIO backup
log_header "MinIO Backup"
export BACKUP_DIR="$BACKUP_DIR/minio"
if "$SCRIPT_DIR/backup-minio.sh"; then
    MINIO_STATUS="SUCCESS"
else
    MINIO_STATUS="FAILED"
    log_error "MinIO backup failed!"
fi

# Calculate duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Final summary
log_header "Backup Complete"
log_info "Date: $(date)"
log_info "Duration: ${DURATION}s"
log_info "PostgreSQL: $POSTGRES_STATUS"
log_info "MinIO: $MINIO_STATUS"
echo ""

# List recent backups
log_info "Recent PostgreSQL backups:"
ls -lht "$PROJECT_DIR/backups/postgres/"*.dump 2>/dev/null | head -5 || echo "  No PostgreSQL backups found"
echo ""

log_info "Recent MinIO backups:"
ls -dt "$PROJECT_DIR/backups/minio/"*_* 2>/dev/null | head -5 || echo "  No MinIO backups found"
echo ""

# Exit with error if any backup failed
if [ "$POSTGRES_STATUS" = "FAILED" ] || [ "$MINIO_STATUS" = "FAILED" ]; then
    log_error "One or more backups failed!"
    exit 1
fi

log_info "All backups completed successfully!"

# Cron scheduling hint
echo ""
log_info "To schedule daily backups, add to crontab:"
echo "  0 2 * * * $SCRIPT_DIR/backup-all.sh >> /var/log/auditcaseos-backup.log 2>&1"
