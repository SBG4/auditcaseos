/**
 * Stress Test for AuditCaseOS
 *
 * Purpose: Weekly stress test to find breaking points
 * Configuration: Progressive load 50 -> 100 -> 150 -> 200 VUs (10 min total)
 *
 * Objectives:
 * - Identify system breaking point
 * - Test recovery behavior
 * - Find performance degradation patterns
 */

import { sleep } from 'k6';
import { STRESS_THRESHOLDS } from '../thresholds.js';
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
  isSuccess,
} from './common.js';

// ============================================================================
// Test Configuration
// ============================================================================

export const options = {
  // Progressive stress test stages
  stages: [
    // Warm-up
    { duration: '30s', target: 50 },   // Ramp to baseline (50 VUs)

    // Stage 1: Normal load
    { duration: '2m', target: 50 },    // Hold at 50 VUs

    // Stage 2: Above normal
    { duration: '30s', target: 100 },  // Ramp to 100 VUs
    { duration: '2m', target: 100 },   // Hold at 100 VUs

    // Stage 3: High load
    { duration: '30s', target: 150 },  // Ramp to 150 VUs
    { duration: '2m', target: 150 },   // Hold at 150 VUs

    // Stage 4: Stress load
    { duration: '30s', target: 200 },  // Ramp to 200 VUs
    { duration: '1m', target: 200 },   // Hold at peak

    // Recovery
    { duration: '30s', target: 0 },    // Ramp down
  ],

  // Thresholds from SLO definitions (relaxed for stress testing)
  thresholds: STRESS_THRESHOLDS,

  // Tags for result filtering
  tags: {
    testType: 'stress',
  },

  // Summary output configuration
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

// ============================================================================
// Setup - Run once before all iterations
// ============================================================================

export function setup() {
  console.log('=== Stress Test Setup ===');
  console.log('Total duration: ~10 minutes');
  console.log('');
  console.log('Load progression:');
  console.log('  - Stage 1: 50 VUs (baseline)');
  console.log('  - Stage 2: 100 VUs (above normal)');
  console.log('  - Stage 3: 150 VUs (high load)');
  console.log('  - Stage 4: 200 VUs (stress/breaking point)');
  console.log('');

  // Verify API is healthy before stress test
  const healthResponse = testHealth();
  if (!isSuccess(healthResponse)) {
    throw new Error('API health check failed - aborting stress test');
  }

  // Get authentication token
  const authData = setupAuth();
  console.log('Authentication successful');
  console.log('Starting stress test...\n');

  return authData;
}

// ============================================================================
// Main Test Scenario - Mixed Workload
// ============================================================================

export default function (authData) {
  // Weighted random selection of operations
  const operation = selectOperation();

  switch (operation) {
    case 'health':
      runHealthCheck();
      break;
    case 'browse':
      runBrowseCases(authData);
      break;
    case 'analytics':
      runAnalytics(authData);
      break;
    case 'search':
      runSearch(authData);
      break;
    case 'create':
      runCreateCase(authData);
      break;
    case 'profile':
      runProfile(authData);
      break;
    default:
      runBrowseCases(authData);
  }

  // Minimal think time during stress test to maximize load
  thinkTime(0.5, 1.5);
}

// ============================================================================
// Operation Selection (Weighted)
// ============================================================================

function selectOperation() {
  const weights = {
    health: 5,      // 5%
    browse: 35,     // 35%
    analytics: 20,  // 20%
    search: 20,     // 20%
    create: 15,     // 15%
    profile: 5,     // 5%
  };

  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  let random = Math.random() * total;

  for (const [operation, weight] of Object.entries(weights)) {
    random -= weight;
    if (random <= 0) {
      return operation;
    }
  }

  return 'browse';
}

// ============================================================================
// Individual Operations
// ============================================================================

function runHealthCheck() {
  testHealth();
}

function runBrowseCases(authData) {
  const limits = [10, 20, 50, 100];
  const limit = randomElement(limits);

  const response = testCasesList(authData, limit);

  // Sometimes drill down into a case
  if (Math.random() < 0.2 && isSuccess(response)) {
    try {
      const cases = JSON.parse(response.body);
      const items = cases.items || cases;
      if (items && items.length > 0) {
        const caseId = items[0].id || items[0].case_id;
        if (caseId) {
          authGet(`/cases/${caseId}`, authData, {
            tags: { endpoint: 'cases_get' },
          });
        }
      }
    } catch (e) {
      // Continue on error
    }
  }
}

function runAnalytics(authData) {
  // Cycle through analytics endpoints
  const endpoints = [
    () => testAnalyticsDashboard(authData),
    () => testAnalyticsCases(authData),
    () => testAnalyticsTrends(authData),
  ];

  // Run 1-2 analytics requests
  randomElement(endpoints)();

  if (Math.random() < 0.3) {
    randomElement(endpoints)();
  }
}

function runSearch(authData) {
  const queries = [
    ...TEST_DATA.searchQueries,
    // Additional stress test queries
    'a',                          // Single character
    'test case audit compliance', // Multiple words
    '2024 Q1 financial review',   // Complex query
    randomElement(['urgent', 'critical', 'high priority']),
  ];

  const query = randomElement(queries);
  testSearch(authData, query);

  // Sometimes perform follow-up searches
  if (Math.random() < 0.2) {
    const refinedQuery = `${query} ${uniqueId().substring(0, 4)}`;
    testSearch(authData, refinedQuery);
  }
}

function runCreateCase(authData) {
  const priorities = ['low', 'medium', 'high', 'critical'];
  const statuses = ['open', 'in_progress', 'pending_review', 'resolved'];

  const newCase = {
    title: `Stress Test Case - ${uniqueId()}`,
    description: `Created during stress test. VU: ${__VU}, Iter: ${__ITER}`,
    priority: randomElement(priorities),
    status: randomElement(statuses),
    tags: ['stress-test', 'automated'],
  };

  testCaseCreate(authData, newCase);
}

function runProfile(authData) {
  testAuthMe(authData);
}

// ============================================================================
// Teardown - Run once after all iterations
// ============================================================================

export function teardown(authData) {
  console.log('\n=== Stress Test Complete ===');

  // Final health check to verify system recovery
  console.log('Verifying system recovery...');
  const healthResponse = testHealth();

  if (isSuccess(healthResponse)) {
    console.log('System recovered successfully');
  } else {
    console.log('WARNING: System may not have fully recovered');
  }
}

// ============================================================================
// Handle Summary
// ============================================================================

export function handleSummary(data) {
  const thresholdResults = [];
  let allPassed = true;
  let failedCount = 0;

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
          failedCount++;
        }
      }
    }
  }

  console.log(`\n${'='.repeat(70)}`);
  console.log(`Stress Test Result: ${allPassed ? 'PASSED' : 'FAILED'}`);
  console.log(`${'='.repeat(70)}`);

  // Performance summary
  console.log('\n--- Performance Summary ---\n');

  if (data.metrics.http_req_duration) {
    const duration = data.metrics.http_req_duration;
    console.log('Request Duration:');
    console.log(`  Average: ${duration.values.avg?.toFixed(2)}ms`);
    console.log(`  Median:  ${duration.values.med?.toFixed(2)}ms`);
    console.log(`  p(90):   ${duration.values['p(90)']?.toFixed(2)}ms`);
    console.log(`  p(95):   ${duration.values['p(95)']?.toFixed(2)}ms`);
    console.log(`  p(99):   ${duration.values['p(99)']?.toFixed(2)}ms`);
    console.log(`  Max:     ${duration.values.max?.toFixed(2)}ms`);
  }

  if (data.metrics.http_req_failed) {
    const errorRate = data.metrics.http_req_failed.values.rate * 100;
    console.log(`\nError Rate: ${errorRate.toFixed(2)}%`);

    if (errorRate > 5) {
      console.log('  WARNING: Error rate exceeds 5% - system may have reached breaking point');
    }
  }

  if (data.metrics.http_reqs) {
    console.log(`\nThroughput:`);
    console.log(`  Total Requests: ${data.metrics.http_reqs.values.count}`);
    console.log(`  Requests/sec:   ${data.metrics.http_reqs.values.rate?.toFixed(2)}`);
  }

  // Breaking point analysis
  console.log('\n--- Breaking Point Analysis ---\n');

  if (data.metrics.vus) {
    console.log(`Peak VUs: ${data.metrics.vus.values.max}`);
  }

  if (!allPassed) {
    console.log(`\nThresholds Failed: ${failedCount}`);
    console.log('Failed thresholds indicate potential breaking points:');
    thresholdResults
      .filter((t) => !t.passed)
      .forEach((t) => {
        console.log(`  - ${t.metric}: ${t.threshold}`);
      });
  } else {
    console.log('\nAll thresholds passed - system handled stress load successfully');
  }

  // Recommendations
  console.log('\n--- Recommendations ---\n');

  if (data.metrics.http_req_failed) {
    const errorRate = data.metrics.http_req_failed.values.rate * 100;

    if (errorRate > 10) {
      console.log('- CRITICAL: High error rate detected. Consider scaling resources.');
    } else if (errorRate > 5) {
      console.log('- WARNING: Moderate error rate. Review server capacity.');
    } else if (errorRate > 1) {
      console.log('- INFO: Low error rate. System is handling load well.');
    } else {
      console.log('- GOOD: Minimal errors. System is robust under stress.');
    }
  }

  if (data.metrics.http_req_duration) {
    const p95 = data.metrics.http_req_duration.values['p(95)'];

    if (p95 > 2000) {
      console.log('- CRITICAL: p95 latency > 2s. Performance optimization needed.');
    } else if (p95 > 1000) {
      console.log('- WARNING: p95 latency > 1s. Consider caching strategies.');
    } else if (p95 > 500) {
      console.log('- INFO: p95 latency acceptable but could be improved.');
    } else {
      console.log('- GOOD: p95 latency is within acceptable range.');
    }
  }

  return {
    'stdout': JSON.stringify(data, null, 2),
    'results/stress-test-summary.json': JSON.stringify(data, null, 2),
  };
}
