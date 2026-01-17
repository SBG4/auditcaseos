/**
 * MSW handlers for cases API endpoints.
 */

import { http, HttpResponse } from 'msw';

const API_BASE = '/api/v1';

// Mock case data
export const mockCases = [
  {
    id: 'case-1',
    case_id: 'case-1',
    case_number: 'FIN-USB-0001',
    scope_code: 'FIN',
    case_type: 'USB',
    status: 'OPEN',
    severity: 'HIGH',
    title: 'Unauthorized USB Device Usage',
    summary: 'Employee used unauthorized USB drive',
    description: 'Full investigation details here...',
    subject_user: 'john.doe',
    subject_computer: 'WORKSTATION-001',
    owner_id: '123e4567-e89b-12d3-a456-426614174000',
    evidence_count: 3,
    findings_count: 2,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-16T14:30:00Z',
  },
  {
    id: 'case-2',
    case_id: 'case-2',
    case_number: 'IT-EMAIL-0001',
    scope_code: 'IT',
    case_type: 'EMAIL',
    status: 'IN_PROGRESS',
    severity: 'CRITICAL',
    title: 'Phishing Attack Investigation',
    summary: 'Multiple employees received phishing emails',
    description: 'Investigation ongoing...',
    subject_user: null,
    subject_computer: null,
    owner_id: '123e4567-e89b-12d3-a456-426614174000',
    evidence_count: 5,
    findings_count: 1,
    created_at: '2024-01-10T08:00:00Z',
    updated_at: '2024-01-17T09:00:00Z',
  },
  {
    id: 'case-3',
    case_id: 'case-3',
    case_number: 'HR-POLICY-0001',
    scope_code: 'HR',
    case_type: 'POLICY',
    status: 'CLOSED',
    severity: 'LOW',
    title: 'Policy Violation Review',
    summary: 'Employee policy violation - resolved',
    description: 'Case closed with corrective action.',
    subject_user: 'jane.smith',
    subject_computer: null,
    owner_id: '123e4567-e89b-12d3-a456-426614174000',
    evidence_count: 2,
    findings_count: 1,
    created_at: '2024-01-05T12:00:00Z',
    updated_at: '2024-01-12T16:00:00Z',
  },
];

// Mock evidence
const mockEvidence = [
  {
    id: 'evidence-1',
    case_id: 'case-1',
    file_name: 'screenshot.png',
    file_path: 'cases/FIN-USB-0001/screenshot.png',
    file_size: 245678,
    mime_type: 'image/png',
    file_hash: 'sha256:abc123',
    description: 'Screenshot of USB activity',
    uploaded_by: '123e4567-e89b-12d3-a456-426614174000',
    uploaded_at: '2024-01-15T11:00:00Z',
  },
];

// Mock findings
const mockFindings = [
  {
    id: 'finding-1',
    case_id: 'case-1',
    title: 'Unauthorized Data Transfer',
    description: 'Employee transferred sensitive data to USB drive',
    severity: 'HIGH',
    evidence_ids: ['evidence-1'],
    created_by: '123e4567-e89b-12d3-a456-426614174000',
    created_at: '2024-01-15T14:00:00Z',
    updated_at: '2024-01-15T14:00:00Z',
  },
];

// Mock timeline
const mockTimeline = [
  {
    id: 'timeline-1',
    case_id: 'case-1',
    event_time: '2024-01-15T09:00:00Z',
    event_type: 'CREATED',
    description: 'Case created',
    source: 'system',
    created_by: '123e4567-e89b-12d3-a456-426614174000',
    created_at: '2024-01-15T09:00:00Z',
  },
];

export const casesHandlers = [
  // List cases
  http.get(`${API_BASE}/cases`, ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const severity = url.searchParams.get('severity');
    const page = parseInt(url.searchParams.get('page') || '1');
    const pageSize = parseInt(url.searchParams.get('page_size') || '20');

    let filtered = [...mockCases];

    if (status) {
      filtered = filtered.filter(c => c.status === status);
    }
    if (severity) {
      filtered = filtered.filter(c => c.severity === severity);
    }

    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    const items = filtered.slice(start, end);

    return HttpResponse.json({
      items,
      total: filtered.length,
      page,
      page_size: pageSize,
    });
  }),

  // Get single case
  http.get(`${API_BASE}/cases/:caseId`, ({ params }) => {
    const { caseId } = params;
    const foundCase = mockCases.find(c => c.id === caseId || c.case_number === caseId);

    if (!foundCase) {
      return HttpResponse.json(
        { detail: 'Case not found' },
        { status: 404 }
      );
    }

    return HttpResponse.json(foundCase);
  }),

  // Create case
  http.post(`${API_BASE}/cases`, async ({ request }) => {
    const data = await request.json() as Record<string, unknown>;
    const newCase = {
      id: `case-${Date.now()}`,
      case_id: `case-${Date.now()}`,
      case_number: `${data.scope_code}-${data.case_type}-${String(mockCases.length + 1).padStart(4, '0')}`,
      ...data,
      owner_id: '123e4567-e89b-12d3-a456-426614174000',
      evidence_count: 0,
      findings_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    return HttpResponse.json(newCase, { status: 201 });
  }),

  // Update case
  http.patch(`${API_BASE}/cases/:caseId`, async ({ params, request }) => {
    const { caseId } = params;
    const data = await request.json() as Record<string, unknown>;
    const foundCase = mockCases.find(c => c.id === caseId);

    if (!foundCase) {
      return HttpResponse.json(
        { detail: 'Case not found' },
        { status: 404 }
      );
    }

    const updatedCase = { ...foundCase, ...data, updated_at: new Date().toISOString() };
    return HttpResponse.json(updatedCase);
  }),

  // Delete case
  http.delete(`${API_BASE}/cases/:caseId`, ({ params }) => {
    const { caseId } = params;
    const foundCase = mockCases.find(c => c.id === caseId);

    if (!foundCase) {
      return HttpResponse.json(
        { detail: 'Case not found' },
        { status: 404 }
      );
    }

    return HttpResponse.json({ message: 'Case deleted successfully' });
  }),

  // Get case evidence
  http.get(`${API_BASE}/cases/:caseId/evidence`, ({ params }) => {
    const { caseId } = params;
    const evidence = mockEvidence.filter(e => e.case_id === caseId);

    return HttpResponse.json({
      items: evidence,
      total: evidence.length,
    });
  }),

  // Get case findings
  http.get(`${API_BASE}/cases/:caseId/findings`, ({ params }) => {
    const { caseId } = params;
    const findings = mockFindings.filter(f => f.case_id === caseId);

    return HttpResponse.json({
      items: findings,
      total: findings.length,
    });
  }),

  // Get case timeline
  http.get(`${API_BASE}/cases/:caseId/timeline`, ({ params }) => {
    const { caseId } = params;
    const timeline = mockTimeline.filter(t => t.case_id === caseId);

    return HttpResponse.json({
      items: timeline,
      total: timeline.length,
    });
  }),
];
