/**
 * MSW handlers for auth API endpoints.
 */

import { http, HttpResponse } from 'msw';

const API_BASE = '/api/v1';

// Mock user data
const mockUser = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  username: 'testuser',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'auditor',
  department: 'IT',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
};

const mockToken = {
  access_token: 'mock-jwt-token',
  token_type: 'bearer',
  ...mockUser,
};

export const authHandlers = [
  // Login
  http.post(`${API_BASE}/auth/login`, async ({ request }) => {
    const formData = await request.formData();
    const username = formData.get('username');
    const password = formData.get('password');

    if (username === 'testuser' && password === 'TestPassword123!') {
      return HttpResponse.json(mockToken);
    }

    return HttpResponse.json(
      { detail: 'Invalid username or password' },
      { status: 401 }
    );
  }),

  // Get current user
  http.get(`${API_BASE}/auth/me`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      );
    }

    return HttpResponse.json(mockUser);
  }),

  // Register (admin only)
  http.post(`${API_BASE}/auth/register`, async ({ request }) => {
    const data = await request.json() as Record<string, unknown>;
    const newUser = {
      id: '123e4567-e89b-12d3-a456-426614174001',
      username: data.username,
      email: data.email,
      full_name: data.full_name,
      role: data.role || 'viewer',
      department: data.department,
      is_active: true,
      created_at: new Date().toISOString(),
    };

    return HttpResponse.json(newUser, { status: 201 });
  }),

  // Change password
  http.post(`${API_BASE}/auth/change-password`, async ({ request }) => {
    const data = await request.json() as Record<string, unknown>;

    if (data.current_password !== 'TestPassword123!') {
      return HttpResponse.json(
        { detail: 'Current password is incorrect' },
        { status: 400 }
      );
    }

    return HttpResponse.json({ message: 'Password changed successfully' });
  }),

  // Logout
  http.post(`${API_BASE}/auth/logout`, () => {
    return HttpResponse.json({ message: 'Logged out successfully' });
  }),
];
