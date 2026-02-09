import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { EditorApi } from '@/services/editorApi'
import { authService } from '@/services/auth'

vi.mock('@/services/auth', () => ({
  authService: {
    getAccessToken: vi.fn().mockResolvedValue('mock-token'),
  },
}))

function mockBlobResponse(
  body: string,
  headers: Record<string, string> = {},
  status = 200
): Response {
  return new Response(body, {
    status,
    headers,
  })
}

describe('EditorApi finance endpoints', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('listFinanceInvoices sends query params with bearer token', async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [] }),
    })

    await EditorApi.listFinanceInvoices({
      status: 'paid',
      q: 'INV-001',
      page: 2,
      pageSize: 30,
      sortBy: 'amount',
      sortOrder: 'asc',
    })

    expect(authService.getAccessToken).toHaveBeenCalled()
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/editor/finance/invoices?status=paid&q=INV-001&page=2&page_size=30&sort_by=amount&sort_order=asc'),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer mock-token' }),
      })
    )
  })

  it('exportFinanceInvoices returns blob and response headers', async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockBlobResponse('invoice_id,manuscript_id\n1,m1\n', {
        'content-disposition': 'attachment; filename="finance_invoices_paid.csv"',
        'x-export-snapshot-at': '2026-02-09T12:00:00Z',
        'x-export-empty': '0',
      })
    )

    const result = await EditorApi.exportFinanceInvoices({ status: 'paid' })

    expect(result.filename).toBe('finance_invoices_paid.csv')
    expect(result.snapshotAt).toBe('2026-02-09T12:00:00Z')
    expect(result.empty).toBe(false)
    expect(result.blob).toBeInstanceOf(Blob)
  })

  it('confirmInvoicePaid posts expected_status and source', async () => {
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: { current_status: 'paid' } }),
    })

    await EditorApi.confirmInvoicePaid('manuscript-1', {
      expectedStatus: 'unpaid',
      source: 'finance_page',
    })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/editor/invoices/confirm',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          manuscript_id: 'manuscript-1',
          expected_status: 'unpaid',
          source: 'finance_page',
        }),
      })
    )
  })
})
