import { test, expect } from '@playwright/test'
import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Process list enhancements (mocked backend)', () => {
  test('Debounced text search + monitor read-only behavior', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'editor@example.com'))

    const manuscriptId = '33333333-3333-3333-3333-333333333333'
    const otherId = '44444444-4444-4444-4444-444444444444'
    let updatedAt = new Date().toISOString()

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const pathname = url.pathname

      if (pathname === '/api/v1/user/profile') return fulfillJson(route, 200, { success: true, data: { roles: ['editor'] } })
      if (pathname === '/api/v1/editor/journals') return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname === '/api/v1/editor/internal-staff') return fulfillJson(route, 200, { success: true, data: [] })

      if (pathname.startsWith('/api/v1/editor/manuscripts/process')) {
        const q = (url.searchParams.get('q') || '').toLowerCase()
        const rows = [
          {
            id: manuscriptId,
            title: 'Incoming Energy Paper',
            status: 'pre_check',
            created_at: updatedAt,
            updated_at: updatedAt,
            journals: { title: 'Journal A' },
          },
          {
            id: otherId,
            title: 'Unrelated Topic',
            status: 'under_review',
            created_at: updatedAt,
            updated_at: updatedAt,
            journals: { title: 'Journal A' },
          },
        ]
        const filtered = q ? rows.filter((r) => (r.title || '').toLowerCase().includes(q)) : rows
        return fulfillJson(route, 200, { success: true, data: filtered })
      }

      return fulfillJson(route, 200, { success: true, data: {} })
    })

    await page.goto('/editor/process')
    const table = page.getByTestId('editor-process-table')
    await expect(table).toBeVisible()
    await expect(table.getByText(manuscriptId)).toBeVisible()
    await expect(table.getByText(otherId)).toBeVisible()

    // Debounce 搜索：输入 energy 后应仅剩一条
    await page.getByPlaceholder('Energy, 9286... (UUID) ...').fill('energy')
    const searchButton = page.getByRole('main').getByRole('button', { name: 'Search' }).last()
    await expect(searchButton).toBeEnabled({ timeout: 10_000 })
    const filteredResponse = page.waitForResponse(
      (res) =>
        res.url().includes('/api/v1/editor/manuscripts/process') &&
        res.url().includes('q=energy') &&
        res.request().method() === 'GET'
    )
    await searchButton.click()
    await filteredResponse
    await expect(page).toHaveURL(/q=energy/)
    await expect(table.getByText(manuscriptId)).toBeVisible()
    await expect.poll(() => table.getByText(otherId).count(), { timeout: 10_000 }).toBe(0)

    // /editor/process 当前是只读监控，不应提供 quick-precheck 等动作入口
    await expect(page.getByRole('columnheader', { name: 'Actions' })).toHaveCount(0)
    await expect(page.getByTestId(`quick-precheck-${manuscriptId}`)).toHaveCount(0)
  })
})
