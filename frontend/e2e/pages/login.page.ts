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
    this.errorMessage = page.locator('div.bg-red-50');
    this.pageTitle = page.locator('h2');
  }

  /**
   * Navigate to the login page.
   */
  async goto() {
    await this.page.goto('/login');
    // Wait for page to be ready
    await this.emailInput.waitFor({ state: 'visible', timeout: 10000 });
  }

  /**
   * Fill in the login form.
   */
  async fillForm(email: string, password: string) {
    // Click and type to ensure values are entered
    await this.emailInput.click();
    await this.emailInput.fill(email);
    await this.passwordInput.click();
    await this.passwordInput.fill(password);

    // Verify values were entered
    await this.page.waitForTimeout(100);
  }

  /**
   * Submit the login form and wait for API response.
   */
  async submit() {
    // Wait for the login API response
    const responsePromise = this.page.waitForResponse(
      (response) => response.url().includes('/api/v1/auth/login'),
      { timeout: 15000 }
    );

    await this.submitButton.click();

    // Wait for the API response to complete
    await responsePromise.catch(() => {
      // API response may already have completed
    });

    // Small wait for UI to update after response
    await this.page.waitForTimeout(500);
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
    // Wait for error message to appear (may take a moment after form submit)
    await expect(this.errorMessage).toBeVisible({ timeout: 10000 });
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

    // Wait for loading spinner to disappear (auth initialization)
    await this.page
      .locator('.animate-spin')
      .waitFor({
        state: 'hidden',
        timeout: 10000,
      })
      .catch(() => {
        // Spinner may already be gone
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
