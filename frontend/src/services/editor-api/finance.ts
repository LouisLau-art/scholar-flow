import type {
  FinanceExportResponse,
  FinanceInvoiceListResponse,
} from '@/types/finance'
import type { FinanceInvoiceFilters } from './types'

type FinanceApiDeps = {
  authedFetch: (input: RequestInfo, init?: RequestInit) => Promise<Response>
  getFilenameFromContentDisposition: (contentDisposition: string | null) => string
}

export function createFinanceApi(deps: FinanceApiDeps) {
  const { authedFetch, getFilenameFromContentDisposition } = deps

  return {
    async listFinanceInvoices(filters: FinanceInvoiceFilters = {}): Promise<FinanceInvoiceListResponse> {
      const params = new URLSearchParams()
      if (filters.status) params.set('status', filters.status)
      if (filters.q) params.set('q', filters.q)
      if (typeof filters.page === 'number') params.set('page', String(filters.page))
      if (typeof filters.pageSize === 'number') params.set('page_size', String(filters.pageSize))
      if (filters.sortBy) params.set('sort_by', filters.sortBy)
      if (filters.sortOrder) params.set('sort_order', filters.sortOrder)
      const qs = params.toString()
      const res = await authedFetch(`/api/v1/editor/finance/invoices${qs ? `?${qs}` : ''}`)
      return res.json()
    },

    async exportFinanceInvoices(filters: FinanceInvoiceFilters = {}): Promise<FinanceExportResponse> {
      const params = new URLSearchParams()
      if (filters.status) params.set('status', filters.status)
      if (filters.q) params.set('q', filters.q)
      if (filters.sortBy) params.set('sort_by', filters.sortBy)
      if (filters.sortOrder) params.set('sort_order', filters.sortOrder)
      const qs = params.toString()
      const res = await authedFetch(`/api/v1/editor/finance/invoices/export${qs ? `?${qs}` : ''}`)
      if (!res.ok) {
        let msg = 'Export failed'
        try {
          const j = await res.json()
          msg = (j?.detail || j?.message || msg).toString()
        } catch {
          // ignore
        }
        throw new Error(msg)
      }
      const blob = await res.blob()
      return {
        blob,
        filename: getFilenameFromContentDisposition(res.headers.get('content-disposition')),
        snapshotAt: res.headers.get('x-export-snapshot-at') || undefined,
        empty: res.headers.get('x-export-empty') === '1',
      }
    },
  }
}
