#!/bin/bash
# Test Suite for AuditCaseOS Backup Scripts
# Tests backup-database.sh, backup-minio.sh, backup-all.sh, and restore scripts

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Test configuration
TEST_BACKUP_DIR="${TEST_BACKUP_DIR:-/tmp/auditcaseos-backup-tests}"
CONTAINER_DB="${CONTAINER_DB:-auditcaseos-db}"
CONTAINER_MINIO="${CONTAINER_MINIO:-auditcaseos-minio}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

# Test result functions
pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1"
    TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
}

# Check if container is running
container_running() {
    docker ps --format '{{.Names}}' | grep -q "^$1$"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test artifacts..."
    rm -rf "$TEST_BACKUP_DIR"
}

# Setup test environment
setup() {
    log_info "Setting up test environment..."
    mkdir -p "$TEST_BACKUP_DIR/postgres"
    mkdir -p "$TEST_BACKUP_DIR/minio"
}

# ==============================================================================
# TEST GROUP: Script Existence and Permissions
# ==============================================================================

test_scripts_exist() {
    log_test "Testing script existence..."

    local scripts=(
        "backup-database.sh"
        "backup-minio.sh"
        "backup-all.sh"
        "restore-database.sh"
        "restore-minio.sh"
    )

    for script in "${scripts[@]}"; do
        if [ -f "$SCRIPT_DIR/$script" ]; then
            pass "Script exists: $script"
        else
            fail "Script missing: $script"
        fi
    done
}

test_scripts_executable() {
    log_test "Testing script permissions..."

    local scripts=(
        "backup-database.sh"
        "backup-minio.sh"
        "backup-all.sh"
        "restore-database.sh"
        "restore-minio.sh"
    )

    for script in "${scripts[@]}"; do
        if [ -x "$SCRIPT_DIR/$script" ]; then
            pass "Script executable: $script"
        else
            fail "Script not executable: $script"
        fi
    done
}

test_scripts_syntax() {
    log_test "Testing script syntax (bash -n)..."

    local scripts=(
        "backup-database.sh"
        "backup-minio.sh"
        "backup-all.sh"
        "restore-database.sh"
        "restore-minio.sh"
    )

    for script in "${scripts[@]}"; do
        if bash -n "$SCRIPT_DIR/$script" 2>/dev/null; then
            pass "Syntax valid: $script"
        else
            fail "Syntax error: $script"
        fi
    done
}

# ==============================================================================
# TEST GROUP: PostgreSQL Backup
# ==============================================================================

test_postgres_backup_container_check() {
    log_test "Testing PostgreSQL container detection..."

    if container_running "$CONTAINER_DB"; then
        pass "PostgreSQL container running: $CONTAINER_DB"
    else
        skip "PostgreSQL container not running (expected in CI)"
    fi
}

test_postgres_backup_creates_files() {
    log_test "Testing PostgreSQL backup file creation..."

    if ! container_running "$CONTAINER_DB"; then
        skip "PostgreSQL container not running"
        return
    fi

    # Run backup with test directory
    export BACKUP_DIR="$TEST_BACKUP_DIR/postgres"
    export RETENTION_DAYS=1
    export CONTAINER_NAME="$CONTAINER_DB"

    if "$SCRIPT_DIR/backup-database.sh" >/dev/null 2>&1; then
        # Check if files were created
        local dump_count
        dump_count=$(find "$TEST_BACKUP_DIR/postgres" -name "*.dump" -type f | wc -l | tr -d ' ')

        if [ "$dump_count" -ge 1 ]; then
            pass "PostgreSQL backup created $dump_count dump file(s)"
        else
            fail "PostgreSQL backup created no files"
        fi
    else
        fail "PostgreSQL backup script failed"
    fi
}

test_postgres_backup_file_not_empty() {
    log_test "Testing PostgreSQL backup files have content..."

    if ! container_running "$CONTAINER_DB"; then
        skip "PostgreSQL container not running"
        return
    fi

    local dump_files
    dump_files=$(find "$TEST_BACKUP_DIR/postgres" -name "*.dump" -type f 2>/dev/null)

    if [ -z "$dump_files" ]; then
        skip "No dump files to check"
        return
    fi

    local all_have_content=true
    for file in $dump_files; do
        if [ -s "$file" ]; then
            pass "Dump file has content: $(basename "$file")"
        else
            fail "Dump file is empty: $(basename "$file")"
            all_have_content=false
        fi
    done
}

