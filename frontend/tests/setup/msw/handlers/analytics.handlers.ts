/**
 * MSW handlers for analytics API endpoints.
 */

import { http, HttpResponse } from 'msw';

const API_BASE = '/api/v1';

// Mock analytics data
const mockOverview = {
  total_cases: 27,
  open_cases: 15,
  critical_cases: 3,
  closed_cases: 8,
  total_evidence: 45,
  total_findings: 32,
  total_entities: 128,
};

const mockCaseStats = {
  by_status: {
    OPEN: 15,
    IN_PROGRESS: 5,
    PENDING_REVIEW: 2,
    CLOSED: 8,
    ARCHIVED: 2,
  },
  by_severity: {
    CRITICAL: 3,
    HIGH: 8,
    MEDIUM: 10,
    LOW: 4,
    INFO: 2,
  },
  by_type: {
    USB: 5,
    EMAIL: 8,
    WEB: 4,
    POLICY: 6,
    LEAK: 2,
    ACCESS: 2,
    OTHER: 0,
  },
  by_scope: {
    FIN: 8,
    HR: 5,
    IT: 7,
    SEC: 4,
    OPS: 2,
    GEN: 1,
  },
};

const mockTrends = {
  period_days: 30,
  created: [
    { date: '2024-01-01', count: 2 },
    { date: '2024-01-08', count: 5 },
    { date: '2024-01-15', count: 3 },
    { date: '2024-01-22', count: 4 },
  ],
  closed: [
    { date: '2024-01-01', count: 1 },
    { date: '2024-01-08', count: 2 },
    { date: '2024-01-15', count: 2 },
    { date: '2024-01-22', count: 3 },
  ],
};

const mockEvidenceFindings = {
  evidence: {
    by_type: {
      'application/pdf': 15,
      'image/png': 10,
      'text/plain': 8,
      'message/rfc822': 12,
    },
    total_size_bytes: 125829120,
    average_per_case: 1.7,
  },
  findings: {
    by_severity: {
      CRITICAL: 5,
      HIGH: 12,
      MEDIUM: 10,
      LOW: 5,
    },
    average_per_case: 1.2,
  },
};

const mockEntityInsights = {
  by_type: {
    EMAIL: 35,
    IP_ADDRESS: 28,
    DOMAIN: 20,
    URL: 15,
    USERNAME: 18,
    HASH: 12,
  },
  top_entities: [
    { type: 'EMAIL', value: 'suspicious@hacker.com', count: 5 },
    { type: 'IP_ADDRESS', value: '192.168.1.100', count: 4 },
    { type: 'DOMAIN', value: 'malicious-site.com', count: 3 },
  ],
};

const mockUserActivity = {
  period_days: 30,
  actions_by_type: {
    VIEW: 250,
    CREATE: 45,
    UPDATE: 120,
    DELETE: 5,
  },
  top_users: [
    { user_id: '123', full_name: 'Admin User', action_count: 150 },
    { user_id: '124', full_name: 'Auditor 1', action_count: 120 },
    { user_id: '125', full_name: 'Auditor 2', action_count: 80 },
  ],
};

export const analyticsHandlers = [
  // Dashboard overview
  http.get(`${API_BASE}/analytics/overview`, () => {
    return HttpResponse.json(mockOverview);
  }),

  // Case statistics
  http.get(`${API_BASE}/analytics/cases`, () => {
    return HttpResponse.json(mockCaseStats);
  }),

  // Trends
  http.get(`${API_BASE}/analytics/trends`, ({ request }) => {
    const url = new URL(request.url);
    const days = parseInt(url.searchParams.get('days') || '30');

    return HttpResponse.json({
      ...mockTrends,
      period_days: days,
    });
  }),

  // Evidence and findings stats
  http.get(`${API_BASE}/analytics/evidence-findings`, () => {
    return HttpResponse.json(mockEvidenceFindings);
  }),

  // Entity insights
  http.get(`${API_BASE}/analytics/entities`, () => {
    return HttpResponse.json(mockEntityInsights);
  }),

  // User activity
  http.get(`${API_BASE}/analytics/activity`, () => {
    return HttpResponse.json(mockUserActivity);
  }),

  // Full analytics (combined)
  http.get(`${API_BASE}/analytics/full`, () => {
    return HttpResponse.json({
      overview: mockOverview,
      cases: mockCaseStats,
      trends: mockTrends,
      evidence_findings: mockEvidenceFindings,
      entities: mockEntityInsights,
      activity: mockUserActivity,
    });
  }),
];
