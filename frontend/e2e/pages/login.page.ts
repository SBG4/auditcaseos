import { Page, Locator, expect } from '@playwright/test';

/**
 * Page Object Model for Login page.
 *
 * @see https://playwright.dev/docs/pom
 */
export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;
  readonly pageTitle: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.locator('input[name="username"]');
    this.passwordInput = page.locator('input[name="password"]');
    this.submitButton = page.locator('button[type="submit"]');
    // Error message has bg-red-50 text-red-700 classes
    this.errorMessage = page.locator('.bg-red-50.text-red-700');
    this.pageTitle = page.locator('h2');
  }

  /**
   * Navigate to the login page.
   */
  async goto() {
    await this.page.goto('/login');
  }

  /**
   * Fill in the login form.
   */
  async fillForm(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
  }

  /**
   * Submit the login form.
   */
  async submit() {
    await this.submitButton.click();
  }

  /**
   * Complete login flow.
   */
  async login(email: string, password: string) {
    await this.fillForm(email, password);
    await this.submit();
  }

  /**
   * Verify we're on the login page.
   */
  async expectToBeVisible() {
    await expect(this.pageTitle).toContainText('Sign in to your account');
    await expect(this.emailInput).toBeVisible();
    await expect(this.passwordInput).toBeVisible();
  }

  /**
   * Verify error message is shown.
   */
  async expectError(message: string) {
    await expect(this.errorMessage).toBeVisible();
    await expect(this.errorMessage).toContainText(message);
  }

  /**
   * Verify successful login (redirected to dashboard).
   */
  async expectLoginSuccess() {
    // Wait for redirect away from login page
    await this.page.waitForURL((url) => !url.pathname.includes('/login'), {
      timeout: 15000,
    });
    // Wait for dashboard to be visible
    await expect(this.page.locator('h1:has-text("Dashboard")')).toBeVisible({
      timeout: 10000,
    });
  }
}

/**
 * Helper function to login and return to a page.
 * Can be used in test setup.
 */
export async function loginAs(
  page: Page,
  email = 'admin@example.com',
  password = 'admin123'
) {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login(email, password);
  await loginPage.expectLoginSuccess();
}
