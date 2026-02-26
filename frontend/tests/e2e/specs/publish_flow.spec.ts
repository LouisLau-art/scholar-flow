import { test, expect } from '@playwright/test'
import path from 'path'
import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Publish workflow (mocked backend)', () => {
  test('Editor uploads final PDF then publishes', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('00000000-0000-0000-0000-000000000123', 'editor@example.com'))

    const manuscriptId = '00000000-0000-0000-0000-000000000456'
    const manuscriptTitle = 'Mocked Post-Acceptance Manuscript'
    const nowIso = new Date().toISOString()

    let manuscript: any = {
      id: manuscriptId,
      title: manuscriptTitle,
      status: 'proofreading',
      final_pdf_path: null,
      updated_at: nowIso,
      invoice: { amount: 1000, status: 'paid' },
      signed_files: {
        original_manuscript: { signed_url: 'https://example.com/original.pdf', path: `${manuscriptId}/v1.pdf` },
        peer_review_reports: [],
      },
    }

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const pathname = url.pathname

      if (pathname === '/api/v1/user/profile') {
        return fulfillJson(route, 200, { success: true, data: { roles: ['managing_editor'] } })
      }

      if (pathname === '/api/v1/editor/rbac/context') {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            user_id: '00000000-0000-0000-0000-000000000123',
            roles: ['managing_editor'],
            normalized_roles: ['managing_editor'],
            allowed_actions: ['manuscript:view_detail', 'decision:record_first', 'decision:submit_final'],
            journal_scope: { enforcement_enabled: false, allowed_journal_ids: [], is_admin: true },
          },
        })
      }

      if (pathname === '/api/v1/stats/author') {
        return fulfillJson(route, 200, {
          success: true,
          data: { total_submissions: 0, published: 0, under_review: 0, revision_required: 0 },
        })
      }

      if (pathname === '/api/v1/manuscripts/mine') {
        return fulfillJson(route, 200, { success: true, data: [] })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}`) {
        return fulfillJson(route, 200, { success: true, data: manuscript })
      }

      if (pathname.includes(`/api/v1/manuscripts/${manuscriptId}/production-file`) && req.method() === 'POST') {
        manuscript = { ...manuscript, final_pdf_path: `production/${manuscriptId}/final.pdf`, updated_at: new Date().toISOString() }
        return fulfillJson(route, 200, { success: true, data: { final_pdf_path: manuscript.final_pdf_path } })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/production/advance` && req.method() === 'POST') {
        manuscript = { ...manuscript, status: 'published', updated_at: new Date().toISOString() }
        return fulfillJson(route, 200, { success: true, data: { new_status: 'published' } })
      }

      if (pathname.includes('/comments')) return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname.includes('/tasks')) return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname.includes('/audit-logs')) return fulfillJson(route, 200, { success: true, data: [] })
      if (pathname.includes('/timeline-context')) return fulfillJson(route, 200, { success: true, data: { events: [] } })
      if (pathname.includes('/cards-context')) {
        return fulfillJson(route, 200, { success: true, data: { task_summary: {}, role_queue: {} } })
      }
      if (pathname.includes('/versions')) return fulfillJson(route, 200, { success: true, data: [] })

      // 默认兜底：避免 Next rewrites 代理到 127.0.0.1:8000（单测环境下可能未启动后端）
      return fulfillJson(route, 200, { success: true, data: {} })
    })

    await page.goto(`/editor/manuscript/${manuscriptId}`)
    await expect(page.getByTestId('production-status-card')).toBeVisible()

    // 上传最终稿
    await page.getByRole('button', { name: 'Upload Final PDF' }).click()
    const fixture = path.join(__dirname, '..', 'fixtures', 'revised.pdf')
    const dialog = page.locator('[role="dialog"][data-state="open"]').filter({ hasText: 'Production Upload' })
    await expect(dialog).toBeVisible()
    await dialog.locator('input[type="file"]').setInputFiles(fixture)
    await expect(dialog.getByRole('button', { name: 'Upload' })).toBeEnabled()
    const uploadResponse = page.waitForResponse(
      (res) =>
        res.url().includes(`/api/v1/manuscripts/${manuscriptId}/production-file`) &&
        res.request().method() === 'POST'
    )
    await dialog.getByRole('button', { name: 'Upload' }).click()
    await uploadResponse
    await expect(page.locator('[role="dialog"][data-state="open"]').filter({ hasText: 'Production Upload' })).toHaveCount(0)

    // Publish（proofreading -> published）
    const publishResult = await page.evaluate(async (id) => {
      const res = await fetch(`/api/v1/editor/manuscripts/${id}/production/advance`, { method: 'POST' })
      const body = await res.json().catch(() => null)
      return { ok: res.ok, status: res.status, body }
    }, manuscriptId)
    expect(publishResult.ok).toBeTruthy()
    await page.reload()
    await expect(page.getByTestId('production-stage')).toHaveText('Published')
  })
})
