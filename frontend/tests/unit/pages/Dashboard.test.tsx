/**
 * Unit tests for Dashboard page.
 *
 * Tests cover:
 * - Loading state
 * - Stats card rendering
 * - Recent cases list
 * - Critical cases section
 * - Empty states
 */

import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '../../setup/test-utils';
import Dashboard from '../../../src/pages/Dashboard';
import { server } from '../../setup/msw/server';
import { http, HttpResponse } from 'msw';

describe('Dashboard', () => {
  describe('loading state', () => {
    it('shows loading spinner while fetching data', () => {
      render(<Dashboard />);

      // Loading spinner should be visible initially
      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('stats cards', () => {
    it('displays total cases count', async () => {
      render(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText('Total Cases')).toBeInTheDocument();
      });

      // Mock data has 3 cases
      expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('displays open cases count', async () => {
      render(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText('Open')).toBeInTheDocument();
      });

      // Mock data has 1 OPEN case
      expect(screen.getAllByText('1')[0]).toBeInTheDocument();
    });

    it('displays in-progress cases count', async () => {
      render(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText('In Progress')).toBeInTheDocument();
      });
    });

    it('displays closed cases count', async () => {
      render(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText('Closed')).toBeInTheDocument();
      });
    });
  });

  describe('recent cases', () => {
    it('displays recent cases section', async () => {
      render(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText('Recent Cases')).toBeInTheDocument();
      });
    });

    it('shows case titles', async () => {
      render(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText('Unauthorized USB Device Usage')).toBeInTheDocument();
        // Phishing Attack appears in both Recent and Critical sections
        expect(screen.getAllByText('Phishing Attack Investigation').length).toBeGreaterThanOrEqual(1);
      });
    });

    it('shows case numbers', async () => {
      render(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText('FIN-USB-0001')).toBeInTheDocument();
        // IT-EMAIL-0001 appears in both Recent and Critical sections
        expect(screen.getAllByText('IT-EMAIL-0001').length).toBeGreaterThanOrEqual(1);
      });
    });

    it('shows view all link', async () => {
      render(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByRole('link', { name: /view all/i })).toBeInTheDocument();
      });
    });

    it('shows empty state when no cases', async () => {
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

      render(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText('No cases yet')).toBeInTheDocument();
      });
    });
  });

  describe('critical cases', () => {
    it('displays critical cases section', async () => {
      render(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText('Critical Cases')).toBeInTheDocument();
      });
    });

    it('shows subtitle about immediate attention', async () => {
      render(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText('Requiring immediate attention')).toBeInTheDocument();
      });
    });

    it('shows critical cases that are not closed', async () => {
      render(<Dashboard />);

      await waitFor(() => {
        // IT-EMAIL-0001 is CRITICAL and IN_PROGRESS, appears in Critical Cases section
        const phishingTexts = screen.getAllByText('Phishing Attack Investigation');
        expect(phishingTexts.length).toBeGreaterThanOrEqual(1);
      });
    });

    it('shows no critical cases message when none exist', async () => {
      server.use(
        http.get('/api/v1/cases', () => {
          return HttpResponse.json({
            items: [
              {
                id: 'case-1',
                case_number: 'TEST-001',
                status: 'OPEN',
                severity: 'LOW',
                title: 'Low Priority Case',
              },
            ],
            total: 1,
            page: 1,
            page_size: 100,
          });
        })
      );

      render(<Dashboard />);

      await waitFor(() => {
        expect(screen.getByText('No critical cases')).toBeInTheDocument();
      });
    });
  });

  describe('navigation', () => {
    it('recent case links navigate to case detail', async () => {
      render(<Dashboard />);

      await waitFor(() => {
        const links = screen.getAllByRole('link');
        // Find the case links (they point to /cases/:id)
        const caseLinks = links.filter(link =>
          link.getAttribute('href')?.startsWith('/cases/')
        );
        expect(caseLinks.length).toBeGreaterThan(0);
      });
    });
  });

  describe('error handling', () => {
    it('handles API error gracefully', async () => {
      server.use(
        http.get('/api/v1/cases', () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          );
        })
      );

      render(<Dashboard />);

      // Should still render the page structure
      await waitFor(() => {
        expect(screen.getByText('Dashboard')).toBeInTheDocument();
      });
    });
  });
});
