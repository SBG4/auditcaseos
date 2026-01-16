/**
 * Common utilities for K6 load tests
 * Authentication helpers, custom metrics, and shared functions
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend, Rate } from 'k6/metrics';
import { API_BASE_URL, DEFAULT_CREDENTIALS, TIMEOUTS, DEBUG } from '../config.js';

// ============================================================================
// Custom Metrics
// ============================================================================

// Counter metrics
export const casesCreated = new Counter('cases_created');
export const casesViewed = new Counter('cases_viewed');
export const searchesPerformed = new Counter('searches_performed');
export const analyticsRequests = new Counter('analytics_requests');

// Trend metrics (latency tracking)
export const searchLatency = new Trend('search_latency', true);
export const authLatency = new Trend('auth_latency', true);
export const casesLatency = new Trend('cases_latency', true);
export const analyticsLatency = new Trend('analytics_latency', true);

// Rate metrics (success rates)
export const authSuccessRate = new Rate('auth_success_rate');
export const apiSuccessRate = new Rate('api_success_rate');

// ============================================================================
// Authentication
// ============================================================================

/**
 * Performs OAuth2 login using form data (application/x-www-form-urlencoded)
 * @param {string} username - User email
 * @param {string} password - User password
 * @returns {object} - Response containing access_token
 */
export function login(username = DEFAULT_CREDENTIALS.username, password = DEFAULT_CREDENTIALS.password) {
  const loginUrl = `${API_BASE_URL}/auth/login`;

  // OAuth2 form login - NOT JSON
  const payload = {
    username: username,
    password: password,
  };

  const params = {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    tags: { endpoint: 'auth_login' },
    timeout: TIMEOUTS.auth,
  };

  const response = http.post(loginUrl, payload, params);

  // Track metrics
  authLatency.add(response.timings.duration);
  authSuccessRate.add(response.status === 200);

  if (DEBUG) {
    console.log(`Login response: ${response.status} - ${response.body}`);
  }

  const success = check(response, {
    'login successful': (r) => r.status === 200,
    'has access token': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.access_token !== undefined;
      } catch {
        return false;
      }
    },
  });

  if (!success) {
    console.error(`Login failed: ${response.status} - ${response.body}`);
    return null;
  }

  return JSON.parse(response.body);
}

/**
 * Setup function to get authentication token
 * Call this in your test's setup() function
 * @returns {object} - Object containing access_token for use in tests
 */
export function setupAuth() {
  const authData = login();

  if (!authData || !authData.access_token) {
    throw new Error('Failed to authenticate during setup');
  }

  return {
    token: authData.access_token,
    tokenType: authData.token_type || 'Bearer',
  };
}

/**
 * Returns authorization headers for authenticated requests
 * @param {object} authData - Auth data from setupAuth()
 * @returns {object} - Headers object with Authorization
 */
export function authHeaders(authData) {
  if (!authData || !authData.token) {
    throw new Error('No auth data provided');
  }

  return {
    'Authorization': `${authData.tokenType} ${authData.token}`,
    'Content-Type': 'application/json',
  };
}

// ============================================================================
// API Helpers
// ============================================================================

/**
 * Makes an authenticated GET request
 * @param {string} endpoint - API endpoint (relative to API_BASE_URL)
 * @param {object} authData - Auth data from setupAuth()
 * @param {object} params - Additional k6 params
 * @returns {object} - HTTP response
 */
export function authGet(endpoint, authData, params = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = { ...authHeaders(authData), ...(params.headers || {}) };

  const response = http.get(url, {
    ...params,
    headers,
    timeout: params.timeout || TIMEOUTS.default,
  });

  apiSuccessRate.add(response.status >= 200 && response.status < 300);

  return response;
}

/**
 * Makes an authenticated POST request
 * @param {string} endpoint - API endpoint (relative to API_BASE_URL)
 * @param {object} body - Request body (will be JSON stringified)
 * @param {object} authData - Auth data from setupAuth()
 * @param {object} params - Additional k6 params
 * @returns {object} - HTTP response
 */
export function authPost(endpoint, body, authData, params = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = { ...authHeaders(authData), ...(params.headers || {}) };

  const response = http.post(url, JSON.stringify(body), {
    ...params,
    headers,
    timeout: params.timeout || TIMEOUTS.default,
  });

  apiSuccessRate.add(response.status >= 200 && response.status < 300);

  return response;
}

/**
 * Makes an authenticated PUT request
 * @param {string} endpoint - API endpoint (relative to API_BASE_URL)
 * @param {object} body - Request body (will be JSON stringified)
 * @param {object} authData - Auth data from setupAuth()
 * @param {object} params - Additional k6 params
 * @returns {object} - HTTP response
 */
export function authPut(endpoint, body, authData, params = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = { ...authHeaders(authData), ...(params.headers || {}) };

  const response = http.put(url, JSON.stringify(body), {
    ...params,
    headers,
    timeout: params.timeout || TIMEOUTS.default,
  });

  apiSuccessRate.add(response.status >= 200 && response.status < 300);

  return response;
}

/**
 * Makes an authenticated DELETE request
 * @param {string} endpoint - API endpoint (relative to API_BASE_URL)
 * @param {object} authData - Auth data from setupAuth()
 * @param {object} params - Additional k6 params
 * @returns {object} - HTTP response
 */
export function authDelete(endpoint, authData, params = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = { ...authHeaders(authData), ...(params.headers || {}) };

  const response = http.del(url, null, {
    ...params,
    headers,
    timeout: params.timeout || TIMEOUTS.default,
  });

  apiSuccessRate.add(response.status >= 200 && response.status < 300);

  return response;
}

// ============================================================================
// Test Helpers
// ============================================================================

