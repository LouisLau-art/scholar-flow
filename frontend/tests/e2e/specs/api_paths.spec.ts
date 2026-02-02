import { test, expect } from '@playwright/test'

test.describe('API paths', () => {
  test('public API endpoints are accessible', async ({ page }) => {
    // 测试公开的 API 端点
    const response = await page.request.get('/api/v1/stats/system')
    
    // 应该返回 200 或其他非 500 状态
    expect(response.status()).toBeLessThan(500)
  })

  test('protected routes redirect properly', async ({ page }) => {
    // 验证受保护路由正确重定向
    await page.goto('/dashboard')
    expect(page.url()).toContain('/login')

    await page.goto('/admin')
    expect(page.url()).toContain('/login')
  })
})
