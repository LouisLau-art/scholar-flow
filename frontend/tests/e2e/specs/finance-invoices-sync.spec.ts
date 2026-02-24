import { expect, test } from '@playwright/test'

import { buildSession, fulfillJson, seedSession } from '../utils'

async function enableE2EAuthBypass(page: import('@playwright/test').Page) {
  await page.context().setExtraHTTPHeaders({ 'x-scholarflow-e2e': '1' })
}

test.describe('Finance invoices sync (mocked)', () => {
  test('filters, confirms payment and exports with current filter', async ({ page }) => {
    test.setTimeout(60_000)
    await enableE2EAuthBypass(page)
    await seedSession(page, buildSession('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'editor@example.com'))

    const invoiceId = '11111111-1111-1111-1111-111111111111'
    const manuscriptId = '22222222-2222-2222-2222-222222222222'
    let currentStatus: 'unpaid' | 'paid' = 'unpaid'
    let lastExportStatus: string | null = null

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const path = url.pathname

      if (path === '/api/v1/user/profile') {
        return fulfillJson(route, 200, { success: true, data: { roles: ['editor', 'admin'] } })
      }

      if (path === '/api/v1/editor/finance/invoices' && req.method() === 'GET') {
        const statusFilter = (url.searchParams.get('status') || 'all').toLowerCase()
        const effectiveStatus = currentStatus
        const rows = [
          {
            invoice_id: invoiceId,
            manuscript_id: manuscriptId,
            invoice_number: 'INV-E2E-001',
            manuscript_title: 'Mocked Finance Manuscript',
            authors: 'Editor A',
            amount: 1200,
            currency: 'USD',
            raw_status: effectiveStatus,
            effective_status: effectiveStatus,
            confirmed_at: effectiveStatus === 'paid' ? '2026-02-09T12:00:00Z' : null,
            updated_at: '2026-02-09T12:00:00Z',
            payment_gate_blocked: effectiveStatus !== 'paid',
          },
        ]
        const filtered = statusFilter === 'all' ? rows : rows.filter((r) => r.effective_status === statusFilter)
        return fulfillJson(route, 200, {
          success: true,
          data: filtered,
          meta: {
            page: 1,
            page_size: 50,
            total: filtered.length,
            status_filter: statusFilter,
            snapshot_at: '2026-02-09T12:00:00Z',
            empty: filtered.length === 0,
          },
        })
      }

      if (path === '/api/v1/editor/invoices/confirm' && req.method() === 'POST') {
        currentStatus = 'paid'
        return fulfillJson(route, 200, {
          success: true,
          data: {
            invoice_id: invoiceId,
            manuscript_id: manuscriptId,
            previous_status: 'unpaid',
            current_status: 'paid',
            conflict: false,
          },
        })
      }

      if (path === '/api/v1/editor/finance/invoices/export' && req.method() === 'GET') {
        lastExportStatus = (url.searchParams.get('status') || 'all').toLowerCase()
        return route.fulfill({
          status: 200,
          headers: {
            'content-type': 'text/csv',
            'content-disposition': 'attachment; filename="finance_invoices_paid.csv"',
            'x-export-snapshot-at': '2026-02-09T12:00:00Z',
            'x-export-empty': lastExportStatus === 'paid' && currentStatus !== 'paid' ? '1' : '0',
          },
          body: 'invoice_id,manuscript_id\n11111111-1111-1111-1111-111111111111,22222222-2222-2222-2222-222222222222\n',
        })
      }

      return fulfillJson(route, 200, { success: true, data: {} })
    })

    await page.goto('/finance', { waitUntil: 'domcontentloaded' })
    await expect(page.getByText('INV-E2E-001')).toBeVisible()
    await expect(page.getByText('UNPAID', { exact: true })).toBeVisible()

    // 确认支付后应在同页刷新为 paid
    await page.getByRole('button', { name: 'Mark Paid' }).click()
    await expect(page.getByText('PAID', { exact: true })).toBeVisible()

    // 切换到 paid 筛选，仍应可见
    await page.getByRole('combobox', { name: 'Finance status filter' }).click()
    await page.getByRole('option', { name: 'Paid', exact: true }).click()
    await expect(page.getByText('INV-E2E-001')).toBeVisible()

    // 导出当前筛选
    await page.getByRole('button', { name: 'Export CSV' }).click()
    await expect.poll(() => lastExportStatus).toBe('paid')
  })
})
