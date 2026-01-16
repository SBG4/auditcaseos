#!/bin/bash
#
# K6 Load Test Runner for AuditCaseOS
#
# Usage: ./run-tests.sh [smoke|load|stress] [options]
#
# Options:
#   --debug       Enable debug output
#   --no-docker   Run k6 locally instead of Docker
#   --help        Show this help message
#

set -e

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
NETWORK_NAME="auditcaseos_default"
K6_IMAGE="grafana/k6:latest"

# Timestamp for result files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Default values
DEBUG_MODE=false
USE_DOCKER=true
TEST_TYPE=""

# =============================================================================
# Functions
# =============================================================================

show_help() {
    cat << EOF
K6 Load Test Runner for AuditCaseOS

Usage: $0 [test_type] [options]

Test Types:
  smoke     Quick sanity check (1 VU, 1 min) - Run on every PR
  load      Normal load test (50 VUs, 8 min) - Run nightly
  stress    Stress test (200 VUs, 10 min) - Run weekly

Options:
  --debug       Enable debug output in tests
  --no-docker   Run k6 locally (requires k6 installed)
  --help, -h    Show this help message

Examples:
  $0 smoke                  # Run smoke test
  $0 load --debug           # Run load test with debug output
  $0 stress --no-docker     # Run stress test using local k6

Environment Variables:
  API_BASE_URL      Override API URL (default: http://api:8000/api/v1)
  TEST_USERNAME     Override test username (default: admin@example.com)
  TEST_PASSWORD     Override test password (default: admin123)
  K6_ENV            Environment name (default: docker)

EOF
}

log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
}

log_success() {
    echo "[SUCCESS] $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
}

check_k6() {
    if ! command -v k6 &> /dev/null; then
        log_error "k6 is not installed or not in PATH"
        log_error "Install k6: https://k6.io/docs/getting-started/installation/"
        exit 1
    fi
}

check_network() {
    if ! docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
        log_error "Docker network '${NETWORK_NAME}' not found"
        log_error "Make sure the AuditCaseOS stack is running: docker-compose up -d"
        exit 1
    fi
}

ensure_results_dir() {
    mkdir -p "${RESULTS_DIR}"
}

run_with_docker() {
    local test_file=$1
    local test_name=$2

    log_info "Running ${test_name} test with Docker..."
    log_info "Using network: ${NETWORK_NAME}"

    # Build environment variables
    local env_vars="-e K6_ENV=docker"

    if [ "$DEBUG_MODE" = true ]; then
        env_vars="${env_vars} -e K6_DEBUG=true"
    fi

    if [ -n "${API_BASE_URL}" ]; then
        env_vars="${env_vars} -e API_BASE_URL=${API_BASE_URL}"
    fi

    if [ -n "${TEST_USERNAME}" ]; then
        env_vars="${env_vars} -e TEST_USERNAME=${TEST_USERNAME}"
    fi

    if [ -n "${TEST_PASSWORD}" ]; then
        env_vars="${env_vars} -e TEST_PASSWORD=${TEST_PASSWORD}"
    fi

    # Run k6 in Docker
    docker run --rm \
        --network="${NETWORK_NAME}" \
        -v "${SCRIPT_DIR}:/scripts:ro" \
        -v "${RESULTS_DIR}:/scripts/results" \
        ${env_vars} \
        "${K6_IMAGE}" run \
        --out json="/scripts/results/${test_name}-${TIMESTAMP}.json" \
        "/scripts/scripts/${test_file}"

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_success "${test_name} test completed successfully"
    else
        log_error "${test_name} test failed with exit code: ${exit_code}"
    fi

    return $exit_code
}

run_locally() {
    local test_file=$1
    local test_name=$2

    log_info "Running ${test_name} test locally..."

    # Build environment variables
    local env_cmd=""

    if [ "$DEBUG_MODE" = true ]; then
        env_cmd="K6_DEBUG=true"
    fi

    if [ -n "${API_BASE_URL}" ]; then
        env_cmd="${env_cmd} API_BASE_URL=${API_BASE_URL}"
    else
        # Default to localhost when running locally
        env_cmd="${env_cmd} API_BASE_URL=http://localhost:8000/api/v1"
    fi

    if [ -n "${TEST_USERNAME}" ]; then
        env_cmd="${env_cmd} TEST_USERNAME=${TEST_USERNAME}"
    fi

    if [ -n "${TEST_PASSWORD}" ]; then
        env_cmd="${env_cmd} TEST_PASSWORD=${TEST_PASSWORD}"
    fi

    env_cmd="${env_cmd} K6_ENV=local"

    # Change to script directory for proper imports
    cd "${SCRIPT_DIR}"

    # Run k6 locally
    env ${env_cmd} k6 run \
        --out json="results/${test_name}-${TIMESTAMP}.json" \
        "scripts/${test_file}"

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_success "${test_name} test completed successfully"
    else
        log_error "${test_name} test failed with exit code: ${exit_code}"
    fi

    return $exit_code
}

# =============================================================================
# Main Script
# =============================================================================

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        smoke|load|stress)
            TEST_TYPE="$1"
            shift
            ;;
        --debug)
            DEBUG_MODE=true
            shift
            ;;
        --no-docker)
            USE_DOCKER=false
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate test type
if [ -z "$TEST_TYPE" ]; then
    log_error "Test type is required"
    echo ""
    show_help
    exit 1
fi

# Map test type to file
case $TEST_TYPE in
    smoke)
        TEST_FILE="smoke-test.js"
        ;;
    load)
        TEST_FILE="load-test.js"
        ;;
    stress)
        TEST_FILE="stress-test.js"
        ;;
    *)
        log_error "Invalid test type: $TEST_TYPE"
        exit 1
        ;;
esac

# Print banner
echo ""
echo "=============================================="
echo "  AuditCaseOS K6 Load Testing"
echo "=============================================="
echo "  Test Type: ${TEST_TYPE}"
echo "  Test File: ${TEST_FILE}"
echo "  Mode:      $([ "$USE_DOCKER" = true ] && echo "Docker" || echo "Local")"
echo "  Debug:     ${DEBUG_MODE}"
echo "  Results:   ${RESULTS_DIR}"
echo "=============================================="
echo ""

# Ensure results directory exists
ensure_results_dir

# Run appropriate version
if [ "$USE_DOCKER" = true ]; then
    check_docker
    check_network
    run_with_docker "${TEST_FILE}" "${TEST_TYPE}"
else
    check_k6
    run_locally "${TEST_FILE}" "${TEST_TYPE}"
fi

exit_code=$?

# Print results location
echo ""
echo "=============================================="
echo "  Results saved to:"
echo "  - ${RESULTS_DIR}/${TEST_TYPE}-${TIMESTAMP}.json"
echo "  - ${RESULTS_DIR}/${TEST_TYPE}-test-summary.json"
echo "=============================================="
echo ""

exit $exit_code
