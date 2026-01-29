import { Page, Locator } from '@playwright/test';

/**
 * Page Object Model for Dashboard Page
 * 中文注释: 仪表板页面的页面对象模型
 */
export class DashboardPage {
  readonly page: Page;
  readonly manuscriptList: Locator;
  readonly manuscriptItems: Locator;
  readonly pendingCount: Locator;
  readonly approvedCount: Locator;
  readonly rejectedCount: Locator;

  constructor(page: Page) {
    this.page = page;
    this.manuscriptList = page.locator('[data-testid="manuscript-list"]');
    this.manuscriptItems = page.locator('[data-testid="manuscript-item"]');
    this.pendingCount = page.locator('[data-testid="pending-count"]');
    this.approvedCount = page.locator('[data-testid="approved-count"]');
    this.rejectedCount = page.locator('[data-testid="rejected-count"]');
  }

  /**
   * Navigate to dashboard page
   * 中文注释: 导航到仪表板页面
   */
  async navigate(): Promise<void> {
    await this.page.goto('/dashboard');
  }

  /**
   * Check if manuscript list is visible
   * 中文注释: 检查稿件列表是否可见
   */
  async isManuscriptListVisible(): Promise<boolean> {
    return await this.manuscriptList.isVisible();
  }

  /**
   * Get manuscript count
   * 中文注释: 获取稿件数量
   */
  async getManuscriptCount(): Promise<number> {
    return await this.manuscriptItems.count();
  }

  /**
   * Get pending manuscript count
   * 中文注释: 获取待处理稿件数量
   */
  async getPendingCount(): Promise<number> {
    const text = await this.pendingCount.textContent();
    return text ? parseInt(text) : 0;
  }

  /**
   * Click on a manuscript item
   * 中文注释: 点击稿件项
   */
  async clickManuscript(index: number = 0): Promise<void> {
    await this.manuscriptItems.nth(index).click();
  }

  /**
   * Check if dashboard is loaded
   * 中文注释: 检查仪表板是否加载完成
   */
  async isDashboardLoaded(): Promise<boolean> {
    return await this.manuscriptList.isVisible();
  }
}
