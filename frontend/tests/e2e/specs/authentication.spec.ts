import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test('login page loads correctly', async ({ page }) => {
    await page.goto('/login')
    
    // 等待客户端渲染完成 - 使用更长的超时
    await expect(page.getByTestId('login-email')).toBeVisible({ timeout: 15000 })
    await expect(page.getByTestId('login-password')).toBeVisible()
    await expect(page.getByTestId('login-submit')).toBeVisible()
    
    // 验证标题存在
    await expect(page.locator('h2')).toContainText('Sign in')
  })

  test('protected routes redirect to login', async ({ page }) => {
    // 访问受保护的路由应重定向到登录页
    await page.goto('/submit')
    await page.waitForLoadState('networkidle')
    
    // 应该被重定向到登录页，URL 包含 next 参数
    expect(page.url()).toContain('/login')
    expect(page.url()).toContain('next=%2Fsubmit')
  })

  test('dashboard redirect to login when not authenticated', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // 应该被重定向到登录页
    expect(page.url()).toContain('/login')
  })
})
