import { Page, Locator, expect } from '@playwright/test';

/**
 * Page Object Model for Case List page.
 */
export class CaseListPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly searchInput: Locator;
  readonly statusFilter: Locator;
  readonly severityFilter: Locator;
  readonly newCaseButton: Locator;
  readonly caseTable: Locator;
  readonly emptyState: Locator;
  readonly loadingSpinner: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1:has-text("Cases")');
    this.searchInput = page.locator('input[placeholder*="Search"]');
    this.statusFilter = page.locator('select').nth(0);
    this.severityFilter = page.locator('select').nth(1);
    this.newCaseButton = page.locator('a:has-text("New Case")');
    this.caseTable = page.locator('table');
    this.emptyState = page.locator('text=No cases found');
    this.loadingSpinner = page.locator('.animate-spin');
  }

  /**
   * Navigate to case list.
   */
  async goto() {
    await this.page.goto('/cases');
  }

  /**
   * Verify case list is loaded.
   */
  async expectToBeVisible() {
    await expect(this.pageTitle).toBeVisible();
    await expect(this.searchInput).toBeVisible();
  }

  /**
   * Wait for cases to load (loading spinner to disappear).
   */
  async waitForCasesToLoad() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 10000 });
  }

  /**
   * Search for cases.
   */
  async search(query: string) {
    await this.searchInput.fill(query);
    // Wait for debounced search
    await this.page.waitForTimeout(500);
  }

  /**
   * Filter by status.
   */
  async filterByStatus(status: string) {
    await this.statusFilter.selectOption(status);
  }

  /**
   * Filter by severity.
   */
  async filterBySeverity(severity: string) {
    await this.severityFilter.selectOption(severity);
  }

  /**
   * Click on a case by case ID.
   */
  async openCase(caseId: string) {
    await this.page.locator(`text=${caseId}`).click();
  }

  /**
   * Get all visible case IDs.
   */
  async getVisibleCaseIds(): Promise<string[]> {
    await this.waitForCasesToLoad();
    const rows = this.caseTable.locator('tbody tr');
    const count = await rows.count();
    const caseIds: string[] = [];
    for (let i = 0; i < count; i++) {
      const text = await rows.nth(i).locator('td').first().textContent();
      if (text) caseIds.push(text.trim());
    }
    return caseIds;
  }

  /**
   * Navigate to create new case.
   */
  async goToNewCase() {
    await this.newCaseButton.click();
    await this.page.waitForURL('/cases/new');
  }
}
