import { test, expect } from '@playwright/test';
import { loginAs } from '../pages/login.page';
import { DashboardPage } from '../pages/dashboard.page';
import { CaseListPage } from '../pages/case-list.page';
import { CaseCreatePage } from '../pages/case-create.page';

/**
 * E2E Tests for Case Management
 *
 * Tests critical user journeys:
 * 1. Dashboard → View Cases → Open Case
 * 2. Create new case
 * 3. Search and filter cases
 * 4. Edit case details
 */
test.describe('Case Management', () => {
  // Login before each test
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test.describe('Dashboard', () => {
    test('should display dashboard with stats', async ({ page }) => {
      const dashboard = new DashboardPage(page);
      await dashboard.goto();
      await dashboard.expectToBeVisible();
    });

    test('should show recent cases', async ({ page }) => {
      const dashboard = new DashboardPage(page);
      await dashboard.goto();
      await expect(page.locator('text=Recent Cases')).toBeVisible();
    });

    test('should navigate to case list via View All', async ({ page }) => {
      const dashboard = new DashboardPage(page);
      await dashboard.goto();
      await dashboard.goToAllCases();
      await expect(page).toHaveURL('/cases');
    });
  });

  test.describe('Case List', () => {
    test('should display case list', async ({ page }) => {
      const caseList = new CaseListPage(page);
      await caseList.goto();
      await caseList.expectToBeVisible();
    });

    test('should search cases', async ({ page }) => {
      const caseList = new CaseListPage(page);
      await caseList.goto();
      await caseList.waitForCasesToLoad();

      // Search for a term
      await caseList.search('USB');

      // Should filter the results (wait for debounce)
      await page.waitForTimeout(500);
    });

    test('should filter by status', async ({ page }) => {
      const caseList = new CaseListPage(page);
      await caseList.goto();
      await caseList.waitForCasesToLoad();

      // Filter by OPEN status
      await caseList.filterByStatus('OPEN');

      // Wait for filter to apply
      await page.waitForTimeout(500);
    });

    test('should filter by severity', async ({ page }) => {
      const caseList = new CaseListPage(page);
      await caseList.goto();
      await caseList.waitForCasesToLoad();

      // Filter by CRITICAL severity
      await caseList.filterBySeverity('CRITICAL');

      // Wait for filter to apply
      await page.waitForTimeout(500);
    });
  });

  test.describe('Case Creation', () => {
    test('should display create case form', async ({ page }) => {
      const createPage = new CaseCreatePage(page);
      await createPage.goto();
      await createPage.expectToBeVisible();
    });

    test('should create a new case', async ({ page }) => {
      const createPage = new CaseCreatePage(page);
      await createPage.goto();

      await createPage.createCase({
        scope: 'IT',
        type: 'USB',
        title: `E2E Test Case ${Date.now()}`,
        summary: 'Automated test case created by Playwright',
        severity: 'HIGH',
      });

      await createPage.expectSuccess();
    });

    test('should navigate to create case from dashboard', async ({ page }) => {
      const dashboard = new DashboardPage(page);
      await dashboard.goto();
      await dashboard.goToNewCase();

      const createPage = new CaseCreatePage(page);
      await createPage.expectToBeVisible();
    });
  });

  test.describe('Case Detail', () => {
    test('should view case details', async ({ page }) => {
      const caseList = new CaseListPage(page);
      await caseList.goto();
      await caseList.waitForCasesToLoad();

      // Get the first visible case ID
      const caseIds = await caseList.getVisibleCaseIds();
      if (caseIds.length === 0) {
        test.skip();
        return;
      }

      // Click on the first case
      await caseList.openCase(caseIds[0]);

      // Should navigate to case detail
      await expect(page).toHaveURL(/\/cases\//);
      await expect(page.locator('h1')).toBeVisible();
    });
  });
});
