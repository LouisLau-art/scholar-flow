import { test, expect } from '@playwright/test'
import { buildSession, fulfillJson, seedSession } from './utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Editor manuscript details (mocked backend)', () => {
  test.setTimeout(90_000)

  test('shows header, file sections, and edits invoice info', async ({ page }) => {
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

      // SiteHeader / Layout dependencies
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
            owner: { full_name: 'Owner A', email: 'owner@example.com' },
            editor: { full_name: 'Editor A', email: 'editor@example.com' },
            invoice: { status: 'unpaid', amount: invoiceApc },
            invoice_metadata: {
              authors: invoiceAuthors,
              affiliation: invoiceAffiliation,
              apc_amount: invoiceApc,
              funding_info: invoiceFunding,
            },
            signed_files: {
              original_manuscript: {
                path: 'manuscripts/demo.pdf',
                // 使用站内静态资源，避免 iframe 跨域/网络导致 page load 事件长时间不触发
                signed_url: '/favicon.svg',
              },
              peer_review_reports: [
                {
                  review_report_id: 'rr1',
                  reviewer_name: 'Reviewer A',
                  signed_url: '/favicon.svg',
                  path: 'review_reports/rr1/annotated.pdf',
                },
              ],
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

      // default: 避免请求真实后端导致 E2E 卡死
      return fulfillJson(route, 200, { success: true, data: [] })
    })

    await page.goto(`/editor/manuscript/${manuscriptId}`, { waitUntil: 'domcontentloaded' })
    await page.waitForURL(`**/editor/manuscript/${manuscriptId}`)

    await expect(page.getByRole('heading', { name: 'Mocked Manuscript Title' })).toBeVisible({ timeout: 15000 })
    await expect(page.locator('main').locator('text=Decision').first()).toBeVisible()

    await expect(page.getByText('Cover Letter')).toBeVisible()
    await expect(page.getByText('Original Manuscript')).toBeVisible()
    await expect(page.getByText('Peer Review Reports (Word/PDF)')).toBeVisible()

    // Invoice info shows initial values
    await expect(page.getByText('Invoice Info')).toBeVisible()
    await expect(page.locator('main').locator('text=John Doe, Jane Smith').first()).toBeVisible()
    await expect(page.locator('main').locator('text=University of Science').first()).toBeVisible()

    // Open modal and edit
    await page.getByTestId('invoice-edit').click()
    await page.getByPlaceholder('Authors').fill('Alice, Bob')
    await page.getByPlaceholder('Affiliation').fill('New Institute')
    await page.getByPlaceholder('APC Amount (USD)').fill('1200')
    await page.getByPlaceholder('Funding Info').fill('N/A')
    await page.getByRole('button', { name: /save/i }).click()

    // After reload, updated values should show
    await expect(page.locator('main').locator('text=Alice, Bob').first()).toBeVisible()
    await expect(page.locator('main').locator('text=New Institute').first()).toBeVisible()
    await expect(page.locator('main').locator('text=1200').first()).toBeVisible()
  })
})
