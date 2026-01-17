/**
 * MSW handlers for users API endpoints.
 */

import { http, HttpResponse } from 'msw';

const API_BASE = '/api/v1';

// Mock users data
export const mockUsers = [
  {
    id: '123e4567-e89b-12d3-a456-426614174000',
    username: 'admin',
    email: 'admin@example.com',
    full_name: 'Admin User',
    role: 'admin',
    department: 'IT',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: '123e4567-e89b-12d3-a456-426614174001',
    username: 'auditor1',
    email: 'auditor1@example.com',
    full_name: 'First Auditor',
    role: 'auditor',
    department: 'Security',
    is_active: true,
    created_at: '2024-01-02T00:00:00Z',
  },
  {
    id: '123e4567-e89b-12d3-a456-426614174002',
    username: 'viewer1',
    email: 'viewer1@example.com',
    full_name: 'First Viewer',
    role: 'viewer',
    department: 'Legal',
    is_active: true,
    created_at: '2024-01-03T00:00:00Z',
  },
];

export const usersHandlers = [
  // List users (admin only)
  http.get(`${API_BASE}/auth/users`, ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const pageSize = parseInt(url.searchParams.get('page_size') || '20');

    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    const items = mockUsers.slice(start, end);

    return HttpResponse.json({
      items,
      total: mockUsers.length,
      page,
      page_size: pageSize,
    });
  }),

  // Get single user
  http.get(`${API_BASE}/auth/users/:userId`, ({ params }) => {
    const { userId } = params;
    const user = mockUsers.find(u => u.id === userId);

    if (!user) {
      return HttpResponse.json(
        { detail: 'User not found' },
        { status: 404 }
      );
    }

    return HttpResponse.json(user);
  }),

  // Update user (admin only)
  http.patch(`${API_BASE}/auth/users/:userId`, async ({ params, request }) => {
    const { userId } = params;
    const data = await request.json() as Record<string, unknown>;
    const user = mockUsers.find(u => u.id === userId);

    if (!user) {
      return HttpResponse.json(
        { detail: 'User not found' },
        { status: 404 }
      );
    }

    const updatedUser = { ...user, ...data };
    return HttpResponse.json(updatedUser);
  }),

  // Deactivate user (admin only)
  http.delete(`${API_BASE}/auth/users/:userId`, ({ params }) => {
    const { userId } = params;
    const user = mockUsers.find(u => u.id === userId);

    if (!user) {
      return HttpResponse.json(
        { detail: 'User not found' },
        { status: 404 }
      );
    }

    return HttpResponse.json({ message: 'User deactivated successfully' });
  }),
];
