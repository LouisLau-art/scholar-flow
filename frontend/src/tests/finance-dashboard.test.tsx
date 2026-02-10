import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import FinanceDashboard from '@/app/finance/page'
import { EditorApi } from '@/services/editorApi'
import { authService } from '@/services/auth'

vi.mock('@/services/editorApi', () => ({
  EditorApi: {
    listFinanceInvoices: vi.fn(),
    confirmInvoicePaid: vi.fn(),
    exportFinanceInvoices: vi.fn(),
  },
}))

vi.mock('@/services/auth', () => ({
  authService: {
    getAccessToken: vi.fn().mockResolvedValue('mock-token'),
  },
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    back: vi.fn(),
  }),
}))

vi.mock('next/link', () => ({
  default: ({ href, children }: any) => <a href={href}>{children}</a>,
}))

vi.mock('@/components/layout/SiteHeader', () => ({
  default: () => <div data-testid="site-header" />,
}))

describe('Finance dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(globalThis.fetch as any) = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        data: { roles: ['editor'] },
      }),
    })
    ;(EditorApi.listFinanceInvoices as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      data: [
        {
          invoice_id: 'inv-1',
          manuscript_id: 'ms-1',
          invoice_number: 'INV-001',
          manuscript_title: 'Deep Learning in Medicine',
          authors: 'Alice',
          amount: 1500,
          currency: 'USD',
          raw_status: 'unpaid',
          effective_status: 'unpaid',
          confirmed_at: null,
          updated_at: '2026-02-09T12:00:00Z',
          payment_gate_blocked: true,
        },
      ],
      meta: {
        page: 1,
        page_size: 50,
        total: 1,
        status_filter: 'all',
        snapshot_at: '2026-02-09T12:00:00Z',
        empty: false,
      },
    })
    ;(EditorApi.confirmInvoicePaid as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      data: { current_status: 'paid' },
    })
  })

  it('loads real invoices and supports status filtering', async () => {
    render(<FinanceDashboard />)

    await waitFor(() => {
      expect(EditorApi.listFinanceInvoices).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 'all',
          page: 1,
          pageSize: 50,
          sortBy: 'updated_at',
        })
      )
    })
    expect(await screen.findByText('INV-001')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('combobox', { name: 'Finance status filter' }))
    fireEvent.click(await screen.findByRole('option', { name: 'Paid' }))
    await waitFor(() => {
      expect(EditorApi.listFinanceInvoices).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 'paid',
        })
      )
    })
  })

  it('calls confirm API with expected status and source', async () => {
    render(<FinanceDashboard />)
    const btn = await screen.findByRole('button', { name: 'Mark Paid' })
    fireEvent.click(btn)

    await waitFor(() => {
      expect(EditorApi.confirmInvoicePaid).toHaveBeenCalledWith('ms-1', {
        expectedStatus: 'unpaid',
        source: 'finance_page',
      })
    })
    expect(authService.getAccessToken).toHaveBeenCalled()
  })
})
