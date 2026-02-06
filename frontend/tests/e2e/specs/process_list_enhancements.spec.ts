import { test, expect } from '@playwright/test'
import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Process list enhancements (mocked backend)', () => {
  test('Debounced text search + quick pre-check action', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'editor@example.com'))

    const manuscriptId = '33333333-3333-3333-3333-333333333333'
    const otherId = '44444444-4444-4444-4444-444444444444'
    let status = 'pre_check'
    let updatedAt = new Date().toISOString()

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const pathname = url.pathname

      if (pathname === '/api/v1/user/profile') return fulfillJson(route, 200, { success: true, data: { roles: ['editor'] } })
      if (pathname === '/api/v1/editor/journals') return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname === '/api/v1/editor/internal-staff') return fulfillJson(route, 200, { success: true, data: [] })

      if (pathname === '/api/v1/editor/manuscripts/process') {
        const q = (url.searchParams.get('q') || '').toLowerCase()
        const rows = [
          {
            id: manuscriptId,
            title: 'Incoming Energy Paper',
            status,
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

      const quickPrecheckPrefix = `/api/v1/editor/manuscripts/${manuscriptId}/quick-precheck`
      if (pathname === quickPrecheckPrefix && req.method() === 'POST') {
        const body = (await req.postDataJSON()) as any
        const decision = body?.decision
        if (decision === 'approve') status = 'under_review'
        if (decision === 'revision') status = 'minor_revision'
        updatedAt = new Date().toISOString()
        return fulfillJson(route, 200, { success: true, data: { id: manuscriptId, status, updated_at: updatedAt } })
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
    await expect(table.getByText(manuscriptId)).toBeVisible()
    await expect(table.getByText(otherId)).not.toBeVisible()

    // Quick Pre-check：改为 Revision，并要求 comment
    await page.getByTestId(`quick-precheck-${manuscriptId}`).click()
    await expect(page.getByRole('heading', { name: 'Quick Pre-check' })).toBeVisible()
    const dialog = page.getByRole('dialog')
    await dialog.getByText('Request Revision', { exact: true }).click()
    await page.getByPlaceholder('Required for revision…').fill('Please fix formatting and reference style.')
    await page.getByRole('button', { name: 'Confirm' }).click()

    // 表格应更新为 Minor Revision（无需页面刷新）
    await expect(table.getByText('Minor Revision')).toBeVisible()
  })
})