/**
 * Random think time between requests (simulates user behavior)
 * @param {number} min - Minimum seconds
 * @param {number} max - Maximum seconds
 */
export function thinkTime(min = 1, max = 3) {
  sleep(Math.random() * (max - min) + min);
}

/**
 * Generates a unique identifier for test data
 * @returns {string} - Unique ID
 */
export function uniqueId() {
  return `${Date.now()}-${Math.random().toString(36).substring(7)}`;
}

/**
 * Parses JSON response safely
 * @param {object} response - HTTP response
 * @returns {object|null} - Parsed JSON or null
 */
export function parseJson(response) {
  try {
    return JSON.parse(response.body);
  } catch (e) {
    if (DEBUG) {
      console.error(`Failed to parse JSON: ${e.message}`);
    }
    return null;
  }
}

/**
 * Checks if response is successful (2xx status)
 * @param {object} response - HTTP response
 * @returns {boolean}
 */
export function isSuccess(response) {
  return response.status >= 200 && response.status < 300;
}

/**
 * Random element from array
 * @param {array} arr - Array to pick from
 * @returns {*} - Random element
 */
export function randomElement(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

// ============================================================================
// Endpoint Test Functions
// ============================================================================

/**
 * Test health endpoint
 * @returns {object} - HTTP response
 */
export function testHealth() {
  const response = http.get(`${API_BASE_URL}/health`, {
    tags: { endpoint: 'health' },
    timeout: TIMEOUTS.default,
  });

  check(response, {
    'health check OK': (r) => r.status === 200,
  });

  return response;
}

/**
 * Test auth/me endpoint
 * @param {object} authData - Auth data from setupAuth()
 * @returns {object} - HTTP response
 */
export function testAuthMe(authData) {
  const response = authGet('/auth/me', authData, {
    tags: { endpoint: 'auth_me' },
  });

  authLatency.add(response.timings.duration);

  check(response, {
    'auth/me successful': (r) => r.status === 200,
    'has user data': (r) => {
      const body = parseJson(r);
      return body && body.email !== undefined;
    },
  });

  return response;
}

/**
 * Test cases list endpoint
 * @param {object} authData - Auth data from setupAuth()
 * @param {number} limit - Number of cases to fetch
 * @returns {object} - HTTP response
 */
export function testCasesList(authData, limit = 20) {
  const response = authGet(`/cases?limit=${limit}`, authData, {
    tags: { endpoint: 'cases_list' },
  });

  casesLatency.add(response.timings.duration);
  casesViewed.add(1);

  check(response, {
    'cases list successful': (r) => r.status === 200,
    'returns array': (r) => {
      const body = parseJson(r);
      return body && Array.isArray(body.items || body);
    },
  });

  return response;
}

/**
 * Test case creation
 * @param {object} authData - Auth data from setupAuth()
 * @param {object} caseData - Case data to create
 * @returns {object} - HTTP response
 */
export function testCaseCreate(authData, caseData) {
  const response = authPost('/cases', caseData, authData, {
    tags: { endpoint: 'cases_create' },
  });

  casesLatency.add(response.timings.duration);

  if (isSuccess(response)) {
    casesCreated.add(1);
  }

  check(response, {
    'case created': (r) => r.status === 201 || r.status === 200,
    'has case id': (r) => {
      const body = parseJson(r);
      return body && (body.id !== undefined || body.case_id !== undefined);
    },
  });

  return response;
}

/**
 * Test analytics dashboard endpoint
 * @param {object} authData - Auth data from setupAuth()
 * @returns {object} - HTTP response
 */
export function testAnalyticsDashboard(authData) {
  const response = authGet('/analytics/dashboard', authData, {
    tags: { endpoint: 'analytics_dashboard' },
    timeout: TIMEOUTS.analytics,
  });

  analyticsLatency.add(response.timings.duration);
  analyticsRequests.add(1);

  check(response, {
    'analytics dashboard successful': (r) => r.status === 200,
  });

  return response;
}

/**
 * Test analytics cases endpoint
 * @param {object} authData - Auth data from setupAuth()
 * @returns {object} - HTTP response
 */
export function testAnalyticsCases(authData) {
  const response = authGet('/analytics/cases', authData, {
    tags: { endpoint: 'analytics_cases' },
    timeout: TIMEOUTS.analytics,
  });

  analyticsLatency.add(response.timings.duration);
  analyticsRequests.add(1);

  check(response, {
    'analytics cases successful': (r) => r.status === 200,
  });

  return response;
}

/**
 * Test analytics trends endpoint
 * @param {object} authData - Auth data from setupAuth()
 * @returns {object} - HTTP response
 */
export function testAnalyticsTrends(authData) {
  const response = authGet('/analytics/trends', authData, {
    tags: { endpoint: 'analytics_trends' },
    timeout: TIMEOUTS.analytics,
  });

  analyticsLatency.add(response.timings.duration);
  analyticsRequests.add(1);

  check(response, {
    'analytics trends successful': (r) => r.status === 200,
  });

  return response;
}

/**
 * Test search endpoint
 * @param {object} authData - Auth data from setupAuth()
 * @param {string} query - Search query
 * @returns {object} - HTTP response
 */
export function testSearch(authData, query) {
  const response = authGet(`/search?q=${encodeURIComponent(query)}`, authData, {
    tags: { endpoint: 'search' },
    timeout: TIMEOUTS.search,
  });

  searchLatency.add(response.timings.duration);
  searchesPerformed.add(1);

  check(response, {
    'search successful': (r) => r.status === 200,
    'returns results': (r) => {
      const body = parseJson(r);
      return body && (Array.isArray(body.results || body.items || body));
    },
  });

  return response;
}
