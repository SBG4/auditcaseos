/**
 * K6 Threshold Definitions
 * SLO (Service Level Objective) definitions for AuditCaseOS
 */

// Authentication endpoint thresholds
export const AUTH_THRESHOLDS = {
  'http_req_duration{endpoint:auth_login}': ['p(95)<300', 'p(99)<500'],
  'http_req_failed{endpoint:auth_login}': ['rate<0.01'],
  'http_req_duration{endpoint:auth_me}': ['p(95)<200', 'p(99)<400'],
  'http_req_failed{endpoint:auth_me}': ['rate<0.01'],
};

// Cases endpoint thresholds
export const CASES_THRESHOLDS = {
  'http_req_duration{endpoint:cases_list}': ['p(95)<400', 'p(99)<800'],
  'http_req_failed{endpoint:cases_list}': ['rate<0.01'],
  'http_req_duration{endpoint:cases_get}': ['p(95)<300', 'p(99)<600'],
  'http_req_failed{endpoint:cases_get}': ['rate<0.01'],
  'http_req_duration{endpoint:cases_create}': ['p(95)<500', 'p(99)<1000'],
  'http_req_failed{endpoint:cases_create}': ['rate<0.01'],
};

// Analytics endpoint thresholds
export const ANALYTICS_THRESHOLDS = {
  'http_req_duration{endpoint:analytics_dashboard}': ['p(95)<200', 'p(99)<400'],
  'http_req_failed{endpoint:analytics_dashboard}': ['rate<0.01'],
  'http_req_duration{endpoint:analytics_cases}': ['p(95)<200', 'p(99)<400'],
  'http_req_failed{endpoint:analytics_cases}': ['rate<0.01'],
  'http_req_duration{endpoint:analytics_trends}': ['p(95)<200', 'p(99)<400'],
  'http_req_failed{endpoint:analytics_trends}': ['rate<0.01'],
};

// Search endpoint thresholds
export const SEARCH_THRESHOLDS = {
  'http_req_duration{endpoint:search}': ['p(95)<800', 'p(99)<1500'],
  'http_req_failed{endpoint:search}': ['rate<0.01'],
};

// Health check thresholds
export const HEALTH_THRESHOLDS = {
  'http_req_duration{endpoint:health}': ['p(95)<100', 'p(99)<200'],
  'http_req_failed{endpoint:health}': ['rate<0.001'],
};

// Combined thresholds for smoke tests
export const SMOKE_THRESHOLDS = {
  ...HEALTH_THRESHOLDS,
  ...AUTH_THRESHOLDS,
  ...CASES_THRESHOLDS,
  ...ANALYTICS_THRESHOLDS,
  ...SEARCH_THRESHOLDS,
  // Overall thresholds
  http_req_duration: ['p(95)<500', 'p(99)<1000'],
  http_req_failed: ['rate<0.01'],
  http_reqs: ['rate>1'],
};

// Load test thresholds (slightly relaxed for higher load)
export const LOAD_THRESHOLDS = {
  ...HEALTH_THRESHOLDS,
  ...AUTH_THRESHOLDS,
  ...CASES_THRESHOLDS,
  ...ANALYTICS_THRESHOLDS,
  ...SEARCH_THRESHOLDS,
  // Overall thresholds
  http_req_duration: ['p(95)<600', 'p(99)<1200'],
  http_req_failed: ['rate<0.02'],
  http_reqs: ['rate>10'],
  // Custom metrics thresholds
  cases_created: ['count>10'],
  search_latency: ['p(95)<800'],
};

// Stress test thresholds (focus on error rates)
export const STRESS_THRESHOLDS = {
  // Relaxed latency thresholds for stress testing
  'http_req_duration{endpoint:auth_login}': ['p(95)<500'],
  'http_req_duration{endpoint:cases_list}': ['p(95)<800'],
  'http_req_duration{endpoint:analytics_dashboard}': ['p(95)<400'],
  'http_req_duration{endpoint:search}': ['p(95)<1500'],
  // Error rate is critical even under stress
  http_req_failed: ['rate<0.05'],
  // Track recovery time
  http_reqs: ['rate>5'],
};

// Export all thresholds
export default {
  smoke: SMOKE_THRESHOLDS,
  load: LOAD_THRESHOLDS,
  stress: STRESS_THRESHOLDS,
};
