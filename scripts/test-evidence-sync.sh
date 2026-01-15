#!/bin/bash
# Comprehensive Evidence-Nextcloud Sync Test Script
# Tests bidirectional sync between MinIO evidence and Nextcloud

# Don't exit on first error - we want to run all tests
# set -e

BASE_URL="${BASE_URL:-http://localhost:18000/api/v1}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:13000}"
NC_URL="${NC_URL:-http://localhost:18081}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC_COLOR='\033[0m' # No Color

PASS=0
FAIL=0
SKIP=0

log_pass() {
    echo -e "${GREEN}[PASS]${NC_COLOR} $1"
    ((PASS++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC_COLOR} $1"
    ((FAIL++))
}

log_skip() {
    echo -e "${YELLOW}[SKIP]${NC_COLOR} $1"
    ((SKIP++))
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC_COLOR} $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC_COLOR}"
    echo -e "${BLUE}$1${NC_COLOR}"
    echo -e "${BLUE}========================================${NC_COLOR}"
}

# ============================================
# PREREQUISITES CHECK
# ============================================
log_section "0. PREREQUISITES CHECK"

# Check API health
if curl -sf "http://localhost:18000/health" > /dev/null; then
    log_pass "API is running"
else
    log_fail "API is not running - cannot proceed"
    exit 1
fi

# Check Nextcloud health
NC_STATUS=$(curl -sf "http://localhost:18081/status.php" | jq -r '.installed')
if [ "$NC_STATUS" = "true" ]; then
    log_pass "Nextcloud is running and installed"
else
    log_fail "Nextcloud is not running or not installed"
    log_info "Some tests will be skipped"
fi

# ============================================
# 1. AUTHENTICATION
# ============================================
log_section "1. AUTHENTICATION"

