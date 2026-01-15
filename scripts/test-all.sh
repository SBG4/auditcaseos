#!/bin/bash
# Comprehensive AuditCaseOS Test Script
# Tests all major functionality end-to-end

# Don't exit on first error - we want to run all tests
# set -e

BASE_URL="${BASE_URL:-http://localhost:18000/api/v1}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:13000}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASS++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL++))
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# ============================================
# 1. Health Checks
# ============================================
echo ""
echo "========================================"
echo "1. HEALTH CHECKS"
echo "========================================"

# API Health
if curl -sf "http://localhost:18000/health" > /dev/null; then
    log_pass "API health check"
else
    log_fail "API health check"
fi

# Frontend Health
if curl -sf "$FRONTEND_URL/health" > /dev/null; then
    log_pass "Frontend health check"
else
    log_fail "Frontend health check"
fi

# ============================================
# 2. Authentication
# ============================================
echo ""
echo "========================================"
echo "2. AUTHENTICATION"
echo "========================================"

# Login
TOKEN=$(curl -sf -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin@example.com&password=admin123" | jq -r '.access_token')

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    log_pass "Login and get JWT token"
else
    log_fail "Login and get JWT token"
    echo "Cannot continue without authentication"
    exit 1
fi

# Get current user
if curl -sf "$BASE_URL/auth/me" -H "Authorization: Bearer $TOKEN" | jq -e '.email' > /dev/null; then
    log_pass "Get current user profile"
else
    log_fail "Get current user profile"
fi

# ============================================
# 3. Cases API
# ============================================
echo ""
echo "========================================"
echo "3. CASES API"
echo "========================================"

# List cases
CASES=$(curl -sf "$BASE_URL/cases" -H "Authorization: Bearer $TOKEN")
CASE_COUNT=$(echo "$CASES" | jq '.total')
if [ "$CASE_COUNT" -ge 0 ]; then
    log_pass "List cases (found $CASE_COUNT)"
else
    log_fail "List cases"
fi

# Create a test case
NEW_CASE=$(curl -sf -X POST "$BASE_URL/cases" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "title": "Test Script Case",
        "summary": "Created by automated test script",
        "scope_code": "IT",
        "case_type": "POLICY",
        "severity": "LOW"
    }')

TEST_CASE_ID=$(echo "$NEW_CASE" | jq -r '.case_id')
TEST_CASE_UUID=$(echo "$NEW_CASE" | jq -r '.id')
if [ "$TEST_CASE_ID" != "null" ] && [ -n "$TEST_CASE_ID" ]; then
    log_pass "Create case ($TEST_CASE_ID)"
else
    log_fail "Create case"
fi

# Get case by UUID
if curl -sf "$BASE_URL/cases/$TEST_CASE_UUID" -H "Authorization: Bearer $TOKEN" | jq -e '.case_id' > /dev/null; then
    log_pass "Get case by UUID"
else
    log_fail "Get case by UUID"
fi

# ============================================
# 4. Evidence API
# ============================================
echo ""
echo "========================================"
echo "4. EVIDENCE API"
echo "========================================"

# Create test file
echo "Test evidence content for automated testing" > /tmp/test_evidence_script.txt

# Upload evidence
EVIDENCE=$(curl -sf -X POST "$BASE_URL/evidence/cases/$TEST_CASE_ID/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@/tmp/test_evidence_script.txt" \
    -F "description=Automated test evidence")

EVIDENCE_ID=$(echo "$EVIDENCE" | jq -r '.id')
if [ "$EVIDENCE_ID" != "null" ] && [ -n "$EVIDENCE_ID" ]; then
    log_pass "Upload evidence"
else
    log_fail "Upload evidence"
fi

# List case evidence
EVIDENCE_LIST=$(curl -sf "$BASE_URL/evidence/cases/$TEST_CASE_ID" -H "Authorization: Bearer $TOKEN")
EVIDENCE_COUNT=$(echo "$EVIDENCE_LIST" | jq '.total')
if [ "$EVIDENCE_COUNT" -ge 1 ]; then
    log_pass "List case evidence (found $EVIDENCE_COUNT)"
else
    log_fail "List case evidence"
fi

# ============================================
# 5. Nextcloud Integration
# ============================================
echo ""
echo "========================================"
echo "5. NEXTCLOUD INTEGRATION"
echo "========================================"

# Nextcloud health
NC_HEALTH=$(curl -sf "$BASE_URL/nextcloud/health" -H "Authorization: Bearer $TOKEN")
NC_AVAILABLE=$(echo "$NC_HEALTH" | jq -r '.available')
if [ "$NC_AVAILABLE" = "true" ]; then
    log_pass "Nextcloud health check"
else
    log_fail "Nextcloud health check (available: $NC_AVAILABLE)"
fi

# Get case folder URL
NC_URL=$(curl -sf "$BASE_URL/nextcloud/case/$TEST_CASE_ID/url" -H "Authorization: Bearer $TOKEN")
FOLDER_URL=$(echo "$NC_URL" | jq -r '.url')
if [[ "$FOLDER_URL" == *"$TEST_CASE_ID"* ]]; then
    log_pass "Get case folder URL (contains case_id)"
else
    log_fail "Get case folder URL (got: $FOLDER_URL)"
fi

# ============================================
# 6. AI Features
# ============================================
echo ""
echo "========================================"
echo "6. AI FEATURES"
echo "========================================"

# AI health
AI_HEALTH=$(curl -sf "$BASE_URL/ai/health" -H "Authorization: Bearer $TOKEN")
OLLAMA_AVAILABLE=$(echo "$AI_HEALTH" | jq -r '.ollama_available')
if [ "$OLLAMA_AVAILABLE" = "true" ]; then
    log_pass "Ollama available"
else
    log_info "Ollama not available (might need model pull)"
fi

# ============================================
# 7. Reports API
# ============================================
echo ""
echo "========================================"
echo "7. REPORTS API"
echo "========================================"

# Report health
if curl -sf "$BASE_URL/reports/health" -H "Authorization: Bearer $TOKEN" | jq -e '.status' > /dev/null; then
    log_pass "Reports health check"
else
    log_fail "Reports health check"
fi

# List templates
TEMPLATES=$(curl -sf "$BASE_URL/reports/templates" -H "Authorization: Bearer $TOKEN")
TEMPLATE_COUNT=$(echo "$TEMPLATES" | jq '.templates | length')
if [ "$TEMPLATE_COUNT" -ge 1 ]; then
    log_pass "List report templates (found $TEMPLATE_COUNT)"
else
    log_fail "List report templates"
fi

# ============================================
# 8. Frontend Proxy
# ============================================
echo ""
echo "========================================"
echo "8. FRONTEND PROXY"
echo "========================================"

# Test frontend proxy to API
PROXY_CASES=$(curl -sf "$FRONTEND_URL/api/v1/cases" -H "Authorization: Bearer $TOKEN")
PROXY_COUNT=$(echo "$PROXY_CASES" | jq '.total')
if [ "$PROXY_COUNT" -ge 0 ]; then
    log_pass "Frontend proxy to API"
else
    log_fail "Frontend proxy to API"
fi

# Test evidence list through proxy
PROXY_EVIDENCE=$(curl -sf "$FRONTEND_URL/api/v1/evidence/cases/$TEST_CASE_ID" -H "Authorization: Bearer $TOKEN")
PROXY_EV_COUNT=$(echo "$PROXY_EVIDENCE" | jq '.total')
if [ "$PROXY_EV_COUNT" -ge 0 ]; then
    log_pass "Evidence API through proxy"
else
    log_fail "Evidence API through proxy"
fi

# Test Nextcloud URL through proxy
PROXY_NC=$(curl -sf "$FRONTEND_URL/api/v1/nextcloud/case/$TEST_CASE_ID/url" -H "Authorization: Bearer $TOKEN")
PROXY_NC_URL=$(echo "$PROXY_NC" | jq -r '.url')
if [[ "$PROXY_NC_URL" == *"$TEST_CASE_ID"* ]]; then
    log_pass "Nextcloud URL through proxy (contains case_id)"
else
    log_fail "Nextcloud URL through proxy"
fi

# ============================================
# 9. Cleanup
# ============================================
echo ""
echo "========================================"
echo "9. CLEANUP"
echo "========================================"

# Archive test case
if curl -sf -X DELETE "$BASE_URL/cases/$TEST_CASE_UUID" -H "Authorization: Bearer $TOKEN" | jq -e '.message' > /dev/null; then
    log_pass "Archive test case"
else
    log_fail "Archive test case"
fi

rm -f /tmp/test_evidence_script.txt
log_pass "Clean up temp files"

# ============================================
# Summary
# ============================================
echo ""
echo "========================================"
echo "TEST SUMMARY"
echo "========================================"
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
TOTAL=$((PASS + FAIL))
echo "Total:  $TOTAL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please investigate.${NC}"
    exit 1
fi
