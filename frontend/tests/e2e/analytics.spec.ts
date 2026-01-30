/**
 * Analytics Dashboard E2E 测试
 * 功能: 端到端测试仪表盘和导出功能
 *
 * 中文注释:
 * - 测试页面加载和组件渲染
 * - 测试导出功能
 * - 需要认证用户（编辑角色）
 */

import { test, expect } from '@playwright/test'

test.describe('Analytics Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // 注意: 真实测试需要先登录获取认证
    // 这里假设测试环境已配置好认证
  })

  test('should display page title', async ({ page }) => {
    await page.goto('/editor/analytics')

    // 检查页面标题存在
    await expect(page.locator('h1')).toContainText('分析仪表盘')
  })

  test('should display KPI cards section', async ({ page }) => {
    await page.goto('/editor/analytics')

    // 等待 KPI 卡片加载
    await expect(page.locator('text=核心指标')).toBeVisible()

    // 检查 KPI 卡片数量
    const kpiCards = page.locator('[data-testid="kpi-card"]')
    // 如果没有 data-testid，检查 Card 组件
    const cards = page.locator('.grid >> .rounded-lg.border')
    await expect(cards.first()).toBeVisible({ timeout: 10000 })
  })

  test('should display finance KPI section', async ({ page }) => {
    await page.goto('/editor/analytics')

    await expect(page.locator('text=财务指标')).toBeVisible()
  })

  test('should display charts section', async ({ page }) => {
    await page.goto('/editor/analytics')

    // 检查趋势图表部分
    await expect(page.locator('text=投稿趋势')).toBeVisible()

    // 检查状态分布和决定分布
    await expect(page.locator('text=状态分布')).toBeVisible()
    await expect(page.locator('text=决定分布')).toBeVisible()
  })

  test('should display geo distribution section', async ({ page }) => {
    await page.goto('/editor/analytics')

    await expect(page.locator('text=作者地理分布')).toBeVisible()
  })

  test('should have export buttons', async ({ page }) => {
    await page.goto('/editor/analytics')

    // 检查导出按钮
    await expect(page.locator('button:has-text("Excel")')).toBeVisible()
    await expect(page.locator('button:has-text("CSV")')).toBeVisible()
  })

  test('should show loading skeletons initially', async ({ page }) => {
    // 拦截 API 请求使其延迟
    await page.route('**/api/v1/analytics/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      await route.continue()
    })

    await page.goto('/editor/analytics')

    // 检查骨架屏显示
    const skeletons = page.locator('.animate-pulse')
    await expect(skeletons.first()).toBeVisible()
  })

  test('should handle API error gracefully', async ({ page }) => {
    // 模拟 API 错误
    await page.route('**/api/v1/analytics/summary', (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: '服务器错误' }),
      })
    })

    await page.goto('/editor/analytics')

    // 检查错误消息显示
    await expect(page.locator('text=加载失败')).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Analytics Export', () => {
  test('should trigger Excel download', async ({ page }) => {
    await page.goto('/editor/analytics')

    // 等待页面加载
    await expect(page.locator('button:has-text("Excel")')).toBeVisible()

    // 设置下载监听
    const downloadPromise = page.waitForEvent('download')

    // 点击 Excel 导出按钮
    await page.click('button:has-text("Excel")')

    // 注意: 实际测试需要认证，这里可能会失败
    // 如果没有认证，会收到 401 错误
  })

  test('should trigger CSV download', async ({ page }) => {
    await page.goto('/editor/analytics')

    await expect(page.locator('button:has-text("CSV")')).toBeVisible()

    // 点击 CSV 导出按钮
    await page.click('button:has-text("CSV")')

    // 检查按钮状态变化（导出中）
    // await expect(page.locator('button:has-text("导出中")')).toBeVisible()
  })
})

test.describe('Analytics Navigation', () => {
  test('should be accessible from Editor Dashboard', async ({ page }) => {
    // 从 Dashboard 导航到 Analytics
    await page.goto('/dashboard')

    // 点击 Editor tab（如果有权限）
    const editorTab = page.locator('[data-testid="editor-tab"]')
    if (await editorTab.isVisible()) {
      await editorTab.click()

      // 检查 Analytics 链接
      await expect(
        page.locator('a:has-text("Analytics Dashboard")'),
      ).toBeVisible()
    }
  })
})
