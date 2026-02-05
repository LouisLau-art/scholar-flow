import { test, expect } from '@playwright/test'
import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Manuscript detail layout (mocked backend)', () => {
  test.setTimeout(90_000)

  test('shows aligned header, 3 file cards, and invoice panel; attaches screenshot', async ({ page }) => {
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('00000000-0000-0000-0000-000000000001', 'editor@example.com'))

    const manuscriptId = '00000000-0000-0000-0000-000000000123'
    let invoiceAuthors = 'John Doe, Jane Smith'
    let invoiceAffiliation = 'University of Science'
    let invoiceApc = 1000
    let invoiceFunding = 'Grant #12345'

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const pathname = url.pathname

      if (pathname === '/api/v1/cms/menu') {
        return fulfillJson(route, 200, { success: true, data: [] })
      }
      if (pathname === '/api/v1/user/profile') {
        return fulfillJson(route, 200, { success: true, data: { roles: ['admin', 'editor'] } })
      }
      if (pathname === '/api/v1/notifications') {
        return fulfillJson(route, 200, { success: true, data: [] })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}` && req.method() === 'GET') {
        return fulfillJson(route, 200, {
          success: true,
          data: {
            id: manuscriptId,
            title: 'Mocked Manuscript Title',
            status: 'decision',
            updated_at: new Date().toISOString(),
            owner: { id: 'o1', full_name: 'Owner A', email: 'owner@example.com' },
            editor: { id: 'e1', full_name: 'Editor A', email: 'editor@example.com' },
            invoice: { status: 'unpaid', amount: invoiceApc },
            invoice_metadata: {
              authors: invoiceAuthors,
              affiliation: invoiceAffiliation,
              apc_amount: invoiceApc,
              funding_info: invoiceFunding,
            },
            files: [
              {
                id: 'original_manuscript',
                file_type: 'manuscript',
                label: 'Current Manuscript PDF',
                path: 'manuscripts/demo.pdf',
                signed_url: '/favicon.svg',
              },
              {
                id: 'rr1',
                file_type: 'review_attachment',
                label: 'Reviewer A — Annotated PDF',
                path: 'review_reports/rr1/annotated.pdf',
                signed_url: '/favicon.svg',
              },
            ],
            signed_files: {
              original_manuscript: { path: 'manuscripts/demo.pdf', signed_url: '/favicon.svg' },
              peer_review_reports: [],
            },
          },
        })
      }

      if (pathname === `/api/v1/editor/manuscripts/${manuscriptId}/invoice-info` && req.method() === 'PUT') {
        let body: any = {}
        try {
          body = req.postDataJSON() as any
        } catch {
          body = {}
        }
        if (typeof body?.authors === 'string') invoiceAuthors = body.authors
        if (typeof body?.affiliation === 'string') invoiceAffiliation = body.affiliation
        if (typeof body?.apc_amount === 'number') invoiceApc = body.apc_amount
        if (typeof body?.funding_info === 'string') invoiceFunding = body.funding_info
        return fulfillJson(route, 200, { success: true, data: { ok: true } })
      }

      if (pathname === `/api/v1/manuscripts/${manuscriptId}/versions` && req.method() === 'GET') {
        return fulfillJson(route, 200, { success: true, data: { versions: [], revisions: [] } })
      }

      return fulfillJson(route, 200, { success: true, data: {} })
    })

    await page.goto(`/editor/manuscript/${manuscriptId}`, { waitUntil: 'domcontentloaded' })
    await expect(page.getByRole('heading', { name: 'Mocked Manuscript Title' })).toBeVisible({ timeout: 15000 })

    await expect(page.getByRole('heading', { name: 'Cover Letter' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Original Manuscript' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Peer Review Files' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Owner Binding' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Invoice Info' })).toBeVisible()

    const shot = await page.screenshot({ fullPage: true })
    test.info().attach('manuscript-detail-layout', { body: shot, contentType: 'image/png' })
  })
})
