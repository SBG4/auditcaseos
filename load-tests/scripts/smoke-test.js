/**
 * Smoke Test for AuditCaseOS
 *
 * Purpose: Quick sanity check for every PR
 * Configuration: 1 VU, 1 minute duration
 *
 * Tests all critical endpoints to ensure basic functionality:
 * - Health check
 * - Authentication (login, me)
 * - Cases (list, create)
 * - Analytics (dashboard, cases, trends)
 * - Search
 */

import { sleep } from 'k6';
import { SMOKE_THRESHOLDS } from '../thresholds.js';
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
  thinkTime,
  uniqueId,
  randomElement,
} from './common.js';

// ============================================================================
// Test Configuration
// ============================================================================

export const options = {
  // Smoke test: 1 VU, 1 minute
  vus: 1,
  duration: '1m',

  // Thresholds from SLO definitions
  thresholds: SMOKE_THRESHOLDS,

  // Tags for result filtering
  tags: {
    testType: 'smoke',
  },

  // Summary output configuration
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

// ============================================================================
// Setup - Run once before all iterations
// ============================================================================

export function setup() {
  console.log('=== Smoke Test Setup ===');
  console.log('Authenticating test user...');

  // Get authentication token
  const authData = setupAuth();
  console.log('Authentication successful');

  return authData;
}

// ============================================================================
// Main Test Scenario
// ============================================================================

export default function (authData) {
  // 1. Health Check
  console.log('Testing: Health endpoint');
  testHealth();
  thinkTime(0.5, 1);

  // 2. Auth - Get current user
  console.log('Testing: Auth/me endpoint');
  testAuthMe(authData);
  thinkTime(0.5, 1);

  // 3. Cases - List
  console.log('Testing: Cases list endpoint');
  testCasesList(authData, 10);
  thinkTime(0.5, 1);

  // 4. Cases - Create
  console.log('Testing: Cases create endpoint');
  const newCase = {
    ...TEST_DATA.sampleCase,
    title: `Smoke Test Case - ${uniqueId()}`,
  };
  testCaseCreate(authData, newCase);
  thinkTime(0.5, 1);

  // 5. Analytics - Dashboard
  console.log('Testing: Analytics dashboard endpoint');
  testAnalyticsDashboard(authData);
  thinkTime(0.5, 1);

  // 6. Analytics - Cases
  console.log('Testing: Analytics cases endpoint');
  testAnalyticsCases(authData);
  thinkTime(0.5, 1);

  // 7. Analytics - Trends
  console.log('Testing: Analytics trends endpoint');
  testAnalyticsTrends(authData);
  thinkTime(0.5, 1);

  // 8. Search
  console.log('Testing: Search endpoint');
  const searchQuery = randomElement(TEST_DATA.searchQueries);
  testSearch(authData, searchQuery);
  thinkTime(0.5, 1);

  // Brief pause before next iteration
  sleep(1);
}

// ============================================================================
// Teardown - Run once after all iterations
// ============================================================================

export function teardown(authData) {
  console.log('=== Smoke Test Complete ===');
}

// ============================================================================
// Handle Summary
// ============================================================================

export function handleSummary(data) {
  const passed = Object.values(data.metrics).every((metric) => {
    if (metric.thresholds) {
      return Object.values(metric.thresholds).every((t) => t.ok);
    }
    return true;
  });

  console.log(`\n${'='.repeat(50)}`);
  console.log(`Smoke Test Result: ${passed ? 'PASSED' : 'FAILED'}`);
  console.log(`${'='.repeat(50)}\n`);

  return {
    'stdout': JSON.stringify(data, null, 2),
    'results/smoke-test-summary.json': JSON.stringify(data, null, 2),
  };
}
