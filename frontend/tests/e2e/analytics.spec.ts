/**
 * Analytics Dashboard E2E 测试
 * 功能: 端到端测试仪表盘访问权限
 */

import { test, expect } from '@playwright/test'

test.describe('Analytics Dashboard', () => {
  test('analytics page requires authentication', async ({ page }) => {
    // 访问分析页面应重定向到登录
    await page.goto('/editor/analytics')
    await page.waitForLoadState('networkidle')
    
    // 应该被重定向到登录页
    expect(page.url()).toContain('/login')
  })
})

test.describe('Analytics Navigation', () => {
  test('dashboard redirects to login when not authenticated', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    expect(page.url()).toContain('/login')
  })
})
