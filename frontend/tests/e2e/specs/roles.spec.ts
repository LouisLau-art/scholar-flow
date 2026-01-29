import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';
import { SubmissionPage } from '../pages/submission.page';
import { EditorPage } from '../pages/editor.page';

/**
 * E2E Tests for User Roles
 * 中文注释: 用户角色的端到端测试
 */
test.describe('User Roles', () => {
  test('author can submit manuscript', async ({ page }) => {
    // Given: 作者用户登录
    const loginPage = new LoginPage(page);
    await loginPage.login('author@example.com', 'password123');

    // When: 访问稿件提交页面
    const submissionPage = new SubmissionPage(page);
    await submissionPage.navigate();

    // Then: 可以提交稿件
    await expect(submissionPage.submitButton).toBeEnabled();
  });

  test('editor can access editor dashboard', async ({ page }) => {
    // Given: 编辑用户登录
    const loginPage = new LoginPage(page);
    await loginPage.login('editor@example.com', 'password123');

    // When: 访问编辑仪表板
    const editorPage = new EditorPage(page);
    await editorPage.navigate();

    // Then: 可以看到待处理稿件
    await expect(editorPage.pendingManuscripts).toBeVisible();
  });

  test('author cannot access editor dashboard', async ({ page }) => {
    // Given: 作者用户登录
    const loginPage = new LoginPage(page);
    await loginPage.login('author@example.com', 'password123');

    // When: 尝试访问编辑仪表板
    await page.goto('/editor/dashboard');

    // Then: 被重定向或显示无权限
    await expect(page.locator('[data-testid="access-denied"]')).toBeVisible();
  });

  test('reviewer can access assigned manuscripts', async ({ page }) => {
    // Given: 审稿人用户登录
    const loginPage = new LoginPage(page);
    await loginPage.login('reviewer@example.com', 'password123');

    // When: 访问审稿人页面
    await page.goto('/reviewer');

    // Then: 可以看到分配的稿件
    await expect(page.locator('[data-testid="assigned-manuscripts"]')).toBeVisible();
  });
});
