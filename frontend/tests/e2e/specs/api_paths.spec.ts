import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';

/**
 * E2E Tests for API Path Consistency
 * 中文注释: API路径一致性的端到端测试
 */
test.describe('API Path Consistency', () => {
  test.beforeEach(async ({ page }) => {
    // Given: 已登录用户
    const loginPage = new LoginPage(page);
    await loginPage.login('test@example.com', 'password123');
  });

  test('should use consistent API paths for manuscripts', async ({ page }) => {
    // Given: 用户已登录
    // When: 访问稿件相关页面
    await page.goto('/submit');

    // 监听网络请求
    const manuscriptRequest = page.waitForRequest(/\/api\/v1\/manuscripts/);

    // 触发API调用（例如获取稿件列表）
    await page.locator('[data-testid="load-manuscripts"]').click();

    // Then: API路径符合规范（无尾部斜杠）
    const request = await manuscriptRequest;
    expect(request.url()).toMatch(/\/api\/v1\/manuscripts$/);
  });

  test('should use consistent API paths for editor endpoints', async ({ page }) => {
    // Given: 编辑用户已登录
    const loginPage = new LoginPage(page);
    await loginPage.login('editor@example.com', 'password123');

    // When: 访问编辑仪表板
    await page.goto('/editor/dashboard');

    // 监听网络请求
    const editorRequest = page.waitForRequest(/\/api\/v1\/editor/);

    // 触发API调用
    await page.locator('[data-testid="load-pending"]').click();

    // Then: API路径符合规范（无尾部斜杠）
    const request = await editorRequest;
    expect(request.url()).toMatch(/\/api\/v1\/editor$/);
  });

  test('should handle API errors consistently', async ({ page }) => {
    // Given: 用户已登录
    const loginPage = new LoginPage(page);
    await loginPage.login('test@example.com', 'password123');

    // When: API返回错误
    await page.route('**/api/v1/**', route => {
      route.fulfill({
        status: 500,
        json: { detail: 'Internal server error' }
      });
    });

    await page.goto('/submit');

    // Then: 错误消息统一显示
    await expect(page.locator('[data-testid="error-toast"]')).toBeVisible();
  });
});