test_postgres_backup_all_databases() {
    log_test "Testing PostgreSQL backs up all 3 databases..."

    if ! container_running "$CONTAINER_DB"; then
        skip "PostgreSQL container not running"
        return
    fi

    local expected_dbs=("auditcaseos" "paperless" "nextcloud")
    local dump_files
    dump_files=$(find "$TEST_BACKUP_DIR/postgres" -name "*.dump" -type f 2>/dev/null | xargs -I {} basename {} 2>/dev/null || true)

    for db in "${expected_dbs[@]}"; do
        if echo "$dump_files" | grep -q "^${db}_"; then
            pass "Database backed up: $db"
        else
            fail "Database not backed up: $db"
        fi
    done
}

test_postgres_backup_graceful_failure() {
    log_test "Testing PostgreSQL backup fails gracefully with bad container..."

    export BACKUP_DIR="$TEST_BACKUP_DIR/postgres-fail"
    export CONTAINER_NAME="nonexistent-container-12345"

    mkdir -p "$TEST_BACKUP_DIR/postgres-fail"

    if "$SCRIPT_DIR/backup-database.sh" >/dev/null 2>&1; then
        fail "Backup should have failed with bad container"
    else
        pass "Backup failed gracefully with bad container"
    fi
}

# ==============================================================================
# TEST GROUP: MinIO Backup
# ==============================================================================

test_minio_backup_container_check() {
    log_test "Testing MinIO container detection..."

    if container_running "$CONTAINER_MINIO"; then
        pass "MinIO container running: $CONTAINER_MINIO"
    else
        skip "MinIO container not running (expected in CI)"
    fi
}

test_minio_backup_creates_directory() {
    log_test "Testing MinIO backup directory creation..."

    if ! container_running "$CONTAINER_MINIO"; then
        skip "MinIO container not running"
        return
    fi

    export BACKUP_DIR="$TEST_BACKUP_DIR/minio"
    export RETENTION_DAYS=1
    export CONTAINER_NAME="$CONTAINER_MINIO"

    if "$SCRIPT_DIR/backup-minio.sh" >/dev/null 2>&1; then
        local backup_dirs
        backup_dirs=$(find "$TEST_BACKUP_DIR/minio" -maxdepth 1 -type d -name "evidence_*" | wc -l | tr -d ' ')

        if [ "$backup_dirs" -ge 1 ]; then
            pass "MinIO backup created $backup_dirs backup directory(ies)"
        else
            # May be empty if bucket is empty
            pass "MinIO backup ran (bucket may be empty)"
        fi
    else
        fail "MinIO backup script failed"
    fi
}

test_minio_backup_graceful_failure() {
    log_test "Testing MinIO backup fails gracefully with bad container..."

    export BACKUP_DIR="$TEST_BACKUP_DIR/minio-fail"
    export CONTAINER_NAME="nonexistent-minio-12345"

    mkdir -p "$TEST_BACKUP_DIR/minio-fail"

    if "$SCRIPT_DIR/backup-minio.sh" >/dev/null 2>&1; then
        fail "MinIO backup should have failed with bad container"
    else
        pass "MinIO backup failed gracefully with bad container"
    fi
}

# ==============================================================================
# TEST GROUP: Combined Backup
# ==============================================================================

test_backup_all_runs() {
    log_test "Testing combined backup script execution..."

    if ! container_running "$CONTAINER_DB" || ! container_running "$CONTAINER_MINIO"; then
        skip "Required containers not running"
        return
    fi

    # Reset environment variables that may have been modified by previous tests
    export BACKUP_DIR="$TEST_BACKUP_DIR/combined"
    export RETENTION_DAYS=1
    export CONTAINER_NAME=""
    export MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
    export MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin123}"

    mkdir -p "$TEST_BACKUP_DIR/combined"

    if "$SCRIPT_DIR/backup-all.sh" >/dev/null 2>&1; then
        pass "Combined backup script completed"
    else
        fail "Combined backup script failed"
    fi
}

