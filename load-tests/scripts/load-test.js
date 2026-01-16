/**
 * Load Test for AuditCaseOS
 *
 * Purpose: Nightly performance validation under normal load
 * Configuration: Ramp 2m to 50 VUs, hold 5m, ramp down 1m (8 min total)
 *
 * Weighted Scenarios:
 * - Browse Cases: 40%
 * - Analytics: 20%
 * - Search: 20%
 * - Create Cases: 15%
 * - Profile: 5%
 */

import { sleep } from 'k6';
import { LOAD_THRESHOLDS } from '../thresholds.js';
import { TEST_DATA } from '../config.js';
import {
  setupAuth,
  testHealth,
  testAuthMe,
  testCasesList,
  testCaseCreate,
  testAnalyticsDashboard,
  testAnalyticsCases,
  testAnalyticsTrends,
  testSearch,
  authGet,
  thinkTime,
  uniqueId,
  randomElement,
  casesLatency,
  analyticsLatency,
  searchLatency,
} from './common.js';

// ============================================================================
// Test Configuration
// ============================================================================

export const options = {
  // Scenarios with weighted distribution
  scenarios: {
    // Browse Cases - 40% of traffic
    browse_cases: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 20 },  // Ramp up to 20 VUs (40% of 50)
        { duration: '5m', target: 20 },  // Hold at 20 VUs
        { duration: '1m', target: 0 },   // Ramp down
      ],
      exec: 'browseCases',
      tags: { scenario: 'browse' },
    },

    // Analytics - 20% of traffic
    analytics: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 10 },  // Ramp up to 10 VUs (20% of 50)
        { duration: '5m', target: 10 },  // Hold at 10 VUs
        { duration: '1m', target: 0 },   // Ramp down
      ],
      exec: 'viewAnalytics',
      tags: { scenario: 'analytics' },
    },

    // Search - 20% of traffic
    search: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 10 },  // Ramp up to 10 VUs (20% of 50)
        { duration: '5m', target: 10 },  // Hold at 10 VUs
        { duration: '1m', target: 0 },   // Ramp down
      ],
      exec: 'performSearch',
      tags: { scenario: 'search' },
    },

    // Create Cases - 15% of traffic
    create_cases: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 8 },   // Ramp up to ~8 VUs (15% of 50)
        { duration: '5m', target: 8 },   // Hold at 8 VUs
        { duration: '1m', target: 0 },   // Ramp down
      ],
      exec: 'createCases',
      tags: { scenario: 'create' },
    },

    // Profile - 5% of traffic
    profile: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 2 },   // Ramp up to 2 VUs (5% of 50)
        { duration: '5m', target: 2 },   // Hold at 2 VUs
        { duration: '1m', target: 0 },   // Ramp down
      ],
      exec: 'viewProfile',
      tags: { scenario: 'profile' },
    },
  },

  // Thresholds from SLO definitions
  thresholds: LOAD_THRESHOLDS,

  // Tags for result filtering
  tags: {
    testType: 'load',
  },

  // Summary output configuration
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

// ============================================================================
// Setup - Run once before all iterations
// ============================================================================

export function setup() {
  console.log('=== Load Test Setup ===');
  console.log('Total duration: 8 minutes');
  console.log('Peak VUs: 50');
  console.log('');
  console.log('Scenario distribution:');
  console.log('  - Browse Cases: 40% (20 VUs)');
  console.log('  - Analytics: 20% (10 VUs)');
  console.log('  - Search: 20% (10 VUs)');
  console.log('  - Create Cases: 15% (8 VUs)');
  console.log('  - Profile: 5% (2 VUs)');
  console.log('');

  // Verify API is healthy
  testHealth();

  // Get authentication token
  const authData = setupAuth();
  console.log('Authentication successful');

  return authData;
}

// ============================================================================
// Scenario: Browse Cases (40%)
// ============================================================================

export function browseCases(authData) {
  // List cases with different pagination
  const limits = [10, 20, 50];
  const limit = randomElement(limits);

  testCasesList(authData, limit);
  thinkTime(2, 5);

  // Occasionally view a specific case
  if (Math.random() < 0.3) {
    const casesResponse = testCasesList(authData, 5);
    try {
      const cases = JSON.parse(casesResponse.body);
      const items = cases.items || cases;
      if (items && items.length > 0) {
        const caseId = items[0].id || items[0].case_id;
        if (caseId) {
          authGet(`/cases/${caseId}`, authData, {
            tags: { endpoint: 'cases_get' },
          });
          casesLatency.add(casesResponse.timings.duration);
        }
      }
    } catch (e) {
      // Ignore parsing errors
    }
    thinkTime(1, 3);
  }
}

