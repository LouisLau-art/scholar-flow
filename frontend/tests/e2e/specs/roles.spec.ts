import { test, expect } from '@playwright/test'

test.describe('Dashboard Access', () => {
  test('dashboard requires authentication', async ({ page }) => {
    // 访问 dashboard 应该被重定向到登录页
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // 验证被重定向到登录页
    expect(page.url()).toContain('/login')
  })

  test('home page shows navigation with role options', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // 首页应该显示 ScholarFlow 品牌
    await expect(page.getByText('ScholarFlow').first()).toBeVisible()
  })
})
