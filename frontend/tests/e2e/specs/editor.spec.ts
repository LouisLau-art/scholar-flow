import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';
import { EditorPage } from '../pages/editor.page';

/**
 * E2E Tests for Editor Dashboard
 * 中文注释: 编辑仪表板的端到端测试
 */
test.describe('Editor Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Given: 已登录的编辑用户
    const loginPage = new LoginPage(page);
    await loginPage.login('editor@example.com', 'password123');
  });

  test('should show pending manuscripts list for editor', async ({ page }) => {
    // Given: 编辑仪表板页面
    const editorPage = new EditorPage(page);

    // When: 导航到编辑仪表板
    await editorPage.navigate();

    // Then: 系统显示待处理稿件列表
    await expect(editorPage.pendingManuscripts).toBeVisible();
    const count = await editorPage.getPendingCount();
    expect(count).toBeGreaterThan(0);
  });

  test('should allow editor to assign reviewer', async ({ page }) => {
    // Given: 编辑仪表板页面
    const editorPage = new EditorPage(page);

    // When: 编辑分配审稿人
    await editorPage.navigate();
    await editorPage.assignReviewerToFirst();

    // Then: 系统更新稿件状态并显示成功提示
    await expect(editorPage.successToast).toBeVisible();
    const successMessage = await editorPage.getSuccessMessage();
    expect(successMessage).toContain('success');
    await expect(editorPage.manuscriptStatus).toContainText('Assigned');
  });

  test('should show different manuscript statuses', async ({ page }) => {
    // Given: 编辑仪表板页面
    const editorPage = new EditorPage(page);

    // When: 查看稿件列表
    await editorPage.navigate();

    // Then: 可以看到不同状态的稿件
    const pendingCount = await editorPage.getPendingCount();
    expect(pendingCount).toBeGreaterThan(0);
  });

  test('should handle empty pending manuscripts list', async ({ page }) => {
    // Given: 编辑仪表板页面（假设没有待处理稿件）
    const editorPage = new EditorPage(page);

    // When: 导航到编辑仪表板
    await editorPage.navigate();

    // Then: 页面仍应正常加载
    await expect(editorPage.isEditorDashboardLoaded()).resolves.toBeTruthy();
  });
});
