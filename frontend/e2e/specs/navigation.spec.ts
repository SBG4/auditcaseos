import { test, expect } from '@playwright/test';
import { loginAs } from '../pages/login.page';

/**
 * E2E Tests for Navigation
 *
 * Tests the main navigation and sidebar functionality.
 */
test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test.describe('Sidebar', () => {
    test('should have Dashboard link', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('nav a:has-text("Dashboard")')).toBeVisible();
    });

    test('should have Cases link', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('nav a:has-text("Cases")')).toBeVisible();
    });

    test('should have Reports link', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('nav a:has-text("Reports")')).toBeVisible();
    });

    test('should have Analytics link', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('nav a:has-text("Analytics")')).toBeVisible();
    });

    test('should navigate to Cases', async ({ page }) => {
      await page.goto('/');
      await page.locator('nav a:has-text("Cases")').click();
      await expect(page).toHaveURL('/cases');
    });

    test('should navigate to Reports', async ({ page }) => {
      await page.goto('/');
      await page.locator('nav a:has-text("Reports")').click();
      await expect(page).toHaveURL('/reports');
    });

    test('should navigate to Analytics', async ({ page }) => {
      await page.goto('/');
      await page.locator('nav a:has-text("Analytics")').click();
      await expect(page).toHaveURL('/analytics');
    });
  });

  test.describe('Header', () => {
    test('should show search bar', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('header input[placeholder*="Search"]')).toBeVisible();
    });

    test('should show user menu', async ({ page }) => {
      await page.goto('/');
      // Look for user menu button (contains user avatar icon)
      await expect(page.locator('header .relative.group > button')).toBeVisible();
    });
  });
});
