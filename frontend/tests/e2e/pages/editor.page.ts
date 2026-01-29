import { Page, Locator } from '@playwright/test';

/**
 * Page Object Model for Editor Dashboard Page
 * 中文注释: 编辑仪表板页面的页面对象模型
 */
export class EditorPage {
  readonly page: Page;
  readonly pendingManuscripts: Locator;
  readonly assignReviewerBtn: Locator;
  readonly reviewerOptions: Locator;
  readonly confirmAssignment: Locator;
  readonly successToast: Locator;
  readonly manuscriptStatus: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pendingManuscripts = page.locator('[data-testid="pending-manuscripts"]');
    this.assignReviewerBtn = page.locator('[data-testid="assign-reviewer-btn"]');
    this.reviewerOptions = page.locator('[data-testid="reviewer-option"]');
    this.confirmAssignment = page.locator('[data-testid="confirm-assignment"]');
    this.successToast = page.locator('[data-testid="success-toast"]');
    this.manuscriptStatus = page.locator('[data-testid="manuscript-status"]');
  }

  /**
   * Navigate to editor dashboard
   * 中文注释: 导航到编辑仪表板
   */
  async navigate(): Promise<void> {
    await this.page.goto('/editor/dashboard');
  }

  /**
   * Check if pending manuscripts list is visible
   * 中文注释: 检查待处理稿件列表是否可见
   */
  async isPendingManuscriptsVisible(): Promise<boolean> {
    return await this.pendingManuscripts.isVisible();
  }

  /**
   * Get pending manuscript count
   * 中文注释: 获取待处理稿件数量
   */
  async getPendingCount(): Promise<number> {
    return await this.pendingManuscripts.count();
  }

  /**
   * Assign reviewer to first manuscript
   * 中文注释: 为第一个稿件分配审稿人
   */
  async assignReviewerToFirst(): Promise<void> {
    await this.assignReviewerBtn.first().click();
    await this.reviewerOptions.first().click();
    await this.confirmAssignment.click();
  }

  /**
   * Get success message
   * 中文注释: 获取成功消息
   */
  async getSuccessMessage(): Promise<string> {
    return await this.successToast.textContent() || '';
  }

  /**
   * Get manuscript status
   * 中文注释: 获取稿件状态
   */
  async getManuscriptStatus(): Promise<string> {
    return await this.manuscriptStatus.textContent() || '';
  }

  /**
   * Check if editor dashboard is loaded
   * 中文注释: 检查编辑仪表板是否加载完成
   */
  async isEditorDashboardLoaded(): Promise<boolean> {
    return await this.pendingManuscripts.isVisible();
  }
}
