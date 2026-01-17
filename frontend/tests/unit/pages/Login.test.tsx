/**
 * Unit tests for Login page.
 *
 * Tests cover:
 * - Rendering of login form
 * - Form validation
 * - Successful login flow
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, userEvent, waitFor } from '../../setup/test-utils';
import Login from '../../../src/pages/Login';
import { server } from '../../setup/msw/server';
import { http, HttpResponse } from 'msw';

describe('Login', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('rendering', () => {
    it('renders the login form', () => {
      render(<Login />);

      expect(screen.getByText('AuditCaseOS')).toBeInTheDocument();
      expect(screen.getByText('Sign in to your account')).toBeInTheDocument();
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    it('shows default credentials hint', () => {
      render(<Login />);

      expect(screen.getByText(/admin@example.com/)).toBeInTheDocument();
    });

    it('has email input as required', () => {
      render(<Login />);

      const emailInput = screen.getByLabelText(/email address/i);
      expect(emailInput).toBeRequired();
    });

    it('has password input as required', () => {
      render(<Login />);

      const passwordInput = screen.getByLabelText(/password/i);
      expect(passwordInput).toBeRequired();
    });
  });

  describe('form interaction', () => {
    it('allows typing in email field', async () => {
      render(<Login />);

      const emailInput = screen.getByLabelText(/email address/i);
      await userEvent.type(emailInput, 'test@example.com');

      expect(emailInput).toHaveValue('test@example.com');
    });

    it('allows typing in password field', async () => {
      render(<Login />);

      const passwordInput = screen.getByLabelText(/password/i);
      await userEvent.type(passwordInput, 'mypassword');

      expect(passwordInput).toHaveValue('mypassword');
    });

    it('password field is type password', () => {
      render(<Login />);

      const passwordInput = screen.getByLabelText(/password/i);
      expect(passwordInput).toHaveAttribute('type', 'password');
    });
  });

  describe('form submission', () => {
    it('shows loading state when submitting', async () => {
      // Add a delay to the handler to see loading state
      server.use(
        http.post('/api/v1/auth/login', async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json({
            access_token: 'mock-token',
            token_type: 'bearer',
            id: '123',
            email: 'test@example.com',
            role: 'auditor',
          });
        })
      );

      render(<Login />);

      await userEvent.type(screen.getByLabelText(/email address/i), 'test@example.com');
      await userEvent.type(screen.getByLabelText(/password/i), 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await userEvent.click(submitButton);

      // Button should be disabled during loading
      expect(submitButton).toBeDisabled();
    });

    it('stores token on successful login', async () => {
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

      render(<Login />);

      await userEvent.type(screen.getByLabelText(/email address/i), 'test@example.com');
      await userEvent.type(screen.getByLabelText(/password/i), 'password123');
      await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(localStorage.getItem('access_token')).toBe('test-jwt-token');
      });
    });

    it('shows error message on login failure', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => {
          return HttpResponse.json(
            { detail: 'Invalid username or password' },
            { status: 401 }
          );
        })
      );

      render(<Login />);

      await userEvent.type(screen.getByLabelText(/email address/i), 'wrong@example.com');
      await userEvent.type(screen.getByLabelText(/password/i), 'wrongpassword');
      await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument();
      });
    });

    it('clears error when resubmitting', async () => {
      let callCount = 0;
      server.use(
        http.post('/api/v1/auth/login', () => {
          callCount++;
          if (callCount === 1) {
            return HttpResponse.json(
              { detail: 'Invalid username or password' },
              { status: 401 }
            );
          }
          return HttpResponse.json({
            access_token: 'token',
            token_type: 'bearer',
            id: '123',
            email: 'test@example.com',
            role: 'auditor',
          });
        })
      );

      render(<Login />);

      // First attempt - should fail
      await userEvent.type(screen.getByLabelText(/email address/i), 'test@example.com');
      await userEvent.type(screen.getByLabelText(/password/i), 'wrong');
      await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument();
      });

      // Clear and retry
      await userEvent.clear(screen.getByLabelText(/password/i));
      await userEvent.type(screen.getByLabelText(/password/i), 'correct');
      await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

      // Error should be cleared after submission starts
      await waitFor(() => {
        expect(screen.queryByText(/invalid email or password/i)).not.toBeInTheDocument();
      });
    });
  });
});
