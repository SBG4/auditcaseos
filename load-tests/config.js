/**
 * K6 Load Testing Configuration
 * Environment configuration for AuditCaseOS load tests
 */

// API Base URL - Docker internal network
export const API_BASE_URL = __ENV.API_BASE_URL || 'http://api:8000/api/v1';

// Default test credentials
export const DEFAULT_CREDENTIALS = {
  username: __ENV.TEST_USERNAME || 'admin@example.com',
  password: __ENV.TEST_PASSWORD || 'admin123',
};

// Request timeout settings (in milliseconds)
export const TIMEOUTS = {
  default: 30000,
  auth: 10000,
  search: 15000,
  analytics: 10000,
};

// Batch sizes for bulk operations
export const BATCH_SIZES = {
  casesList: 20,
  searchResults: 50,
  analyticsRange: 30, // days
};

// Test data configuration
export const TEST_DATA = {
  // Sample case data for creation tests
  sampleCase: {
    title: 'Load Test Case',
    description: 'Created during k6 load testing',
    priority: 'medium',
    status: 'open',
  },
  // Search queries for search tests
  searchQueries: [
    'audit',
    'compliance',
    'risk assessment',
    'financial',
    'security',
  ],
};

// Environment detection
export const ENVIRONMENT = __ENV.K6_ENV || 'docker';

// Debug mode
export const DEBUG = __ENV.K6_DEBUG === 'true';
