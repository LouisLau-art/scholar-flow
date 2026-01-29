import { Page, Locator } from '@playwright/test';

/**
 * Page Object Model for Submission Page
 * 中文注释: 稿件提交页面的页面对象模型
 */
export class SubmissionPage {
  readonly page: Page;
  readonly fileInput: Locator;
  readonly titleInput: Locator;
  readonly abstractInput: Locator;
  readonly submitButton: Locator;
  readonly successMessage: Locator;
  readonly errorMessage: Locator;
  readonly titleError: Locator;
  readonly abstractError: Locator;

  constructor(page: Page) {
    this.page = page;
    this.fileInput = page.locator('input[type="file"]');
    this.titleInput = page.locator('input[name="title"]');
    this.abstractInput = page.locator('textarea[name="abstract"]');
    this.submitButton = page.locator('button[type="submit"]');
    this.successMessage = page.locator('[data-testid="success-toast"]');
    this.errorMessage = page.locator('[data-testid="error-toast"]');
    this.titleError = page.locator('[data-testid="title-error"]');
    this.abstractError = page.locator('[data-testid="abstract-error"]');
  }

  /**
   * Navigate to submission page
   * 中文注释: 导航到提交页面
   */
  async navigate(): Promise<void> {
    await this.page.goto('/submit');
  }

  /**
   * Upload PDF file
   * 中文注释: 上传PDF文件
   */
  async uploadPDF(filePath: string): Promise<void> {
    await this.fileInput.setInputFiles(filePath);
  }

  /**
   * Fill title field
   * 中文注释: 填写标题字段
   */
  async fillTitle(title: string): Promise<void> {
    await this.titleInput.fill(title);
  }

  /**
   * Fill abstract field
   * 中文注释: 填写摘要字段
   */
  async fillAbstract(abstract: string): Promise<void> {
    await this.abstractInput.fill(abstract);
  }

  /**
   * Click submit button
   * 中文注释: 点击提交按钮
   */
  async submit(): Promise<void> {
    await this.submitButton.click();
  }

  /**
   * Perform complete submission flow
   * 中文注释: 执行完整的提交流程
   */
  async submitManuscript(filePath: string, title: string, abstract: string): Promise<void> {
    await this.navigate();
    await this.uploadPDF(filePath);
    await this.fillTitle(title);
    await this.fillAbstract(abstract);
    await this.submit();
    await this.page.waitForTimeout(1000); // Wait for submission to complete
  }

  /**
   * Get success message text
   * 中文注释: 获取成功消息文本
   */
  async getSuccessMessage(): Promise<string> {
    return await this.successMessage.textContent() || '';
  }

  /**
   * Get error message text
   * 中文注释: 获取错误消息文本
   */
  async getErrorMessage(): Promise<string> {
    return await this.errorMessage.textContent() || '';
  }

  /**
   * Check if submit button is disabled
   * 中文注释: 检查提交按钮是否被禁用
   */
  async isSubmitButtonDisabled(): Promise<boolean> {
    return await this.submitButton.isDisabled();
  }

  /**
   * Get title error message
   * 中文注释: 获取标题错误消息
   */
  async getTitleError(): Promise<string> {
    return await this.titleError.textContent() || '';
  }

  /**
   * Get abstract error message
   * 中文注释: 获取摘要错误消息
   */
  async getAbstractError(): Promise<string> {
    return await this.abstractError.textContent() || '';
  }
}
