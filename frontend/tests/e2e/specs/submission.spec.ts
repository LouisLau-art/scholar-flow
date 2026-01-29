import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';
import { SubmissionPage } from '../pages/submission.page';

/**
 * E2E Tests for Manuscript Submission
 * 中文注释: 稿件提交的端到端测试
 */
test.describe('Manuscript Submission', () => {
  test.beforeEach(async ({ page }) => {
    // Given: 已登录用户
    const loginPage = new LoginPage(page);
    await loginPage.login('test@example.com', 'password123');
  });

  test('should successfully submit manuscript with valid data', async ({ page }) => {
    // Given: 稿件提交页面
    const submissionPage = new SubmissionPage(page);

    // When: 上传PDF并提交稿件
    await submissionPage.navigate();
    await submissionPage.uploadPDF('./tests/e2e/fixtures/sample.pdf');
    await submissionPage.fillTitle('Test Manuscript Title');
    await submissionPage.fillAbstract('This is a test abstract for the manuscript.');
    await submissionPage.submit();

    // Then: 系统成功创建稿件并显示成功消息
    await expect(submissionPage.successMessage).toBeVisible();
    const successMessage = await submissionPage.getSuccessMessage();
    expect(successMessage).toContain('success');
  });

  test('should show validation error for empty form', async ({ page }) => {
    // Given: 稿件提交页面
    const submissionPage = new SubmissionPage(page);

    // When: 尝试提交空表单
    await submissionPage.navigate();
    await submissionPage.submit();

    // Then: 系统显示表单验证错误
    await expect(submissionPage.titleError).toBeVisible();
    await expect(submissionPage.abstractError).toBeVisible();
  });

  test('should show validation error for title too short', async ({ page }) => {
    // Given: 稿件提交页面
    const submissionPage = new SubmissionPage(page);

    // When: 填写过短的标题
    await submissionPage.navigate();
    await submissionPage.uploadPDF('./tests/e2e/fixtures/sample.pdf');
    await submissionPage.fillTitle('A'); // 太短
    await submissionPage.fillAbstract('Valid abstract content here.');
    await submissionPage.submit();

    // Then: 显示标题验证错误
    await expect(submissionPage.titleError).toBeVisible();
  });

  test('should show validation error for abstract too long', async ({ page }) => {
    // Given: 稿件提交页面
    const submissionPage = new SubmissionPage(page);

    // When: 填写过长的摘要
    await submissionPage.navigate();
    await submissionPage.uploadPDF('./tests/e2e/fixtures/sample.pdf');
    await submissionPage.fillTitle('Valid Title');
    await submissionPage.fillAbstract('A'.repeat(5001)); // 超过5000字符限制
    await submissionPage.submit();

    // Then: 显示摘要验证错误
    await expect(submissionPage.abstractError).toBeVisible();
  });

  test('should disable submit button when form is invalid', async ({ page }) => {
    // Given: 稿件提交页面
    const submissionPage = new SubmissionPage(page);

    // When: 表单不完整
    await submissionPage.navigate();

    // Then: 提交按钮被禁用
    await expect(submissionPage.submitButton).toBeDisabled();
  });
});
