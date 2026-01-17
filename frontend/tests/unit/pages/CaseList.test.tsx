/**
 * Unit tests for CaseList page.
 *
 * Tests cover:
 * - Rendering of case list
 * - Loading state
 * - Search functionality
 * - Status filter
 * - Severity filter
 * - Empty states
 */

import { describe, it, expect } from 'vitest';
import { render, screen, waitFor, userEvent } from '../../setup/test-utils';
import CaseList from '../../../src/pages/CaseList';
import { server } from '../../setup/msw/server';
import { http, HttpResponse } from 'msw';

describe('CaseList', () => {
  describe('rendering', () => {
    it('shows page title', () => {
      render(<CaseList />);

      expect(screen.getByText('Cases')).toBeInTheDocument();
      expect(screen.getByText('Manage and track all audit cases')).toBeInTheDocument();
    });

    it('shows New Case button', () => {
      render(<CaseList />);

      expect(screen.getByRole('button', { name: /new case/i })).toBeInTheDocument();
    });

    it('shows search input', () => {
      render(<CaseList />);

      expect(screen.getByPlaceholderText('Search cases...')).toBeInTheDocument();
    });

    it('shows status filter dropdown', () => {
      render(<CaseList />);

      expect(screen.getByDisplayValue('All Status')).toBeInTheDocument();
    });

    it('shows severity filter dropdown', () => {
      render(<CaseList />);

      expect(screen.getByDisplayValue('All Severity')).toBeInTheDocument();
    });
  });

  describe('loading state', () => {
    it('shows loading spinner while fetching data', () => {
      render(<CaseList />);

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('case list', () => {
    it('displays cases in table', async () => {
      render(<CaseList />);

      await waitFor(() => {
        expect(screen.getByText('Unauthorized USB Device Usage')).toBeInTheDocument();
        expect(screen.getByText('Phishing Attack Investigation')).toBeInTheDocument();
        expect(screen.getByText('Policy Violation Review')).toBeInTheDocument();
      });
    });

    it('shows case numbers', async () => {
      render(<CaseList />);

      await waitFor(() => {
        expect(screen.getByText('FIN-USB-0001')).toBeInTheDocument();
        expect(screen.getByText('IT-EMAIL-0001')).toBeInTheDocument();
        expect(screen.getByText('HR-POLICY-0001')).toBeInTheDocument();
      });
    });

    it('shows table headers', async () => {
      render(<CaseList />);

      await waitFor(() => {
        expect(screen.getByText('Case')).toBeInTheDocument();
        expect(screen.getByText('Status')).toBeInTheDocument();
        expect(screen.getByText('Severity')).toBeInTheDocument();
        expect(screen.getByText('Created')).toBeInTheDocument();
        expect(screen.getByText('Updated')).toBeInTheDocument();
      });
    });
  });

  describe('search functionality', () => {
    it('filters cases by title', async () => {
      render(<CaseList />);

      await waitFor(() => {
        expect(screen.getByText('Unauthorized USB Device Usage')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search cases...');
      await userEvent.type(searchInput, 'USB');

      // Only USB case should be visible
      expect(screen.getByText('Unauthorized USB Device Usage')).toBeInTheDocument();
      expect(screen.queryByText('Phishing Attack Investigation')).not.toBeInTheDocument();
    });

    it('filters cases by case number', async () => {
      render(<CaseList />);

      await waitFor(() => {
        expect(screen.getByText('FIN-USB-0001')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search cases...');
      await userEvent.type(searchInput, 'IT-EMAIL');

      // Only IT-EMAIL case should be visible
      expect(screen.getByText('IT-EMAIL-0001')).toBeInTheDocument();
      expect(screen.queryByText('FIN-USB-0001')).not.toBeInTheDocument();
    });

    it('search is case insensitive', async () => {
      render(<CaseList />);

      await waitFor(() => {
        expect(screen.getByText('Unauthorized USB Device Usage')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search cases...');
      await userEvent.type(searchInput, 'usb');

      expect(screen.getByText('Unauthorized USB Device Usage')).toBeInTheDocument();
    });
  });

  describe('empty states', () => {
    it('shows message when no cases found', async () => {
      server.use(
        http.get('/api/v1/cases', () => {
          return HttpResponse.json({
            items: [],
            total: 0,
            page: 1,
            page_size: 100,
          });
        })
      );

      render(<CaseList />);

      await waitFor(() => {
        expect(screen.getByText('No cases found')).toBeInTheDocument();
      });
    });

    it('shows create button in empty state', async () => {
      server.use(
        http.get('/api/v1/cases', () => {
          return HttpResponse.json({
            items: [],
            total: 0,
            page: 1,
            page_size: 100,
          });
        })
      );

      render(<CaseList />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create your first case/i })).toBeInTheDocument();
      });
    });
  });

  describe('status filter options', () => {
    it('has all status options', () => {
      render(<CaseList />);

      const statusSelect = screen.getByDisplayValue('All Status');
      expect(statusSelect).toBeInTheDocument();

      // Check options exist
      expect(screen.getByRole('option', { name: 'All Status' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Open' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'In Progress' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Pending Review' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Closed' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Archived' })).toBeInTheDocument();
    });
  });

  describe('severity filter options', () => {
    it('has all severity options', () => {
      render(<CaseList />);

      const severitySelect = screen.getByDisplayValue('All Severity');
      expect(severitySelect).toBeInTheDocument();

      // Check options exist
      expect(screen.getByRole('option', { name: 'All Severity' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Critical' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'High' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Medium' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Low' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Info' })).toBeInTheDocument();
    });
  });

  describe('navigation', () => {
    it('New Case button links to create page', () => {
      render(<CaseList />);

      const newCaseLink = screen.getByRole('link', { name: /new case/i });
      expect(newCaseLink).toHaveAttribute('href', '/cases/new');
    });
  });
});
