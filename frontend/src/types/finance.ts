export type FinanceStatusFilter = 'all' | 'unpaid' | 'paid' | 'waived'
export type FinanceSortBy = 'updated_at' | 'amount' | 'status'
export type FinanceSortOrder = 'asc' | 'desc'

export type FinanceInvoiceRow = {
  invoice_id: string
  manuscript_id: string
  invoice_number?: string | null
  manuscript_title: string
  authors?: string | null
  amount: number
  currency: string
  raw_status: string
  effective_status: 'unpaid' | 'paid' | 'waived'
  confirmed_at?: string | null
  updated_at: string
  payment_gate_blocked: boolean
}

export type FinanceInvoiceListMeta = {
  page: number
  page_size: number
  total: number
  status_filter: FinanceStatusFilter
  snapshot_at: string
  empty: boolean
}

export type FinanceInvoiceListResponse = {
  success: boolean
  data: FinanceInvoiceRow[]
  meta?: FinanceInvoiceListMeta
  detail?: string
  message?: string
}

export type FinanceExportResponse = {
  blob: Blob
  filename: string
  snapshotAt?: string
  empty: boolean
}
