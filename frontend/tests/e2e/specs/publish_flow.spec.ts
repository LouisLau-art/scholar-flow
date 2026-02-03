import { test, expect } from '@playwright/test'
import path from 'path'
import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

function buildPipeline(args: {
  approved?: any[]
  published?: any[]
}) {
  return {
    pending_quality: [],
    under_review: [],
    pending_decision: [],
    revision_requested: [],
    resubmitted: [],
    rejected: [],
    approved: args.approved ?? [],
    published: args.published ?? [],
  }
}

test.describe('Publish workflow (mocked backend)', () => {
  test('Editor uploads final PDF then publishes', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('00000000-0000-0000-0000-000000000123', 'editor@example.com'))

    const manuscriptId = '00000000-0000-0000-0000-000000000456'
    const manuscriptTitle = 'Mocked Post-Acceptance Manuscript'
    const nowIso = new Date().toISOString()

    let approvedRow: any = {
      id: manuscriptId,
      title: manuscriptTitle,
      status: 'approved',
      invoice_amount: 1000,
      invoice_status: 'paid',
      final_pdf_path: null,
      updated_at: nowIso,
    }
    let published: any[] = []

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const pathname = url.pathname

      if (pathname === '/api/v1/user/profile') {
        return fulfillJson(route, 200, { success: true, data: { roles: ['editor'] } })
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

      if (pathname === '/api/v1/editor/pipeline') {
        return fulfillJson(route, 200, {
          success: true,
          data: buildPipeline({
            approved: [approvedRow],
            published,
          }),
        })
      }

      if (pathname === `/api/v1/manuscripts/${manuscriptId}/production-file` && req.method() === 'POST') {
        approvedRow = { ...approvedRow, final_pdf_path: `production/${manuscriptId}/final.pdf` }
        return fulfillJson(route, 200, { success: true, data: { final_pdf_path: approvedRow.final_pdf_path } })
      }

      if (pathname === '/api/v1/editor/publish' && req.method() === 'POST') {
        published = [{ id: manuscriptId, title: manuscriptTitle, status: 'published', updated_at: nowIso }]
        return fulfillJson(route, 200, { success: true, data: { ...approvedRow, status: 'published' } })
      }

      return route.fallback()
    })

    await page.goto('/dashboard?tab=editor')

    await expect(page.getByTestId('editor-pipeline')).toBeVisible()

    // Approved 卡片存在
    await page.getByRole('button', { name: /Approved/i }).click()
    await expect(page.getByText(manuscriptTitle)).toBeVisible()

    // 未上传最终稿时，Publish 应禁用
    const publishBtn = page.getByTestId('editor-publish').first()
    await expect(publishBtn).toBeDisabled()

    // Upload Final PDF
    await page.getByRole('button', { name: 'Upload Final PDF' }).first().click()
    const fixture = path.join(__dirname, '..', 'fixtures', 'revised.pdf')
    await page.setInputFiles('input[type="file"]', fixture)
    await page.getByRole('button', { name: 'Upload' }).click()

    // 上传后 Publish 可用
    await expect(publishBtn).toBeEnabled()

    // Publish
    await publishBtn.click()

    // Published 列表应出现该稿件
    await page.getByRole('button', { name: /Published/i }).click()
    await expect(page.getByText(manuscriptTitle)).toBeVisible()
  })
})

