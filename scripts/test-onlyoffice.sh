#!/bin/bash
# Test script for ONLYOFFICE Integration (Feature 3.9)
# Tests the ONLYOFFICE Document Server integration with the AuditCaseOS API

set -e

BASE_URL="${BASE_URL:-http://localhost:18000}"
NEXTCLOUD_URL="${NEXTCLOUD_URL:-http://localhost:18081}"
ONLYOFFICE_URL="${ONLYOFFICE_URL:-http://localhost:18082}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0
TOTAL=0

# Helper function to run a test
run_test() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    TOTAL=$((TOTAL + 1))

    if [[ "$actual" == *"$expected"* ]]; then
        echo -e "${GREEN}✓${NC} $name"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $name"
        echo -e "  Expected: $expected"
        echo -e "  Actual: $actual"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "=========================================="
echo "ONLYOFFICE Integration Tests"
echo "=========================================="
echo ""

# ==========================================
# Test 1: ONLYOFFICE Document Server Health
# ==========================================
echo -e "${YELLOW}1. Testing ONLYOFFICE Document Server Health${NC}"

response=$(curl -s "$ONLYOFFICE_URL/healthcheck" || echo "error")
run_test "ONLYOFFICE healthcheck responds" "true" "$response"

# ==========================================
# Test 2: ONLYOFFICE API Health Endpoint
# ==========================================
echo ""
echo -e "${YELLOW}2. Testing ONLYOFFICE API Health Endpoint${NC}"

response=$(curl -s "$BASE_URL/api/v1/onlyoffice/health" || echo "error")
run_test "API health check shows available" '"available":true' "$response"
run_test "API health check includes external_url" '"external_url"' "$response"

# ==========================================
# Test 3: Supported Extensions Endpoint
# ==========================================
echo ""
echo -e "${YELLOW}3. Testing Supported Extensions${NC}"

response=$(curl -s "$BASE_URL/api/v1/onlyoffice/extensions" || echo "error")
run_test "Extensions includes documents" '".docx"' "$response"
run_test "Extensions includes spreadsheets" '".xlsx"' "$response"
run_test "Extensions includes presentations" '".pptx"' "$response"
run_test "Extensions includes editable list" '"editable"' "$response"

# ==========================================
# Test 4: Editor URL Endpoint
# ==========================================
echo ""
echo -e "${YELLOW}4. Testing Editor URL Endpoint${NC}"

response=$(curl -s "$BASE_URL/api/v1/onlyoffice/editor-url" || echo "error")
run_test "Editor URL returns URL" '"editor_url"' "$response"
run_test "Editor URL is localhost:18082" "localhost:18082" "$response"

# ==========================================
# Test 5: Get Auth Token for Authenticated Tests
# ==========================================
echo ""
echo -e "${YELLOW}5. Getting Auth Token${NC}"

# Login and get token
login_response=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin@example.com&password=admin123" 2>/dev/null || echo "error")

TOKEN=$(echo "$login_response" | jq -r '.access_token // empty')

if [ -n "$TOKEN" ]; then
    run_test "Login successful for tests" "access_token" "$login_response"
else
    echo -e "${RED}✗${NC} Login failed - cannot continue with authenticated tests"
    echo "Response: $login_response"
    FAILED=$((FAILED + 1))
    TOTAL=$((TOTAL + 1))
fi

# ==========================================
# Test 6: Edit URL Generation (requires auth)
# ==========================================
echo ""
echo -e "${YELLOW}6. Testing Edit URL Generation${NC}"

if [ -n "$TOKEN" ]; then
    response=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/onlyoffice/edit-url?file_path=AuditCases/TEST-001/Reports/report.docx" || echo "error")
    run_test "Edit URL returns edit_url" '"edit_url"' "$response"
    run_test "Edit URL marks as editable" '"is_editable":true' "$response"
    run_test "Edit URL marks as viewable" '"is_viewable":true' "$response"
    run_test "Edit URL identifies document type" '"document_type":"word"' "$response"

    # Test non-editable but viewable file (PDF)
    response=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/onlyoffice/edit-url?file_path=AuditCases/TEST-001/Evidence/document.pdf" || echo "error")
    run_test "PDF is viewable" '"is_viewable":true' "$response"
    run_test "PDF is not editable" '"is_editable":false' "$response"

    # Test spreadsheet
    response=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/onlyoffice/edit-url?file_path=AuditCases/TEST-001/Evidence/data.xlsx" || echo "error")
    run_test "Excel file is editable" '"is_editable":true' "$response"
    run_test "Excel file type is cell" '"document_type":"cell"' "$response"

    # Test presentation
    response=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/onlyoffice/edit-url?file_path=AuditCases/TEST-001/Evidence/slides.pptx" || echo "error")
    run_test "PowerPoint is editable" '"is_editable":true' "$response"
    run_test "PowerPoint type is slide" '"document_type":"slide"' "$response"

    # Test unsupported file type
    response=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/onlyoffice/edit-url?file_path=AuditCases/TEST-001/Evidence/image.jpg" 2>&1 || echo "error")
    run_test "Unsupported file returns error" '"detail"' "$response"
else
    echo -e "${YELLOW}⚠${NC} Skipping edit URL tests - no auth token"
fi

# ==========================================
# Test 7: Nextcloud ONLYOFFICE Connector
# ==========================================
echo ""
echo -e "${YELLOW}7. Testing Nextcloud ONLYOFFICE Connector${NC}"

# Check if ONLYOFFICE app is installed in Nextcloud
response=$(docker exec -u www-data auditcaseos-nextcloud php occ app:list --shipped=false 2>/dev/null | grep -c onlyoffice || echo "0")
run_test "ONLYOFFICE app installed in Nextcloud" "1" "$response"

# Check ONLYOFFICE config in Nextcloud
response=$(docker exec -u www-data auditcaseos-nextcloud php occ config:app:get onlyoffice DocumentServerUrl 2>/dev/null || echo "error")
run_test "Nextcloud ONLYOFFICE URL configured" "localhost:18082" "$response"

response=$(docker exec -u www-data auditcaseos-nextcloud php occ config:app:get onlyoffice jwt_secret 2>/dev/null || echo "error")
run_test "Nextcloud ONLYOFFICE JWT secret configured" "auditcaseos-onlyoffice-secret" "$response"

# ==========================================
# Test 8: Case Documents Endpoint (requires case)
# ==========================================
echo ""
echo -e "${YELLOW}8. Testing Case Documents Endpoint${NC}"

if [ -n "$TOKEN" ]; then
    # First, create a test case
    case_response=$(curl -s -X POST "$BASE_URL/api/v1/cases" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"title": "ONLYOFFICE Test Case", "description": "Testing ONLYOFFICE integration", "case_type": "INVESTIGATION", "scope_code": "IT-POLICY", "severity": "LOW"}' 2>/dev/null || echo "error")

    CASE_ID=$(echo "$case_response" | jq -r '.case_id // empty')

    if [ -n "$CASE_ID" ]; then
        run_test "Test case created" "$CASE_ID" "$case_response"

        # Test case documents endpoint
        response=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/onlyoffice/case/$CASE_ID/documents" || echo "error")
        run_test "Case documents endpoint works" '"documents"' "$response"
        run_test "Case documents returns total" '"total"' "$response"
    else
        echo -e "${YELLOW}⚠${NC} Skipping case documents test - could not create test case"
    fi
else
    echo -e "${YELLOW}⚠${NC} Skipping case documents test - no auth token"
fi

# ==========================================
# Summary
# ==========================================
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Total: $TOTAL | ${GREEN}Passed: $PASSED${NC} | ${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
