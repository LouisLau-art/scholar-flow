import { test, expect } from '@playwright/test'

test.describe('Error handling', () => {
  test('404 page shows for invalid routes', async ({ page }) => {
    const response = await page.goto('/invalid-route-that-does-not-exist')
    
    // Next.js 会返回 404 或显示 404 页面
    expect(response?.status()).toBe(404)
  })

  test('API errors show user-friendly messages', async ({ page }) => {
    // 测试 API 返回错误时的处理
    await page.route('**/api/v1/stats/system', async (route) => {
      await route.fulfill({
        status: 500,
        body: JSON.stringify({ success: false, message: 'Internal error' }),
      })
    })
    
    // 首页加载应该优雅处理 API 错误
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // 页面应该仍然可用
    await expect(page.getByText('ScholarFlow').first()).toBeVisible()
  })
})
