import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';
import { SubmissionPage } from '../pages/submission.page';

/**
 * E2E Tests for Authentication
 * 中文注释: 认证的端到端测试
 */
test.describe('Authentication', () => {
  test('should show login prompt when user is not authenticated', async ({ page }) => {
    // Given: 用户未登录
    const submissionPage = new SubmissionPage(page);

    // When: 访问稿件提交页面
    await submissionPage.navigate();

    // Then: 系统显示登录提示并阻止提交
    await expect(page.locator('[data-testid="login-prompt"]')).toBeVisible();
    await expect(submissionPage.submitButton).toBeDisabled();
  });

  test('should successfully login with valid credentials', async ({ page }) => {
    // Given: 登录页面
    const loginPage = new LoginPage(page);

    // When: 使用有效凭据登录
    await loginPage.login('test@example.com', 'password123');

    // Then: 用户被重定向到仪表板或提交页面
    const currentUrl = page.url();
    expect(currentUrl).toMatch(/\/dashboard|\/submit/);
  });

  test('should show error for invalid credentials', async ({ page }) => {
    // Given: 登录页面
    const loginPage = new LoginPage(page);

    // When: 使用无效凭据登录
    await loginPage.navigate();
    await loginPage.fillEmail('invalid@example.com');
    await loginPage.fillPassword('wrongpassword');
    await loginPage.clickLogin();

    // Then: 显示错误消息
    await expect(loginPage.errorMessage).toBeVisible();
    const errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toContain('Invalid');
  });

  test('should persist session after login', async ({ page }) => {
    // Given: 已登录用户
    const loginPage = new LoginPage(page);
    await loginPage.login('test@example.com', 'password123');

    // When: 刷新页面
    await page.reload();

    // Then: 用户仍保持登录状态
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('should show login prompt for protected routes', async ({ page }) => {
    // Given: 未登录用户
    // When: 尝试访问受保护的路由
    await page.goto('/dashboard');

    // Then: 系统重定向到登录页面
    await expect(page.locator('input[name="email"]')).toBeVisible();
  });
});
