import { test, expect } from '@playwright/test'

test.describe('Submission flow', () => {
  test('submit page requires authentication', async ({ page }) => {
    // 未登录访问 submit 页面应重定向到登录
    await page.goto('/submit')
    await page.waitForLoadState('networkidle')
    
    expect(page.url()).toContain('/login')
    expect(page.url()).toContain('next=%2Fsubmit')
  })

  test('login page has link to signup', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('networkidle')
    
    // 登录页应该有注册链接
    const signupLink = page.getByRole('link', { name: /create an account/i })
    await expect(signupLink).toBeVisible()
  })
})
