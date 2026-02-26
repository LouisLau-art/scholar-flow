import { test, expect } from '@playwright/test'
import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

function row(id: string, status: string, title?: string) {
  const now = new Date().toISOString()
  return { id, status, title: title || 'Mocked', created_at: now, updated_at: now, journals: { title: 'Journal A' } }
}

test.describe('Process list filtering (mocked backend)', () => {
  test('URL query params filter the list', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'editor@example.com'))

    const rows = [
      row('11111111-1111-1111-1111-111111111111', 'under_review', 'Under Review Paper'),
      row('22222222-2222-2222-2222-222222222222', 'pre_check', 'Incoming Paper'),
    ]

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const pathname = url.pathname

      if (pathname === '/api/v1/user/profile') return fulfillJson(route, 200, { success: true, data: { roles: ['managing_editor'] } })
      if (pathname === '/api/v1/editor/rbac/context') {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            user_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            roles: ['managing_editor'],
            normalized_roles: ['managing_editor'],
            allowed_actions: ['process:view'],
            journal_scope: { enforcement_enabled: false, allowed_journal_ids: [], is_admin: true },
          },
        })
      }
      if (pathname === '/api/v1/editor/journals') return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname === '/api/v1/editor/internal-staff') return fulfillJson(route, 200, { success: true, data: [] })

      if (pathname.includes('/api/v1/editor/manuscripts/process')) {
        const statuses = url.searchParams.getAll('status')
        const filtered = statuses.length ? rows.filter((r) => statuses.includes(r.status)) : rows
        return fulfillJson(route, 200, { success: true, data: filtered })
      }

      return fulfillJson(route, 200, { success: true, data: {} })
    })

    await page.goto('/editor/process?status=under_review&q=basic-process-e2e')
    const table = page.getByTestId('editor-process-table')
    await expect(table).toBeVisible()
    await expect(page).toHaveURL(/status=under_review/)
    await expect(page).toHaveURL(/q=basic-process-e2e/)
    await expect(page.getByRole('button', { name: 'Under Review' })).toBeVisible()

    // 刷新后依然根据 URL 过滤（URL 驱动）
    await page.reload()
    await expect(page).toHaveURL(/status=under_review/)
    await expect(page).toHaveURL(/q=basic-process-e2e/)
    await expect(page.getByRole('button', { name: 'Under Review' })).toBeVisible()
  })
})
