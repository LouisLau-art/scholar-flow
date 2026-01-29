import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';
import { SubmissionPage } from '../pages/submission.page';

/**
 * E2E Tests for Browser Compatibility
 * 中文注释: 浏览器兼容性的端到端测试
 */
test.describe('Browser Compatibility', () => {
  test('should work correctly in Chromium', async ({ page, browserName }) => {
    test.skip(browserName !== 'chromium', 'Chromium-specific test');

    // Given: 用户已登录
    const loginPage = new LoginPage(page);
    await loginPage.login('test@example.com', 'password123');

    // When: 使用稿件提交功能
    const submissionPage = new SubmissionPage(page);
    await submissionPage.navigate();

    // Then: 所有元素正常显示
    await expect(submissionPage.fileInput).toBeVisible();
    await expect(submissionPage.titleInput).toBeVisible();
    await expect(submissionPage.abstractInput).toBeVisible();
  });

  test('should work correctly in Firefox', async ({ page, browserName }) => {
    test.skip(browserName !== 'firefox', 'Firefox-specific test');

    // Given: 用户已登录
    const loginPage = new LoginPage(page);
    await loginPage.login('test@example.com', 'password123');

    // When: 使用稿件提交功能
    const submissionPage = new SubmissionPage(page);
    await submissionPage.navigate();

    // Then: 所有元素正常显示
    await expect(submissionPage.fileInput).toBeVisible();
    await expect(submissionPage.titleInput).toBeVisible();
    await expect(submissionPage.abstractInput).toBeVisible();
  });

  test('should work correctly in WebKit (Safari)', async ({ page, browserName }) => {
    test.skip(browserName !== 'webkit', 'WebKit-specific test');

    // Given: 用户已登录
    const loginPage = new LoginPage(page);
    await loginPage.login('test@example.com', 'password123');

    // When: 使用稿件提交功能
    const submissionPage = new SubmissionPage(page);
    await submissionPage.navigate();

    // Then: 所有元素正常显示
    await expect(submissionPage.fileInput).toBeVisible();
    await expect(submissionPage.titleInput).toBeVisible();
    await expect(submissionPage.abstractInput).toBeVisible();
  });

  test('should handle responsive design correctly', async ({ page }) => {
    // Given: 用户已登录
    const loginPage = new LoginPage(page);
    await loginPage.login('test@example.com', 'password123');

    // When: 在移动设备尺寸下
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/submit');

    // Then: 页面布局适应移动设备
    await expect(page.locator('input[type="file"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });
});
