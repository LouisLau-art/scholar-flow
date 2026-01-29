import { Page, Locator } from '@playwright/test';

/**
 * Page Object Model for Login Page
 * 中文注释: 登录页面的页面对象模型
 */
export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.locator('input[name="email"]');
    this.passwordInput = page.locator('input[name="password"]');
    this.loginButton = page.locator('button[type="submit"]');
    this.errorMessage = page.locator('[data-testid="error-message"]');
  }

  /**
   * Navigate to login page
   * 中文注释: 导航到登录页面
   */
  async navigate(): Promise<void> {
    await this.page.goto('/login');
  }

  /**
   * Fill email field
   * 中文注释: 填写邮箱字段
   */
  async fillEmail(email: string): Promise<void> {
    await this.emailInput.fill(email);
  }

  /**
   * Fill password field
   * 中文注释: 填写密码字段
   */
  async fillPassword(password: string): Promise<void> {
    await this.passwordInput.fill(password);
  }

  /**
   * Click login button
   * 中文注释: 点击登录按钮
   */
  async clickLogin(): Promise<void> {
    await this.loginButton.click();
  }

  /**
   * Perform complete login flow
   * 中文注释: 执行完整的登录流程
   */
  async login(email: string, password: string): Promise<void> {
    await this.navigate();
    await this.fillEmail(email);
    await this.fillPassword(password);
    await this.clickLogin();
    await this.page.waitForURL(/\/dashboard|\/submit/);
  }

  /**
   * Check if login button is disabled
   * 中文注释: 检查登录按钮是否被禁用
   */
  async isLoginButtonDisabled(): Promise<boolean> {
    return await this.loginButton.isDisabled();
  }

  /**
   * Get error message text
   * 中文注释: 获取错误消息文本
   */
  async getErrorMessage(): Promise<string> {
    return await this.errorMessage.textContent() || '';
  }
}