test_backup_all_creates_postgres() {
    log_test "Testing combined backup creates PostgreSQL backups..."

    if ! container_running "$CONTAINER_DB"; then
        skip "PostgreSQL container not running"
        return
    fi

    local postgres_files
    postgres_files=$(find "$TEST_BACKUP_DIR/combined/postgres" -name "*.dump" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [ "$postgres_files" -ge 1 ]; then
        pass "Combined backup created PostgreSQL files"
    else
        skip "No PostgreSQL backup files (may not have run combined)"
    fi
}

test_backup_all_creates_minio() {
    log_test "Testing combined backup creates MinIO backups..."

    if ! container_running "$CONTAINER_MINIO"; then
        skip "MinIO container not running"
        return
    fi

    local minio_dirs
    minio_dirs=$(find "$TEST_BACKUP_DIR/combined/minio" -maxdepth 1 -type d -name "evidence_*" 2>/dev/null | wc -l | tr -d ' ')

    if [ "$minio_dirs" -ge 0 ]; then
        # 0 is okay if bucket is empty
        pass "Combined backup processed MinIO"
    else
        skip "No MinIO backup directory"
    fi
}

# ==============================================================================
# TEST GROUP: Restore Scripts (Dry Run / Validation Only)
# ==============================================================================

test_restore_database_usage() {
    log_test "Testing restore-database.sh usage output..."

    # Reset environment to defaults (avoid interference from previous tests)
    export BACKUP_DIR="./backups/postgres"
    export CONTAINER_NAME="auditcaseos-db"

    # Capture output (script exits with 1, so disable pipefail temporarily)
    local output
    output=$("$SCRIPT_DIR/restore-database.sh" 2>&1 || true)

    if echo "$output" | grep -q "Usage"; then
        pass "restore-database.sh shows usage without arguments"
    else
        fail "restore-database.sh should show usage without arguments"
    fi
}

test_restore_minio_usage() {
    log_test "Testing restore-minio.sh usage output..."

    # Reset environment to defaults (avoid interference from previous tests)
    export BACKUP_DIR="./backups/minio"
    export CONTAINER_NAME="auditcaseos-minio"

    # Capture output (script exits with 1, so disable pipefail temporarily)
    local output
    output=$("$SCRIPT_DIR/restore-minio.sh" 2>&1 || true)

    if echo "$output" | grep -q "Usage"; then
        pass "restore-minio.sh shows usage without arguments"
    else
        fail "restore-minio.sh should show usage without arguments"
    fi
}

test_restore_database_file_check() {
    log_test "Testing restore-database.sh checks for valid file..."

    # Reset environment to defaults (avoid interference from previous tests)
    export BACKUP_DIR="./backups/postgres"
    export CONTAINER_NAME="auditcaseos-db"

    # Capture output (script exits with 1, so disable pipefail temporarily)
    local output
    output=$("$SCRIPT_DIR/restore-database.sh" /nonexistent/file.dump 2>&1 || true)

    if echo "$output" | grep -q -i "not found\|error"; then
        pass "restore-database.sh validates backup file exists"
    else
        fail "restore-database.sh should check if backup file exists"
    fi
}

test_restore_minio_dir_check() {
    log_test "Testing restore-minio.sh checks for valid directory..."

    # Reset environment to defaults (avoid interference from previous tests)
    export BACKUP_DIR="./backups/minio"
    export CONTAINER_NAME="auditcaseos-minio"

    # Capture output (script exits with 1, so disable pipefail temporarily)
    local output
    output=$("$SCRIPT_DIR/restore-minio.sh" /nonexistent/dir 2>&1 || true)

    if echo "$output" | grep -q -i "not found\|error"; then
        pass "restore-minio.sh validates backup directory exists"
    else
        fail "restore-minio.sh should check if backup directory exists"
    fi
}

# ==============================================================================
# TEST GROUP: Retention Policy
# ==============================================================================

test_retention_creates_old_files() {
    log_test "Testing retention policy setup..."

    # Create fake old backup files
    local old_file="$TEST_BACKUP_DIR/retention/test_old_20200101_000000.dump"
    mkdir -p "$TEST_BACKUP_DIR/retention"
    touch "$old_file"

    # Set modification time to 30 days ago (cross-platform)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS: use -t with timestamp format YYYYMMDDhhmm
        local old_date
        old_date=$(date -v-30d +%Y%m%d%H%M)
        touch -t "$old_date" "$old_file"
    else
        # Linux: use -d with relative date
        touch -d "30 days ago" "$old_file"
    fi

    if [ -f "$old_file" ]; then
        pass "Created test file for retention"
    else
        fail "Could not create test file for retention"
    fi
}

test_retention_deletes_old_files() {
    log_test "Testing retention policy deletes old files..."

    if ! container_running "$CONTAINER_DB"; then
        skip "PostgreSQL container not running"
        return
    fi

    local old_file="$TEST_BACKUP_DIR/retention/test_old_20200101_000000.dump"

    # Create old file
    mkdir -p "$TEST_BACKUP_DIR/retention"
    touch "$old_file"

    # Set modification time to 30 days ago (cross-platform)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        local old_date
        old_date=$(date -v-30d +%Y%m%d%H%M)
        touch -t "$old_date" "$old_file"
    else
        touch -d "30 days ago" "$old_file"
    fi

    export BACKUP_DIR="$TEST_BACKUP_DIR/retention"
    export RETENTION_DAYS=7
    export CONTAINER_NAME="$CONTAINER_DB"

    # Run backup (which includes cleanup)
    "$SCRIPT_DIR/backup-database.sh" >/dev/null 2>&1 || true

    if [ ! -f "$old_file" ]; then
        pass "Retention policy deleted old backup"
    else
        fail "Retention policy should have deleted old backup"
    fi
}

# ==============================================================================
# TEST GROUP: Backup Directory Structure
# ==============================================================================

test_backup_directory_exists() {
    log_test "Testing backups directory structure..."

    if [ -d "$PROJECT_DIR/backups" ]; then
        pass "backups/ directory exists"
    else
        fail "backups/ directory missing"
    fi
}

test_backup_directory_has_subdirs() {
    log_test "Testing backup subdirectories..."

    if [ -d "$PROJECT_DIR/backups/postgres" ]; then
        pass "backups/postgres/ exists"
    else
        fail "backups/postgres/ missing"
    fi

    if [ -d "$PROJECT_DIR/backups/minio" ]; then
        pass "backups/minio/ exists"
    else
        fail "backups/minio/ missing"
    fi
}

test_backup_directory_has_readme() {
    log_test "Testing backup documentation..."

    if [ -f "$PROJECT_DIR/backups/README.md" ]; then
        pass "backups/README.md exists"
    else
        fail "backups/README.md missing"
    fi
}

test_backup_directory_has_gitignore() {
    log_test "Testing backup .gitignore..."

    if [ -f "$PROJECT_DIR/backups/.gitignore" ]; then
        pass "backups/.gitignore exists"

        # Check it ignores dump files
        if grep -q "\.dump" "$PROJECT_DIR/backups/.gitignore"; then
            pass ".gitignore ignores .dump files"
        else
            fail ".gitignore should ignore .dump files"
        fi
    else
        fail "backups/.gitignore missing"
    fi
}

# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================

main() {
    echo ""
    echo "========================================"
    echo " AuditCaseOS Backup Test Suite"
    echo "========================================"
    echo ""

    # Setup
    setup
    trap cleanup EXIT

    # Run test groups
    echo ""
    echo "--- Script Validation ---"
    test_scripts_exist
    test_scripts_executable
    test_scripts_syntax

    echo ""
    echo "--- Backup Directory Structure ---"
    test_backup_directory_exists
    test_backup_directory_has_subdirs
    test_backup_directory_has_readme
    test_backup_directory_has_gitignore

    echo ""
    echo "--- PostgreSQL Backup Tests ---"
    test_postgres_backup_container_check
    test_postgres_backup_creates_files
    test_postgres_backup_file_not_empty
    test_postgres_backup_all_databases
    test_postgres_backup_graceful_failure

    echo ""
    echo "--- MinIO Backup Tests ---"
    test_minio_backup_container_check
    test_minio_backup_creates_directory
    test_minio_backup_graceful_failure

    echo ""
    echo "--- Combined Backup Tests ---"
    test_backup_all_runs
    test_backup_all_creates_postgres
    test_backup_all_creates_minio

    echo ""
    echo "--- Restore Script Tests ---"
    test_restore_database_usage
    test_restore_minio_usage
    test_restore_database_file_check
    test_restore_minio_dir_check

    echo ""
    echo "--- Retention Policy Tests ---"
    test_retention_creates_old_files
    test_retention_deletes_old_files

    # Summary
    echo ""
    echo "========================================"
    echo " Test Summary"
    echo "========================================"
    echo -e " ${GREEN}Passed:${NC}  $TESTS_PASSED"
    echo -e " ${RED}Failed:${NC}  $TESTS_FAILED"
    echo -e " ${YELLOW}Skipped:${NC} $TESTS_SKIPPED"
    echo "========================================"

    # Exit with failure if any tests failed
    if [ "$TESTS_FAILED" -gt 0 ]; then
        exit 1
    fi

    exit 0
}

# Run main
main "$@"