// ============================================================================
// Scenario: Analytics (20%)
// ============================================================================

export function viewAnalytics(authData) {
  // Randomly select an analytics endpoint
  const analyticsEndpoints = [
    () => testAnalyticsDashboard(authData),
    () => testAnalyticsCases(authData),
    () => testAnalyticsTrends(authData),
  ];

  const selectedEndpoint = randomElement(analyticsEndpoints);
  selectedEndpoint();
  thinkTime(3, 7);

  // Sometimes view multiple analytics pages (simulate dashboard refresh)
  if (Math.random() < 0.4) {
    testAnalyticsDashboard(authData);
    thinkTime(1, 2);
    testAnalyticsTrends(authData);
  }
}

// ============================================================================
// Scenario: Search (20%)
// ============================================================================

export function performSearch(authData) {
  // Select a random search query
  const query = randomElement(TEST_DATA.searchQueries);
  testSearch(authData, query);
  thinkTime(2, 5);

  // Sometimes perform multiple searches (refining results)
  if (Math.random() < 0.3) {
    const refinedQuery = `${query} ${randomElement(['2024', 'important', 'urgent', 'completed'])}`;
    testSearch(authData, refinedQuery);
    thinkTime(1, 3);
  }
}

// ============================================================================
// Scenario: Create Cases (15%)
// ============================================================================

export function createCases(authData) {
  // Create a new case
  const priorities = ['low', 'medium', 'high', 'critical'];
  const statuses = ['open', 'in_progress', 'pending_review'];

  const newCase = {
    title: `Load Test Case - ${uniqueId()}`,
    description: `Created during load test at ${new Date().toISOString()}`,
    priority: randomElement(priorities),
    status: randomElement(statuses),
  };

  testCaseCreate(authData, newCase);
  thinkTime(3, 8);

  // After creating, sometimes view the cases list
  if (Math.random() < 0.5) {
    testCasesList(authData, 10);
  }
}

// ============================================================================
// Scenario: Profile (5%)
// ============================================================================

export function viewProfile(authData) {
  // View user profile
  testAuthMe(authData);
  thinkTime(5, 10);

  // Occasionally check health status
  if (Math.random() < 0.2) {
    testHealth();
  }
}

// ============================================================================
// Teardown - Run once after all iterations
// ============================================================================

export function teardown(authData) {
  console.log('=== Load Test Complete ===');
}

// ============================================================================
// Handle Summary
// ============================================================================

export function handleSummary(data) {
  const thresholdResults = [];
  let allPassed = true;

  for (const [metricName, metric] of Object.entries(data.metrics)) {
    if (metric.thresholds) {
      for (const [thresholdName, threshold] of Object.entries(metric.thresholds)) {
        thresholdResults.push({
          metric: metricName,
          threshold: thresholdName,
          passed: threshold.ok,
        });
        if (!threshold.ok) {
          allPassed = false;
        }
      }
    }
  }

  console.log(`\n${'='.repeat(60)}`);
  console.log(`Load Test Result: ${allPassed ? 'PASSED' : 'FAILED'}`);
  console.log(`${'='.repeat(60)}`);

  if (!allPassed) {
    console.log('\nFailed Thresholds:');
    thresholdResults
      .filter((t) => !t.passed)
      .forEach((t) => {
        console.log(`  - ${t.metric}: ${t.threshold}`);
      });
  }

  console.log('\nKey Metrics:');
  if (data.metrics.http_req_duration) {
    const duration = data.metrics.http_req_duration;
    console.log(`  - Request Duration (p95): ${duration.values['p(95)']?.toFixed(2)}ms`);
    console.log(`  - Request Duration (avg): ${duration.values.avg?.toFixed(2)}ms`);
  }
  if (data.metrics.http_req_failed) {
    console.log(`  - Error Rate: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%`);
  }
  if (data.metrics.http_reqs) {
    console.log(`  - Total Requests: ${data.metrics.http_reqs.values.count}`);
    console.log(`  - Requests/sec: ${data.metrics.http_reqs.values.rate?.toFixed(2)}`);
  }

  return {
    'stdout': JSON.stringify(data, null, 2),
    'results/load-test-summary.json': JSON.stringify(data, null, 2),
  };
}
