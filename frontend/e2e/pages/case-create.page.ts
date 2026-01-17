import { Page, Locator, expect } from '@playwright/test';

/**
 * Page Object Model for Case Create page.
 */
export class CaseCreatePage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly scopeSelect: Locator;
  readonly typeSelect: Locator;
  readonly titleInput: Locator;
  readonly summaryInput: Locator;
  readonly descriptionInput: Locator;
  readonly severitySelect: Locator;
  readonly submitButton: Locator;
  readonly cancelButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1:has-text("New Case")');
    this.scopeSelect = page.locator('select[name="scope_code"]');
    this.typeSelect = page.locator('select[name="case_type"]');
    this.titleInput = page.locator('input[name="title"]');
    this.summaryInput = page.locator('textarea[name="summary"]');
    this.descriptionInput = page.locator('textarea[name="description"]');
    this.severitySelect = page.locator('select[name="severity"]');
    this.submitButton = page.locator('button[type="submit"]');
    this.cancelButton = page.locator('button:has-text("Cancel")');
    this.errorMessage = page.locator('[role="alert"]');
  }

  /**
   * Navigate to create case page.
   */
  async goto() {
    await this.page.goto('/cases/new');
  }

  /**
   * Verify page is loaded.
   */
  async expectToBeVisible() {
    await expect(this.pageTitle).toBeVisible();
    await expect(this.titleInput).toBeVisible();
  }

  /**
   * Fill in the case form.
   */
  async fillForm(data: {
    scope: string;
    type: string;
    title: string;
    summary?: string;
    description?: string;
    severity?: string;
  }) {
    await this.scopeSelect.selectOption(data.scope);
    await this.typeSelect.selectOption(data.type);
    await this.titleInput.fill(data.title);
    if (data.summary) {
      await this.summaryInput.fill(data.summary);
    }
    if (data.description) {
      await this.descriptionInput.fill(data.description);
    }
    if (data.severity) {
      await this.severitySelect.selectOption(data.severity);
    }
  }

  /**
   * Submit the form.
   */
  async submit() {
    await this.submitButton.click();
  }

  /**
   * Create a case with the given data.
   */
  async createCase(data: {
    scope: string;
    type: string;
    title: string;
    summary?: string;
    description?: string;
    severity?: string;
  }) {
    await this.fillForm(data);
    await this.submit();
  }

  /**
   * Expect error message.
   */
  async expectError(message: string) {
    await expect(this.errorMessage).toBeVisible();
    await expect(this.errorMessage).toContainText(message);
  }

  /**
   * Expect successful creation (redirect to case detail).
   */
  async expectSuccess() {
    // Wait for redirect to case detail page
    await this.page.waitForURL(/\/cases\/[\w-]+$/);
  }
}
