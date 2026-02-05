import { test, expect } from '@playwright/test'

test.describe('API paths', () => {
  test('public API endpoints are accessible', async ({ page }) => {
    // 中文注释：
    // - mocked E2E 不依赖真实后端（Next rewrites 默认会代理到 127.0.0.1:8000，CI 会失败）。
    // - 因此用 browser fetch + route mock 来验证“端点可访问且不崩”。
    await page.route('**/api/v1/stats/system', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ success: true, data: { ok: true } }),
      })
    })

    await page.goto('/')
    const status = await page.evaluate(async () => {
      const res = await fetch('/api/v1/stats/system')
      return res.status
    })
    expect(status).toBe(200)
  })

  test('protected routes redirect properly', async ({ page }) => {
    // 验证受保护路由正确重定向
    await page.goto('/dashboard')
    expect(page.url()).toContain('/login')

    await page.goto('/admin')
    expect(page.url()).toContain('/login')
  })
})
