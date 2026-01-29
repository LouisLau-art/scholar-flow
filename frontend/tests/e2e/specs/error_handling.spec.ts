import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';

/**
 * E2E Tests for Error Handling
 * 中文注释: 错误处理的端到端测试
 */
test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    // Given: 已登录用户
    const loginPage = new LoginPage(page);
    await loginPage.login('test@example.com', 'password123');
  });

  test('should display error message when API returns error', async ({ page }) => {
    // Given: 用户已登录
    // When: API返回错误
    await page.route('**/api/v1/manuscripts', route => {
      route.fulfill({
        status: 500,
        json: { detail: 'Internal server error' }
      });
    });

    await page.goto('/submit');
    await page.locator('button[type="submit"]').click();

    // Then: 显示错误消息
    await expect(page.locator('[data-testid="error-toast"]')).toBeVisible();
  });

  test('should handle 404 errors gracefully', async ({ page }) => {
    // Given: 用户已登录
    // When: 访问不存在的页面
    await page.goto('/nonexistent-page');

    // Then: 显示404错误页面
    await expect(page.locator('[data-testid="404-page"]')).toBeVisible();
  });

  test('should handle network errors', async ({ page }) => {
    // Given: 用户已登录
    // When: 网络请求失败
    await page.route('**/api/v1/**', route => {
      route.abort('failed');
    });

    await page.goto('/submit');

    // Then: 显示网络错误提示
    await expect(page.locator('[data-testid="network-error"]')).toBeVisible();
  });

  test('should show validation errors inline', async ({ page }) => {
    // Given: 用户已登录
    // When: 提交无效数据
    await page.goto('/submit');
    await page.locator('input[name="title"]').fill('A'); // 太短
    await page.locator('button[type="submit"]').click();

    // Then: 显示内联验证错误
    await expect(page.locator('[data-testid="title-error"]')).toBeVisible();
  });
});
