import { expect, test } from '@playwright/test'

import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Internal collaboration overdue filter (mocked)', () => {
  test('process list supports overdue-only filtering', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'editor@example.com'))

    const overdueId = '11111111-1111-1111-1111-111111111111'
    const normalId = '22222222-2222-2222-2222-222222222222'

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname

      if (path === '/api/v1/user/profile') {
        return fulfillJson(route, 200, { success: true, data: { roles: ['managing_editor', 'admin'] } })
      }
      if (path === '/api/v1/editor/rbac/context') {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            user_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            roles: ['managing_editor', 'admin'],
            normalized_roles: ['managing_editor', 'admin'],
            allowed_actions: ['process:view'],
            journal_scope: { enforcement_enabled: false, allowed_journal_ids: [], is_admin: true },
          },
        })
      }
      if (path === '/api/v1/editor/journals') {
        return fulfillJson(route, 200, { success: true, data: [] })
      }
      if (path === '/api/v1/editor/internal-staff') {
        return fulfillJson(route, 200, { success: true, data: [] })
      }

      if (path.includes('/api/v1/editor/manuscripts/process') && req.method() === 'GET') {
        const overdueOnly = ['1', 'true', 'yes', 'on'].includes((url.searchParams.get('overdue_only') || '').toLowerCase())
        const rows = [
          {
            id: overdueId,
            title: 'Overdue Manuscript',
            status: 'under_review',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            journals: { title: 'Journal A' },
            is_overdue: true,
            overdue_tasks_count: 2,
          },
          {
            id: normalId,
            title: 'On Track Manuscript',
            status: 'under_review',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            journals: { title: 'Journal A' },
            is_overdue: false,
            overdue_tasks_count: 0,
          },
        ]
        return fulfillJson(route, 200, { success: true, data: overdueOnly ? [rows[0]] : rows })
      }

      return fulfillJson(route, 200, { success: true, data: {} })
    })

    await page.goto('/editor/process?q=overdue-seed')
    const table = page.getByTestId('editor-process-table')
    await expect(table).toBeVisible()

    await page.getByLabel('Overdue only').check()
    const searchButton = page.getByRole('main').getByRole('button', { name: 'Search' }).last()
    await expect(searchButton).toBeEnabled({ timeout: 10_000 })
    const overdueFilteredResponse = page.waitForResponse(
      (res) =>
        res.url().includes('/api/v1/editor/manuscripts/process') &&
        res.url().includes('overdue_only=true') &&
        res.request().method() === 'GET'
    )
    await searchButton.click()
    await overdueFilteredResponse
    await expect(page).toHaveURL(/overdue_only=true/)

    await expect(table.getByText(overdueId)).toBeVisible()
    await expect.poll(() => table.getByText(normalId).count(), { timeout: 10_000 }).toBe(0)
    await expect(table.getByText('Overdue')).toBeVisible()
  })
})
