import { Page, Locator, expect } from '@playwright/test';

/**
 * Page Object Model for Dashboard page.
 */
export class DashboardPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly totalCasesCard: Locator;
  readonly openCasesCard: Locator;
  readonly inProgressCasesCard: Locator;
  readonly closedCasesCard: Locator;
  readonly recentCasesSection: Locator;
  readonly criticalCasesSection: Locator;
  readonly viewAllLink: Locator;
  readonly newCaseButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1:has-text("Dashboard")');
    this.totalCasesCard = page.locator('text=Total Cases').locator('..');
    this.openCasesCard = page.locator('text=Open').locator('..');
    this.inProgressCasesCard = page.locator('text=In Progress').locator('..');
    this.closedCasesCard = page.locator('text=Closed').locator('..');
    this.recentCasesSection = page.locator('text=Recent Cases').locator('..');
    this.criticalCasesSection = page.locator('text=Critical Cases').locator('..');
    this.viewAllLink = page.locator('a:has-text("View all")');
    this.newCaseButton = page.locator('a:has-text("New Case")');
  }

  /**
   * Navigate to dashboard.
   */
  async goto() {
    await this.page.goto('/');
  }

  /**
   * Verify dashboard is loaded.
   */
  async expectToBeVisible() {
    await expect(this.pageTitle).toBeVisible();
    await expect(this.totalCasesCard).toBeVisible();
  }

  /**
   * Get the total cases count from the stats card.
   */
  async getTotalCasesCount(): Promise<number> {
    const text = await this.totalCasesCard.textContent();
    const match = text?.match(/\d+/);
    return match ? parseInt(match[0], 10) : 0;
  }

  /**
   * Click on a recent case by title.
   */
  async clickRecentCase(title: string) {
    await this.recentCasesSection.locator(`a:has-text("${title}")`).click();
  }

  /**
   * Navigate to the case list via "View all" link.
   */
  async goToAllCases() {
    await this.viewAllLink.click();
    await this.page.waitForURL('/cases');
  }

  /**
   * Navigate to create new case.
   */
  async goToNewCase() {
    await this.newCaseButton.click();
    await this.page.waitForURL('/cases/new');
  }
}
