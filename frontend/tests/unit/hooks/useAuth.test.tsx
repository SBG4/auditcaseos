/**
 * Unit tests for useAuth hook.
 *
 * Tests cover:
 * - Initial state
 * - Login functionality
 * - Logout functionality
 * - Token persistence
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider, useAuth } from '../../../src/context/AuthContext';
import { server } from '../../setup/msw/server';
import { http, HttpResponse } from 'msw';

// Wrapper component with all required providers
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>{children}</AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    );
  };
};

describe('useAuth', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('initial state', () => {
    it('returns null user when not authenticated', async () => {
      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      // Wait for loading to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.user).toBe(null);
      expect(result.current.isAuthenticated).toBe(false);
    });

    it('shows loading state when token exists', async () => {
      // With a token, it should show loading while fetching /me
      localStorage.setItem('access_token', 'test-token');

      // Add delay to see loading state
      server.use(
        http.get('/api/v1/auth/me', async () => {
          await new Promise((r) => setTimeout(r, 50));
          return HttpResponse.json({
            id: '123',
            email: 'test@example.com',
            role: 'auditor',
          });
        })
      );

      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      // Initially should be loading
      expect(result.current.isLoading).toBe(true);

      // Wait for loading to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });
  });

  describe('login', () => {
    it('stores token in localStorage on successful login', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => {
          return HttpResponse.json({
            access_token: 'test-jwt-token',
            token_type: 'bearer',
            id: '123',
            email: 'test@example.com',
            role: 'auditor',
          });
        })
      );

      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.login({
          username: 'test@example.com',
          password: 'password',
        });
      });

      expect(localStorage.getItem('access_token')).toBe('test-jwt-token');
    });

    it('sets user after successful login', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => {
          return HttpResponse.json({
            access_token: 'test-jwt-token',
            token_type: 'bearer',
            id: '123',
            email: 'test@example.com',
            role: 'auditor',
            full_name: 'Test User',
          });
        })
      );

      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.login({
          username: 'test@example.com',
          password: 'password',
        });
      });

      expect(result.current.user).not.toBeNull();
      expect(result.current.user?.email).toBe('test@example.com');
      expect(result.current.isAuthenticated).toBe(true);
    });

    it('throws error on failed login', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => {
          return HttpResponse.json(
            { detail: 'Invalid credentials' },
            { status: 401 }
          );
        })
      );

      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await expect(
        act(async () => {
          await result.current.login({
            username: 'wrong@example.com',
            password: 'wrongpass',
          });
        })
      ).rejects.toThrow();
    });
  });

  describe('token persistence', () => {
    it('restores user from token on mount', async () => {
      // Set token in localStorage before rendering
      localStorage.setItem('access_token', 'existing-token');

      server.use(
        http.get('/api/v1/auth/me', () => {
          return HttpResponse.json({
            id: '123',
            email: 'restored@example.com',
            role: 'admin',
            full_name: 'Restored User',
          });
        })
      );

      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.user).not.toBeNull();
      expect(result.current.user?.email).toBe('restored@example.com');
      expect(result.current.isAuthenticated).toBe(true);
    });

    it('clears token if /me request fails', async () => {
      localStorage.setItem('access_token', 'expired-token');

      server.use(
        http.get('/api/v1/auth/me', () => {
          return HttpResponse.json(
            { detail: 'Token expired' },
            { status: 401 }
          );
        })
      );

      const { result } = renderHook(() => useAuth(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(localStorage.getItem('access_token')).toBe(null);
      expect(result.current.user).toBe(null);
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe('context requirement', () => {
    it('throws error when used outside AuthProvider', () => {
      // Render without AuthProvider
      const wrapper = ({ children }: { children: ReactNode }) => (
        <BrowserRouter>{children}</BrowserRouter>
      );

      expect(() => {
        renderHook(() => useAuth(), { wrapper });
      }).toThrow('useAuth must be used within an AuthProvider');
    });
  });
});
