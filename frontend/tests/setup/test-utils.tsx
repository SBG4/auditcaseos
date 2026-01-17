/**
 * Custom render function and test utilities.
 *
 * Wraps components with all required providers for testing:
 * - React Query
 * - Router
 * - Auth Context
 *
 * Source: https://testing-library.com/docs/react-testing-library/setup
 */

import React, { ReactElement } from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../../src/context/AuthContext';

// Create a new QueryClient for each test
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

interface WrapperProps {
  children: React.ReactNode;
}

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  route?: string;
  initialEntries?: string[];
}

/**
 * Wrapper component with all providers for testing.
 */
const AllTheProviders = ({ children }: WrapperProps): ReactElement => {
  const queryClient = createTestQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>{children}</AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

/**
 * Custom render function with all providers.
 */
const customRender = (
  ui: ReactElement,
  options?: CustomRenderOptions
): RenderResult => {
  const { route = '/', initialEntries = [route], ...renderOptions } = options || {};

  // Set initial route for BrowserRouter
  window.history.pushState({}, 'Test page', route);

  return render(ui, { wrapper: AllTheProviders, ...renderOptions });
};

/**
 * Render with MemoryRouter for testing specific routes.
 */
const renderWithMemoryRouter = (
  ui: ReactElement,
  { initialEntries = ['/'], ...options }: CustomRenderOptions = {}
): RenderResult => {
  const queryClient = createTestQueryClient();

  const Wrapper = ({ children }: WrapperProps): ReactElement => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <AuthProvider>{children}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );

  return render(ui, { wrapper: Wrapper, ...options });
};

// Re-export everything from testing-library
export * from '@testing-library/react';

// Override render with custom render
export { customRender as render, renderWithMemoryRouter };

// Export user-event with setup
export { default as userEvent } from '@testing-library/user-event';

// Helper for waiting on async operations
export const waitForLoadingToFinish = (): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, 0));

// Mock localStorage
export const mockLocalStorage = () => {
  const storage: Record<string, string> = {};

  return {
    getItem: (key: string): string | null => storage[key] || null,
    setItem: (key: string, value: string): void => {
      storage[key] = value;
    },
    removeItem: (key: string): void => {
      delete storage[key];
    },
    clear: (): void => {
      Object.keys(storage).forEach((key) => delete storage[key]);
    },
  };
};

// Mock authenticated user
export const mockAuthenticatedUser = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  username: 'testuser',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'auditor',
  department: 'IT',
  is_active: true,
};

// Mock JWT token
export const mockToken = 'mock-jwt-token-for-testing';

// Helper to set up authenticated state
export const setupAuthenticatedState = (): void => {
  localStorage.setItem('token', mockToken);
  localStorage.setItem('user', JSON.stringify(mockAuthenticatedUser));
};

// Helper to clear auth state
export const clearAuthState = (): void => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
};
