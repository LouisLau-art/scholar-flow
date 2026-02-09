'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, DollarSign, Download, RefreshCw } from 'lucide-react'
import SiteHeader from '@/components/layout/SiteHeader'
import { Button, buttonVariants } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { EditorApi } from '@/services/editorApi'
import { authService } from '@/services/auth'
import type { FinanceInvoiceListMeta, FinanceInvoiceRow, FinanceStatusFilter } from '@/types/finance'
import { FinanceInvoicesTable } from '@/components/finance/FinanceInvoicesTable'

export default function FinanceDashboard() {
  const router = useRouter()
  const [rows, setRows] = useState<FinanceInvoiceRow[]>([])
  const [meta, setMeta] = useState<FinanceInvoiceListMeta | null>(null)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [confirmingId, setConfirmingId] = useState<string | null>(null)
  const [status, setStatus] = useState<FinanceStatusFilter>('all')
  const [search, setSearch] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [forbidden, setForbidden] = useState(false)
  const [internalReady, setInternalReady] = useState(false)

  const handleBack = () => {
    if (typeof window !== 'undefined' && window.history.length > 1) {
      router.back()
      return
    }
    router.push('/')
  }

  const query = useMemo(
    () => ({
      status,
      q: search.trim() || undefined,
      page: 1,
      pageSize: 50,
      sortBy: 'updated_at' as const,
      sortOrder: 'desc' as const,
    }),
    [search, status]
  )

  async function ensureInternalRole() {
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        setForbidden(true)
        setError('Please sign in again.')
        setInternalReady(true)
        return
      }
      const profileRes = await fetch('/api/v1/user/profile', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!profileRes.ok) {
        setForbidden(true)
        setError('Unable to verify permissions.')
        setInternalReady(true)
        return
      }
      const profileJson = await profileRes.json().catch(() => null)
      const roles = (profileJson?.data?.roles || []) as string[]
      const isInternal = roles.includes('editor') || roles.includes('admin')
      setForbidden(!isInternal)
      if (!isInternal) {
        setError('Finance is restricted to internal editor/admin roles.')
      } else {
        setError(null)
      }
    } catch {
      setForbidden(true)
      setError('Unable to verify permissions.')
    } finally {
      setInternalReady(true)
    }
  }

  async function loadInvoices() {
    setLoading(true)
    try {
      const json = await EditorApi.listFinanceInvoices(query)
      if (!json?.success) {
        const detail = (json?.detail || json?.message || 'Failed to fetch finance invoices').toString()
        setError(detail)
        if (detail.toLowerCase().includes('insufficient role')) {
          setForbidden(true)
        }
        return
      }
      setRows(json.data || [])
      setMeta(json.meta || null)
      setError(null)
    } catch (e) {
      setError((e as Error)?.message || 'Failed to fetch finance invoices')
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirm(row: FinanceInvoiceRow) {
    setConfirmingId(row.invoice_id)
    try {
      const expectedStatus =
        row.raw_status === 'unpaid' || row.raw_status === 'paid' || row.raw_status === 'waived'
          ? row.raw_status
          : undefined
      const json = await EditorApi.confirmInvoicePaid(row.manuscript_id, {
        expectedStatus,
        source: 'finance_page',
      })
      if (!json?.success) {
        setError((json?.detail || json?.message || 'Failed to confirm invoice').toString())
        return
      }
      await loadInvoices()
    } catch (e) {
      setError((e as Error)?.message || 'Failed to confirm invoice')
    } finally {
      setConfirmingId(null)
    }
  }

  async function handleExport() {
    setExporting(true)
    try {
      const result = await EditorApi.exportFinanceInvoices(query)
      const url = URL.createObjectURL(result.blob)
      const a = document.createElement('a')
      a.href = url
      a.download = result.filename || 'finance_invoices.csv'
      a.click()
      URL.revokeObjectURL(url)
      if (result.empty) {
        setError('当前无匹配账单，已导出空结果表头。')
      }
    } catch (e) {
      setError((e as Error)?.message || 'Export failed')
    } finally {
      setExporting(false)
    }
  }

  useEffect(() => {
    void ensureInternalRole()
  }, [])

  useEffect(() => {
    if (!internalReady || forbidden) return
    void loadInvoices()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [internalReady, forbidden, query])

  if (forbidden && internalReady) {
    return (
      <div className="min-h-screen bg-slate-50">
        <SiteHeader />
        <div className="mx-auto max-w-5xl p-8">
          <Card>
            <CardHeader>
              <CardTitle>Finance Access Restricted</CardTitle>
              <CardDescription>{error || 'You do not have permission to access Finance.'}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={handleBack}>Back</Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <SiteHeader />
      <div className="mx-auto max-w-5xl p-8">
        <header className="mb-10 border-b border-slate-200 pb-6">
          <div className="flex items-center justify-between gap-4">
            <button
              type="button"
              onClick={handleBack}
              className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }), 'gap-2')}
            >
              <ArrowLeft className="h-4 w-4" />
              返回
            </button>
            <div className="flex items-center gap-2">
              <Link
                href="/"
                className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}
              >
                首页
              </Link>
              <Link
                href="/dashboard"
                className={cn(buttonVariants({ variant: 'default', size: 'sm' }))}
              >
                Dashboard
              </Link>
            </div>
          </div>

          <div className="mt-6">
            <h1 className="flex items-center gap-3 font-serif text-3xl font-bold text-slate-900">
              <DollarSign className="h-8 w-8 text-blue-600" />
              Finance
            </h1>
            <p className="mt-2 text-slate-600">
              Internal invoices workspace backed by real Supabase invoices data.
            </p>
          </div>
        </header>

        <Card className="overflow-hidden border-slate-200">
          <CardHeader className="border-b border-slate-100">
            <CardTitle className="text-slate-900">Invoices</CardTitle>
            <CardDescription>Filter by status and export the current reconciliation snapshot.</CardDescription>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
              <select
                aria-label="Finance status filter"
                value={status}
                onChange={(e) => setStatus(e.target.value as FinanceStatusFilter)}
                className="h-9 rounded-md border border-slate-300 bg-white px-3 text-sm"
              >
                <option value="all">All</option>
                <option value="unpaid">Unpaid</option>
                <option value="paid">Paid</option>
                <option value="waived">Waived</option>
              </select>
              <input
                aria-label="Finance search input"
                placeholder="Search invoice number or manuscript title"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-9 w-full rounded-md border border-slate-300 px-3 text-sm sm:max-w-sm"
              />
              <div className="flex items-center gap-2">
                <Button type="button" variant="outline" onClick={() => void loadInvoices()} disabled={loading}>
                  <RefreshCw className="mr-1 h-4 w-4" />
                  Refresh
                </Button>
                <Button type="button" onClick={() => void handleExport()} disabled={loading || exporting}>
                  <Download className="mr-1 h-4 w-4" />
                  {exporting ? 'Exporting...' : 'Export CSV'}
                </Button>
              </div>
            </div>
            {meta && (
              <p className="text-xs text-slate-500">
                Total: {meta.total} • Snapshot: {meta.snapshot_at ? new Date(meta.snapshot_at).toLocaleString() : '—'}
              </p>
            )}
            {error && <p className="text-xs text-red-600">{error}</p>}
          </CardHeader>
          <CardContent className="p-0">
            <FinanceInvoicesTable
              rows={rows}
              loading={loading || !internalReady}
              confirmingInvoiceId={confirmingId}
              onConfirm={(row) => void handleConfirm(row)}
              emptyText="当前无匹配账单"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
