import { expect, test } from '@playwright/test'

import { LoginPage } from '../pages/login.page'

const smokeEmail = process.env.SMOKE_ADMIN_EMAIL?.trim() || ''
const smokePassword = process.env.SMOKE_ADMIN_PASSWORD?.trim() || ''
const smokePublishedArticleId = process.env.SMOKE_PUBLISHED_ARTICLE_ID?.trim() || ''
const smokeDecisionManuscriptId = process.env.SMOKE_DECISION_MANUSCRIPT_ID?.trim() || ''

test.describe('Deployed UAT smoke', () => {
  test('public homepage loads', async ({ page, baseURL }) => {
    await page.goto('/')

    await expect(page.getByRole('heading', { name: /ScholarFlow Journal/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /Submit Manuscript/i })).toBeVisible()

    if ((baseURL || '').includes('q1yw.vercel.app')) {
      await expect(page.getByText(/Current Environment: UAT Staging/i)).toBeVisible()
    }
  })

  test('editor shell loads after real login', async ({ page }) => {
    test.skip(!smokeEmail || !smokePassword, '需要配置 SMOKE_ADMIN_EMAIL / SMOKE_ADMIN_PASSWORD')

    const loginPage = new LoginPage(page)
    await loginPage.goto()
    await loginPage.login(smokeEmail, smokePassword)

    await page.goto('/dashboard?tab=editor')
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: 20000 })
    await expect(
      page.getByText('当前账号未分配可访问的 Dashboard 角色，请联系管理员在 User Management 中补齐角色。')
    ).not.toBeVisible()

    await page.goto('/settings')
    await expect(page.getByRole('heading', { name: /Account Settings/i })).toBeVisible({ timeout: 20000 })

    const processResponsePromise = page.waitForResponse(
      (response) =>
        response.url().includes('/api/v1/editor/manuscripts/process') &&
        response.request().method() === 'GET' &&
        response.status() === 200,
      { timeout: 30000 }
    )
    await page.goto('/editor/process')
    await processResponsePromise
    await expect(page.getByRole('heading', { name: /Manuscripts Process/i })).toBeVisible()
    await expect(page.getByTestId('editor-process-table')).toBeVisible({ timeout: 20000 })
    await expect(page.getByText(/Failed to fetch manuscripts process/i)).not.toBeVisible()

    await page.goto('/admin/users')
    await expect(page.getByRole('heading', { name: /User Management/i })).toBeVisible({ timeout: 20000 })
  })

  test('published article route stays readable', async ({ page }) => {
    test.skip(!smokePublishedArticleId, '未配置 SMOKE_PUBLISHED_ARTICLE_ID')

    await page.goto(`/articles/${smokePublishedArticleId}`)
    await expect(page.getByText(/Article not found/i)).not.toBeVisible()
    await expect(page.getByRole('button', { name: /Download PDF/i })).toBeVisible({ timeout: 20000 })
  })

  test('decision workspace route loads after real login', async ({ page }) => {
    test.skip(
      !smokeEmail || !smokePassword || !smokeDecisionManuscriptId,
      '需要配置 SMOKE_ADMIN_EMAIL / SMOKE_ADMIN_PASSWORD / SMOKE_DECISION_MANUSCRIPT_ID'
    )

    const loginPage = new LoginPage(page)
    await loginPage.goto()
    await loginPage.login(smokeEmail, smokePassword)

    await page.goto(`/editor/decision/${smokeDecisionManuscriptId}`)
    await expect(page.getByText(/Decision workspace is unavailable/i)).not.toBeVisible()
    await expect(page.getByRole('link', { name: '返回稿件详情' })).toBeVisible({ timeout: 20000 })
    await expect(page.getByTestId('decision-workspace-mode-banner')).toBeVisible({ timeout: 20000 })
    await expect(page.getByText(/Review Reports|No submitted reports yet\./i)).toBeVisible({ timeout: 20000 })
  })
})
