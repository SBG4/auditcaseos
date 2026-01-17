import { test, expect } from '@playwright/test';
import { LoginPage, loginAs } from '../pages/login.page';
import { DashboardPage } from '../pages/dashboard.page';

/**
 * E2E Tests for Authentication Flow
 *
 * Tests critical user journeys:
 * 1. Login with valid credentials
 * 2. Login with invalid credentials
 * 3. Logout
 * 4. Protected route redirect
 */
test.describe('Authentication', () => {
  test.describe('Login', () => {
    test('should display login page', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.expectToBeVisible();
    });

    test('should login successfully with valid credentials', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('admin@example.com', 'admin123');
      await loginPage.expectLoginSuccess();
    });

    test('should show error with invalid credentials', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('admin@example.com', 'wrongpassword');
      await loginPage.expectError('Invalid');
    });

    test('should show error with non-existent user', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('nonexistent@example.com', 'password123');
      await loginPage.expectError('Invalid');
    });
  });

  test.describe('Protected Routes', () => {
    test('should redirect to login when not authenticated', async ({ page }) => {
      // Try to access dashboard without logging in
      await page.goto('/');

      // Should redirect to login
      await expect(page).toHaveURL(/\/login/);
    });

    test('should redirect to login when accessing cases', async ({ page }) => {
      await page.goto('/cases');
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe('Session', () => {
    test('should persist login across page refresh', async ({ page }) => {
      // Login first
      await loginAs(page);

      // Refresh the page
      await page.reload();

      // Should still be logged in (on dashboard)
      const dashboard = new DashboardPage(page);
      await dashboard.expectToBeVisible();
    });

    test('should logout successfully', async ({ page }) => {
      // Login first
      await loginAs(page);

      // Find and click sign out button (in dropdown menu)
      await page.locator('button:has-text("Sign out")').click();

      // Should be redirected to login
      await expect(page).toHaveURL(/\/login/);
    });
  });
});
