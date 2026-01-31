import { test, expect } from '@playwright/test'

test.describe('DOI Tasks', () => {
  test('DOI tasks page requires authentication', async ({ page }) => {
    // 访问 DOI 任务页面应重定向到登录
    await page.goto('/editor/doi-tasks')
    await page.waitForLoadState('networkidle')
    
    // 应该被重定向到登录页
    expect(page.url()).toContain('/login')
  })
})
