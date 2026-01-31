import { test, expect } from '@playwright/test'

test.describe('Editor dashboard', () => {
  test('editor routes require authentication', async ({ page }) => {
    // 编辑器路由需要认证
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // 应该被重定向到登录页
    expect(page.url()).toContain('/login')
  })

  test('admin routes require authentication', async ({ page }) => {
    await page.goto('/admin/manuscripts')
    await page.waitForLoadState('networkidle')
    
    expect(page.url()).toContain('/login')
  })
})
