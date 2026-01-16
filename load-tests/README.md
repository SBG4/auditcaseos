# K6 Load Testing for AuditCaseOS

This directory contains k6 load testing scripts for performance testing the AuditCaseOS API.

## Directory Structure

```
load-tests/
├── scripts/
│   ├── common.js           # Auth helpers, custom metrics, shared functions
│   ├── smoke-test.js       # Quick sanity check (1 VU, 1 min)
│   ├── load-test.js        # Normal load test (50 VUs, 8 min)
│   └── stress-test.js      # Stress test (200 VUs, 10 min)
├── config.js               # Environment configuration
├── thresholds.js           # SLO (Service Level Objective) definitions
├── run-tests.sh            # Docker-based test runner
├── results/                # Test results output directory
└── README.md               # This file
```

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- AuditCaseOS stack running (`docker-compose up -d`)

### Running Tests

```bash
# Run smoke test (recommended for every PR)
./run-tests.sh smoke

# Run load test (recommended nightly)
./run-tests.sh load

# Run stress test (recommended weekly)
./run-tests.sh stress
```

### Options

```bash
./run-tests.sh [smoke|load|stress] [options]

Options:
  --debug       Enable debug output in tests
  --no-docker   Run k6 locally (requires k6 installed)
  --help        Show help message
```

## Test Types

### Smoke Test (`smoke-test.js`)

- **Purpose**: Quick sanity check to verify all critical endpoints work
- **When to run**: Every PR, before merging
- **Configuration**: 1 VU, 1 minute duration
- **Endpoints tested**:
  - Health check
  - Authentication (login, me)
  - Cases (list, create)
  - Analytics (dashboard, cases, trends)
  - Search

### Load Test (`load-test.js`)

- **Purpose**: Validate performance under normal expected load
- **When to run**: Nightly (CI/CD scheduled job)
- **Configuration**: Ramp to 50 VUs over 2 min, hold 5 min, ramp down 1 min
- **Weighted scenarios**:
  - Browse Cases: 40%
  - Analytics: 20%
  - Search: 20%
  - Create Cases: 15%
  - Profile: 5%

### Stress Test (`stress-test.js`)

- **Purpose**: Find system breaking points and test recovery
- **When to run**: Weekly (scheduled job)
- **Configuration**: Progressive load 50 -> 100 -> 150 -> 200 VUs
- **Duration**: ~10 minutes total

## Thresholds (SLOs)

| Endpoint | p95 Latency | Error Rate |
|----------|-------------|------------|
| `/auth/login` | < 300ms | < 1% |
| `/cases` (list) | < 400ms | < 1% |
| `/analytics/*` | < 200ms | < 1% |
| `/search` | < 800ms | < 1% |

## Configuration

### Environment Variables

```bash
# Override API URL (default: http://api:8000/api/v1 for Docker)
export API_BASE_URL=http://localhost:8000/api/v1

# Override test credentials
export TEST_USERNAME=admin@example.com
export TEST_PASSWORD=admin123

# Enable debug mode
export K6_DEBUG=true
```

### Running Locally (without Docker)

1. Install k6: https://k6.io/docs/getting-started/installation/
2. Run with `--no-docker` flag:

```bash
API_BASE_URL=http://localhost:8000/api/v1 ./run-tests.sh smoke --no-docker
```

## Custom Metrics

The tests track these custom metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `cases_created` | Counter | Number of cases created |
| `cases_viewed` | Counter | Number of case views |
| `searches_performed` | Counter | Number of search queries |
| `analytics_requests` | Counter | Number of analytics API calls |
| `search_latency` | Trend | Search endpoint latency |
| `auth_latency` | Trend | Authentication latency |
| `cases_latency` | Trend | Cases endpoint latency |
| `analytics_latency` | Trend | Analytics endpoint latency |
| `auth_success_rate` | Rate | Authentication success rate |
| `api_success_rate` | Rate | Overall API success rate |

## Results

Test results are saved to the `results/` directory:

- `<test-type>-<timestamp>.json` - Full k6 JSON output
- `<test-type>-test-summary.json` - Summary statistics

### Viewing Results

```bash
# View summary in terminal (generated automatically)

# Parse JSON results with jq
cat results/load-20240115_120000.json | jq '.metrics.http_req_duration'

# Use k6 cloud for detailed analysis (requires k6 cloud account)
k6 cloud results/load-20240115_120000.json
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Load Tests

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM

jobs:
  smoke-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start services
        run: docker-compose up -d

      - name: Wait for API
        run: |
          timeout 60 bash -c 'until curl -s http://localhost:8000/api/v1/health; do sleep 2; done'

      - name: Run smoke test
        run: ./load-tests/run-tests.sh smoke

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: load-test-results
          path: load-tests/results/

  load-test:
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Start services
        run: docker-compose up -d
      - name: Run load test
        run: ./load-tests/run-tests.sh load
```

## Troubleshooting

### Common Issues

1. **Network not found**
   ```
   Error: Docker network 'auditcaseos_default' not found
   ```
   Solution: Start the AuditCaseOS stack first: `docker-compose up -d`

2. **Authentication failed**
   ```
   Error: Login failed: 401 - Unauthorized
   ```
   Solution: Verify the test credentials exist in the database

3. **Connection refused**
   ```
   Error: dial tcp: connect: connection refused
   ```
   Solution: Ensure the API container is running and healthy

### Debug Mode

Enable debug output for more detailed logging:

```bash
./run-tests.sh smoke --debug
```

## Contributing

When adding new tests or endpoints:

1. Add threshold definitions to `thresholds.js`
2. Add helper functions to `scripts/common.js`
3. Update test scenarios as needed
4. Document any new custom metrics in this README
