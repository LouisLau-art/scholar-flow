import { test, expect } from '@playwright/test'
import { fulfillJson } from '../utils'

test('dashboard exposes author, reviewer, editor roles', async ({ page }) => {
  await page.route('**/api/v1/stats/author', async (route) => {
    await fulfillJson(route, 200, { success: true, data: { total_submissions: 0 } })
  })
  await page.route('**/api/v1/editor/pipeline', async (route) => {
    await fulfillJson(route, 200, { success: true, data: { pending_quality: [], under_review: [], pending_decision: [], published: [] } })
  })

  await page.goto('/dashboard')
  await expect(page.getByRole('tab', { name: /Author/i })).toBeVisible()
  await expect(page.getByRole('tab', { name: /Reviewer/i })).toBeVisible()
  await expect(page.getByRole('tab', { name: /Editor/i })).toBeVisible()

  await page.getByRole('tab', { name: /Reviewer/i }).click()
  await page.getByRole('tab', { name: /Editor/i }).click()
})
