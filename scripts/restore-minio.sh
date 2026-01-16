#!/bin/bash
# MinIO Restore Script for AuditCaseOS
# Restores from mc mirror backup
# Source: min.io/docs best practices

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups/minio}"
CONTAINER_NAME="${CONTAINER_NAME:-auditcaseos-minio}"
MINIO_ALIAS="${MINIO_ALIAS:-local}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:19000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin123}"

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
    echo "Usage: $0 <backup_directory> [bucket_name]"
    echo ""
    echo "Arguments:"
    echo "  backup_directory  Path to the backup directory (e.g., evidence_20260116_120000)"
    echo "  bucket_name       Optional: Override bucket name (default: extracted from directory name)"
    echo ""
    echo "Examples:"
    echo "  $0 ./backups/minio/evidence_20260116_120000"
    echo "  $0 ./backups/minio/evidence_20260116_120000 my_test_bucket"
    echo ""
    echo "Available backups:"
    ls -dt "$BACKUP_DIR"/*_* 2>/dev/null | head -10 || echo "  No backups found in $BACKUP_DIR"
    exit 1
}

# Check arguments
if [ $# -lt 1 ]; then
    usage
fi

BACKUP_PATH="$1"
BUCKET_NAME="${2:-}"

# Verify backup directory exists
if [ ! -d "$BACKUP_PATH" ]; then
    log_error "Backup directory not found: $BACKUP_PATH"
    exit 1
fi

# Extract bucket name from directory name if not provided
if [ -z "$BUCKET_NAME" ]; then
    DIRNAME=$(basename "$BACKUP_PATH")
    BUCKET_NAME=$(echo "$DIRNAME" | sed 's/_[0-9]\{8\}_[0-9]\{6\}$//')
    log_info "Extracted bucket name: $BUCKET_NAME"
fi

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

# Count files in backup
FILE_COUNT=$(find "$BACKUP_PATH" -type f | wc -l | tr -d ' ')
BACKUP_SIZE=$(du -sh "$BACKUP_PATH" | cut -f1)

# Confirmation prompt
echo ""
log_warn "=== RESTORE CONFIRMATION ==="
log_warn "This will OVERWRITE files in the bucket!"
echo ""
echo "Backup directory: $BACKUP_PATH"
echo "Files to restore: $FILE_COUNT"
echo "Backup size: $BACKUP_SIZE"
echo "Target bucket: $BUCKET_NAME"
echo "Container: $CONTAINER_NAME"
echo ""
read -p "Are you sure you want to proceed? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log_info "Restore cancelled."
    exit 0
fi

log_info "Starting MinIO restore..."

# Configure mc alias (only for local mc)
if [ "$MC_CMD" = "mc" ]; then
    log_info "Configuring MinIO alias..."
    mc alias set "$MINIO_ALIAS" "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" --api S3v4 >/dev/null 2>&1

    # Create bucket if it doesn't exist
    if ! mc ls "${MINIO_ALIAS}/${BUCKET_NAME}" &>/dev/null; then
        log_info "Creating bucket: $BUCKET_NAME"
        mc mb "${MINIO_ALIAS}/${BUCKET_NAME}" 2>/dev/null || true
    fi

    # Restore using mc mirror
    log_info "Restoring files to bucket..."
    if mc mirror --preserve --overwrite "$BACKUP_PATH" "${MINIO_ALIAS}/${BUCKET_NAME}" 2>&1; then
        log_info "Files restored successfully"
    else
        log_error "Failed to restore files"
        exit 1
    fi

    # Verify restore
    log_info "Verifying restore..."
    RESTORED_COUNT=$(mc ls --recursive "${MINIO_ALIAS}/${BUCKET_NAME}" 2>/dev/null | wc -l | tr -d ' ')
else
    # Using mc inside container
    CONTAINER_RESTORE_PATH="/tmp/restore_${BUCKET_NAME}"

    # Copy backup to container
    log_info "Copying backup to container..."
    docker cp "$BACKUP_PATH" "${CONTAINER_NAME}:${CONTAINER_RESTORE_PATH}"

    # Create bucket if it doesn't exist
    docker exec "$CONTAINER_NAME" mc mb "local/${BUCKET_NAME}" 2>/dev/null || true

    # Restore using mc mirror inside container
    log_info "Restoring files to bucket..."
    if docker exec "$CONTAINER_NAME" mc mirror --preserve --overwrite "$CONTAINER_RESTORE_PATH" "local/${BUCKET_NAME}" 2>&1; then
        log_info "Files restored successfully"
    else
        log_error "Failed to restore files"
        docker exec "$CONTAINER_NAME" rm -rf "$CONTAINER_RESTORE_PATH"
        exit 1
    fi

    # Cleanup container temp
    docker exec "$CONTAINER_NAME" rm -rf "$CONTAINER_RESTORE_PATH"

    # Verify restore
    log_info "Verifying restore..."
    RESTORED_COUNT=$(docker exec "$CONTAINER_NAME" mc ls --recursive "local/${BUCKET_NAME}" 2>/dev/null | wc -l | tr -d ' ')
fi

echo ""
log_info "=== Restore Summary ==="
log_info "Bucket: $BUCKET_NAME"
log_info "Files in backup: $FILE_COUNT"
log_info "Files in bucket: $RESTORED_COUNT"
log_info "Backup directory: $BACKUP_PATH"
log_info "MinIO restore completed successfully!"