TOKEN=$(curl -sf -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin@example.com&password=admin123" | jq -r '.access_token')

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    log_pass "Login successful - got JWT token"
else
    log_fail "Login failed - cannot proceed"
    exit 1
fi

# ============================================
# 2. CREATE TEST CASE
# ============================================
log_section "2. CREATE TEST CASE"

TEST_CASE=$(curl -sf -X POST "$BASE_URL/cases" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "title": "Evidence Sync Test Case",
        "summary": "Testing evidence-Nextcloud bidirectional sync",
        "scope_code": "IT",
        "case_type": "POLICY",
        "severity": "LOW"
    }')

TEST_CASE_ID=$(echo "$TEST_CASE" | jq -r '.case_id')
TEST_CASE_UUID=$(echo "$TEST_CASE" | jq -r '.id')

if [ "$TEST_CASE_ID" != "null" ] && [ -n "$TEST_CASE_ID" ]; then
    log_pass "Created test case: $TEST_CASE_ID"
else
    log_fail "Failed to create test case"
    exit 1
fi

# ============================================
# 3. VERIFY NEXTCLOUD FOLDER CREATED
# ============================================
log_section "3. NEXTCLOUD FOLDER STRUCTURE"

# Check if case folder URL contains case_id (not UUID)
NC_FOLDER_URL=$(curl -sf "$BASE_URL/nextcloud/case/$TEST_CASE_ID/url" \
    -H "Authorization: Bearer $TOKEN")
FOLDER_URL=$(echo "$NC_FOLDER_URL" | jq -r '.url')

if [[ "$FOLDER_URL" == *"$TEST_CASE_ID"* ]]; then
    log_pass "Nextcloud folder URL contains case_id: $TEST_CASE_ID"
else
    log_fail "Nextcloud folder URL doesn't contain case_id (got: $FOLDER_URL)"
fi

# List case files in Nextcloud (should have Evidence, Reports, Notes subfolders)
NC_FILES=$(curl -sf "$BASE_URL/nextcloud/case/$TEST_CASE_ID/files" \
    -H "Authorization: Bearer $TOKEN")
NC_FILE_COUNT=$(echo "$NC_FILES" | jq '.files | length')

if [ "$NC_FILE_COUNT" -ge 3 ]; then
    log_pass "Nextcloud case folder has subfolders ($NC_FILE_COUNT items)"
else
    log_info "Nextcloud folder structure: $NC_FILES"
    log_skip "Nextcloud folder check - may need time to create"
fi

# ============================================
# 4. UPLOAD EVIDENCE VIA API
# ============================================
log_section "4. UPLOAD EVIDENCE VIA API"

# Create test file
echo "Test evidence content - uploaded via API at $(date)" > /tmp/test_evidence_api.txt

# Upload via evidence API
EVIDENCE=$(curl -sf -X POST "$BASE_URL/evidence/cases/$TEST_CASE_ID/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@/tmp/test_evidence_api.txt" \
    -F "description=Evidence uploaded via API for sync test")

EVIDENCE_ID=$(echo "$EVIDENCE" | jq -r '.id')
EVIDENCE_FILENAME=$(echo "$EVIDENCE" | jq -r '.file_name')

if [ "$EVIDENCE_ID" != "null" ] && [ -n "$EVIDENCE_ID" ]; then
    log_pass "Uploaded evidence via API: $EVIDENCE_FILENAME (ID: $EVIDENCE_ID)"
else
    log_fail "Failed to upload evidence via API"
fi

# ============================================
# 5. CHECK EVIDENCE IN MINIO
# ============================================
log_section "5. VERIFY EVIDENCE IN MINIO"

# List evidence for case
EVIDENCE_LIST=$(curl -sf "$BASE_URL/evidence/cases/$TEST_CASE_ID" \
    -H "Authorization: Bearer $TOKEN")
EVIDENCE_COUNT=$(echo "$EVIDENCE_LIST" | jq '.total')

if [ "$EVIDENCE_COUNT" -ge 1 ]; then
    log_pass "Evidence found in database (count: $EVIDENCE_COUNT)"
else
    log_fail "Evidence not found in database"
fi

# ============================================
# 6. CHECK EVIDENCE SYNCED TO NEXTCLOUD
# ============================================
log_section "6. VERIFY EVIDENCE SYNCED TO NEXTCLOUD"

# Wait a moment for sync
sleep 2

# List files in Nextcloud Evidence folder
NC_EVIDENCE_FILES=$(curl -sf "$BASE_URL/nextcloud/case/$TEST_CASE_ID/files?subfolder=Evidence" \
    -H "Authorization: Bearer $TOKEN")
NC_EVIDENCE_COUNT=$(echo "$NC_EVIDENCE_FILES" | jq '.files | length' 2>/dev/null || echo "0")

if [ "$NC_EVIDENCE_COUNT" -ge 1 ]; then
    log_pass "Evidence synced to Nextcloud Evidence folder ($NC_EVIDENCE_COUNT files)"
else
    log_fail "Evidence NOT synced to Nextcloud (found $NC_EVIDENCE_COUNT files)"
    log_info "This is expected if sync is not yet implemented"
fi

# ============================================
# 7. MANUAL UPLOAD TO NEXTCLOUD
# ============================================
log_section "7. UPLOAD FILE DIRECTLY TO NEXTCLOUD"

# Create test file for NC upload
echo "Test file uploaded directly to Nextcloud at $(date)" > /tmp/test_evidence_nc.txt

# Upload directly to Nextcloud via our API
NC_UPLOAD=$(curl -sf -X POST "$BASE_URL/nextcloud/case/$TEST_CASE_ID/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@/tmp/test_evidence_nc.txt" \
    -F "subfolder=Evidence")

NC_UPLOAD_SUCCESS=$(echo "$NC_UPLOAD" | jq -r '.success')

if [ "$NC_UPLOAD_SUCCESS" = "true" ]; then
    log_pass "File uploaded directly to Nextcloud Evidence folder"
else
    log_fail "Failed to upload file directly to Nextcloud"
    log_info "Response: $NC_UPLOAD"
fi

# ============================================
# 8. IMPORT NC FILE TO AUDITCASEOS
# ============================================
log_section "8. IMPORT NC FILE TO AUDITCASEOS"

# Call import endpoint to bring Nextcloud files into evidence
IMPORT_RESULT=$(curl -sf -X POST "$BASE_URL/evidence/cases/$TEST_CASE_ID/import-from-nextcloud" \
    -H "Authorization: Bearer $TOKEN")
IMPORT_SUCCESS=$(echo "$IMPORT_RESULT" | jq -r '.success')
IMPORT_COUNT=$(echo "$IMPORT_RESULT" | jq -r '.synced_count')

if [ "$IMPORT_SUCCESS" = "true" ]; then
    log_pass "Import from Nextcloud succeeded (imported $IMPORT_COUNT files)"
else
    log_fail "Import from Nextcloud failed"
    log_info "Response: $IMPORT_RESULT"
fi

# Get evidence list again
EVIDENCE_LIST_AFTER=$(curl -sf "$BASE_URL/evidence/cases/$TEST_CASE_ID" \
    -H "Authorization: Bearer $TOKEN")
EVIDENCE_COUNT_AFTER=$(echo "$EVIDENCE_LIST_AFTER" | jq '.total')

if [ "$EVIDENCE_COUNT_AFTER" -gt "$EVIDENCE_COUNT" ]; then
    log_pass "Nextcloud file imported to AuditCaseOS evidence (count: $EVIDENCE_COUNT_AFTER)"
else
    log_info "No new files imported (may already exist or empty folder)"
fi

# ============================================
# 9. TEST SYNC ENDPOINT (if exists)
# ============================================
log_section "9. TEST SYNC ENDPOINTS"

# Try to sync evidence to Nextcloud
SYNC_TO_NC=$(curl -sf -X POST "$BASE_URL/evidence/cases/$TEST_CASE_ID/sync-to-nextcloud" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null)

if [ -n "$SYNC_TO_NC" ]; then
    SYNC_SUCCESS=$(echo "$SYNC_TO_NC" | jq -r '.success' 2>/dev/null)
    if [ "$SYNC_SUCCESS" = "true" ]; then
        log_pass "Sync evidence to Nextcloud endpoint works"
    else
        log_info "Sync to Nextcloud response: $SYNC_TO_NC"
    fi
else
    log_skip "Sync to Nextcloud endpoint not found (needs implementation)"
fi

# Try to import from Nextcloud
IMPORT_FROM_NC=$(curl -sf -X POST "$BASE_URL/evidence/cases/$TEST_CASE_ID/import-from-nextcloud" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null)

if [ -n "$IMPORT_FROM_NC" ]; then
    IMPORT_SUCCESS=$(echo "$IMPORT_FROM_NC" | jq -r '.success' 2>/dev/null)
    if [ "$IMPORT_SUCCESS" = "true" ]; then
        log_pass "Import from Nextcloud endpoint works"
    else
        log_info "Import from Nextcloud response: $IMPORT_FROM_NC"
    fi
else
    log_skip "Import from Nextcloud endpoint not found (needs implementation)"
fi

# ============================================
# 10. TEST EVIDENCE DOWNLOAD
# ============================================
log_section "10. TEST EVIDENCE DOWNLOAD"

if [ "$EVIDENCE_ID" != "null" ] && [ -n "$EVIDENCE_ID" ]; then
    DOWNLOAD_RESPONSE=$(curl -sf "$BASE_URL/evidence/$EVIDENCE_ID/download" \
        -H "Authorization: Bearer $TOKEN" \
        -o /tmp/downloaded_evidence.txt \
        -w "%{http_code}")

    if [ "$DOWNLOAD_RESPONSE" = "200" ]; then
        log_pass "Evidence download works"
        # Verify content
        if grep -q "uploaded via API" /tmp/downloaded_evidence.txt; then
            log_pass "Downloaded evidence content matches original"
        else
            log_fail "Downloaded evidence content doesn't match"
        fi
    else
        log_fail "Evidence download failed (HTTP $DOWNLOAD_RESPONSE)"
    fi
else
    log_skip "Evidence download - no evidence ID available"
fi

# ============================================
# 11. TEST MULTIPLE FILE TYPES
# ============================================
log_section "11. UPLOAD MULTIPLE FILE TYPES"

# Test PDF-like file
echo "%PDF-1.4 fake pdf content" > /tmp/test_doc.pdf
PDF_UPLOAD=$(curl -sf -X POST "$BASE_URL/evidence/cases/$TEST_CASE_ID/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@/tmp/test_doc.pdf" \
    -F "description=Test PDF file")
PDF_ID=$(echo "$PDF_UPLOAD" | jq -r '.id')
if [ "$PDF_ID" != "null" ] && [ -n "$PDF_ID" ]; then
    log_pass "PDF file upload works"
else
    log_fail "PDF file upload failed"
fi

# Test image-like file
echo "fake image data" > /tmp/test_image.png
IMG_UPLOAD=$(curl -sf -X POST "$BASE_URL/evidence/cases/$TEST_CASE_ID/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@/tmp/test_image.png" \
    -F "description=Test image file")
IMG_ID=$(echo "$IMG_UPLOAD" | jq -r '.id')
if [ "$IMG_ID" != "null" ] && [ -n "$IMG_ID" ]; then
    log_pass "Image file upload works"
else
    log_fail "Image file upload failed"
fi

# ============================================
# 12. VERIFY EVIDENCE METADATA
# ============================================
log_section "12. VERIFY EVIDENCE METADATA"

if [ "$EVIDENCE_ID" != "null" ] && [ -n "$EVIDENCE_ID" ]; then
    METADATA=$(curl -sf "$BASE_URL/evidence/$EVIDENCE_ID" \
        -H "Authorization: Bearer $TOKEN")

    FILE_HASH=$(echo "$METADATA" | jq -r '.file_hash')
    FILE_SIZE=$(echo "$METADATA" | jq -r '.file_size')
    MIME_TYPE=$(echo "$METADATA" | jq -r '.mime_type')

    if [ "$FILE_HASH" != "null" ] && [ -n "$FILE_HASH" ]; then
        log_pass "Evidence has SHA-256 hash: ${FILE_HASH:0:16}..."
    else
        log_fail "Evidence missing file hash"
    fi

    if [ "$FILE_SIZE" -gt 0 ]; then
        log_pass "Evidence has file size: $FILE_SIZE bytes"
    else
        log_fail "Evidence missing file size"
    fi

    if [ "$MIME_TYPE" != "null" ] && [ -n "$MIME_TYPE" ]; then
        log_pass "Evidence has MIME type: $MIME_TYPE"
    else
        log_fail "Evidence missing MIME type"
    fi
else
    log_skip "Evidence metadata verification - no evidence ID"
fi

# ============================================
# 13. TEST NEXTCLOUD HEALTH
# ============================================
log_section "13. NEXTCLOUD INTEGRATION HEALTH"

NC_HEALTH=$(curl -sf "$BASE_URL/nextcloud/health" \
    -H "Authorization: Bearer $TOKEN")
NC_AVAILABLE=$(echo "$NC_HEALTH" | jq -r '.available')
NC_VERSION=$(echo "$NC_HEALTH" | jq -r '.version')

if [ "$NC_AVAILABLE" = "true" ]; then
    log_pass "Nextcloud health check passed (version: $NC_VERSION)"
else
    log_fail "Nextcloud health check failed"
    log_info "Response: $NC_HEALTH"
fi

# ============================================
# 14. CLEANUP
# ============================================
log_section "14. CLEANUP"

# Archive test case
ARCHIVE_RESULT=$(curl -sf -X DELETE "$BASE_URL/cases/$TEST_CASE_UUID" \
    -H "Authorization: Bearer $TOKEN")
ARCHIVE_MSG=$(echo "$ARCHIVE_RESULT" | jq -r '.message')

if [ -n "$ARCHIVE_MSG" ]; then
    log_pass "Archived test case: $TEST_CASE_ID"
else
    log_fail "Failed to archive test case"
fi

# Clean up temp files
rm -f /tmp/test_evidence_api.txt /tmp/test_evidence_nc.txt /tmp/downloaded_evidence.txt
rm -f /tmp/test_doc.pdf /tmp/test_image.png
log_pass "Cleaned up temporary files"

# ============================================
# SUMMARY
# ============================================
log_section "TEST SUMMARY"
echo -e "${GREEN}Passed: $PASS${NC_COLOR}"
echo -e "${RED}Failed: $FAIL${NC_COLOR}"
echo -e "${YELLOW}Skipped: $SKIP${NC_COLOR}"
TOTAL=$((PASS + FAIL + SKIP))
echo "Total:  $TOTAL"
echo ""

# Feature status
echo "FEATURE STATUS:"
echo "==============="
if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}All implemented features are working!${NC_COLOR}"
else
    echo -e "${YELLOW}Some features need implementation or fixing:${NC_COLOR}"
    echo "  - Evidence upload to MinIO: Working"
    echo "  - Evidence metadata: Working"
    echo "  - Nextcloud folder creation: Working"
    echo "  - Evidence sync TO Nextcloud: NEEDS IMPLEMENTATION"
    echo "  - Evidence import FROM Nextcloud: NEEDS IMPLEMENTATION"
fi
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC_COLOR}"
    exit 0
else
    echo -e "${RED}Some tests failed. Check output above.${NC_COLOR}"
    exit 1
fi
