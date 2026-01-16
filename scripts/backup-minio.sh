#!/bin/bash
# MinIO Backup Script for AuditCaseOS
# Uses mc mirror for bucket backup (NOT Docker volume backup)
# Source: min.io/docs best practices
#
# IMPORTANT: Do NOT backup MinIO Docker volumes directly!
# MinIO uses filesystem-specific metadata that can be corrupted by volume backups.
# Always use mc mirror for reliable backups.

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups/minio}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
CONTAINER_NAME="${CONTAINER_NAME:-auditcaseos-minio}"
MINIO_ALIAS="${MINIO_ALIAS:-local}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:19000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin123}"
DATE=$(date +%Y%m%d_%H%M%S)

# Buckets to backup
BUCKETS=("evidence")

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

# Check if mc (MinIO Client) is installed locally, otherwise use Docker
MC_CMD=""
if command -v mc &> /dev/null; then
    MC_CMD="mc"
    log_info "Using local mc client"
else
    # Use mc from Docker container
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        MC_CMD="docker exec $CONTAINER_NAME mc"
        log_info "Using mc from Docker container"
    else
        log_error "mc client not found and container $CONTAINER_NAME is not running!"
        exit 1
    fi
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

log_info "Starting MinIO backup..."
log_info "Backup directory: $BACKUP_DIR"
log_info "Retention: $RETENTION_DAYS days"

# Configure mc alias (only for local mc, container already has it)
if [ "$MC_CMD" = "mc" ]; then
    log_info "Configuring MinIO alias..."
    mc alias set "$MINIO_ALIAS" "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" --api S3v4 >/dev/null 2>&1
fi

# Backup each bucket
BACKUP_SUCCESS=true
for bucket in "${BUCKETS[@]}"; do
    BUCKET_BACKUP_DIR="${BACKUP_DIR}/${bucket}_${DATE}"
    mkdir -p "$BUCKET_BACKUP_DIR"

    log_info "Backing up bucket: $bucket"

    if [ "$MC_CMD" = "mc" ]; then
        # Local mc - mirror from MinIO server to local directory
        if mc mirror --preserve "${MINIO_ALIAS}/${bucket}" "$BUCKET_BACKUP_DIR" 2>/dev/null; then
            # Verify backup with mc diff
            DIFF_OUTPUT=$(mc diff "${MINIO_ALIAS}/${bucket}" "$BUCKET_BACKUP_DIR" 2>/dev/null || true)
            if [ -z "$DIFF_OUTPUT" ]; then
                SIZE=$(du -sh "$BUCKET_BACKUP_DIR" | cut -f1)
                FILE_COUNT=$(find "$BUCKET_BACKUP_DIR" -type f | wc -l | tr -d ' ')
                log_info "Successfully backed up $bucket ($SIZE, $FILE_COUNT files)"
            else
                log_warn "Backup completed but verification found differences"
                echo "$DIFF_OUTPUT"
            fi
        else
            log_error "Failed to backup bucket: $bucket"
            rm -rf "$BUCKET_BACKUP_DIR"
            BACKUP_SUCCESS=false
        fi
    else
        # Using mc inside container - need to copy data out
        # First mirror inside container, then copy out
        CONTAINER_BACKUP_PATH="/tmp/backup_${bucket}_${DATE}"

        if docker exec "$CONTAINER_NAME" mc mirror --preserve "local/${bucket}" "$CONTAINER_BACKUP_PATH" 2>/dev/null; then
            # Copy from container to host
            docker cp "${CONTAINER_NAME}:${CONTAINER_BACKUP_PATH}/." "$BUCKET_BACKUP_DIR/"
            # Cleanup container temp
            docker exec "$CONTAINER_NAME" rm -rf "$CONTAINER_BACKUP_PATH"

            SIZE=$(du -sh "$BUCKET_BACKUP_DIR" | cut -f1)
            FILE_COUNT=$(find "$BUCKET_BACKUP_DIR" -type f | wc -l | tr -d ' ')
            log_info "Successfully backed up $bucket ($SIZE, $FILE_COUNT files)"
        else
            log_error "Failed to backup bucket: $bucket"
            rm -rf "$BUCKET_BACKUP_DIR"
            BACKUP_SUCCESS=false
        fi
    fi
done

# Cleanup old backups
log_info "Cleaning up backups older than $RETENTION_DAYS days..."
DELETED_COUNT=0
while IFS= read -r -d '' dir; do
    rm -rf "$dir"
    ((DELETED_COUNT++))
done < <(find "$BACKUP_DIR" -maxdepth 1 -type d -name "*_*" -mtime +$RETENTION_DAYS -print0 2>/dev/null)

if [ $DELETED_COUNT -gt 0 ]; then
    log_info "Deleted $DELETED_COUNT old backup(s)"
fi

# Summary
echo ""
log_info "=== Backup Summary ==="
log_info "Date: $(date)"
log_info "Location: $BACKUP_DIR"
ls -la "$BACKUP_DIR" 2>/dev/null | head -20 || true

if [ "$BACKUP_SUCCESS" = true ]; then
    log_info "MinIO backup completed successfully!"
    exit 0
else
    log_error "MinIO backup completed with errors!"
    exit 1
fi
