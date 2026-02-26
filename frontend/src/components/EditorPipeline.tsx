'use client'

import { useState, useEffect, useRef } from 'react'
import { FileText, Users, CheckCircle2, ArrowRight, Loader2, RefreshCw, Clock } from 'lucide-react'
import { authService } from '@/services/auth'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import ProductionUploadDialog from '@/components/ProductionUploadDialog'
import { getStatusLabel } from '@/lib/statusStyles'

type Manuscript = {
  id: string
  title: string
  status?: string
  created_at?: string
  updated_at?: string
  review_count?: number
  version?: number
  invoice_id?: string | null
  invoice_amount?: number | string | null
  invoice_status?: string | null
  final_pdf_path?: string | null
}

type PipelineStage =
  | 'pending_quality'
  | 'under_review'
  | 'pending_decision'
  | 'approved'
  | 'published'
  | 'resubmitted'
  | 'revision_requested'
  | 'rejected'

const SECTION_PREVIEW_LIMIT = 3
const ACTIVE_FILTER_RENDER_LIMIT = 30
const PIPELINE_CACHE_TTL_MS = 15_000

let pipelineCache: { data: any; cachedAt: number } | null = null

interface EditorPipelineProps {
  onAssign?: (manuscript: Manuscript) => void
  onDecide?: (manuscript: Manuscript) => void
  refreshKey?: number
}

export default function EditorPipeline({ onAssign, onDecide, refreshKey }: EditorPipelineProps) {
  const [pipelineData, setPipelineData] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [activeFilter, setActiveFilter] = useState<PipelineStage | null>(null)
  const listRef = useRef<HTMLDivElement | null>(null)
  const requestIdRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)
  const pipelineDataRef = useRef<any>(null)

  useEffect(() => {
    pipelineDataRef.current = pipelineData
  }, [pipelineData])

  const reloadPipeline = async (
    options?: { preferCache?: boolean; silent?: boolean; suppressErrorToast?: boolean; forceRefresh?: boolean }
  ) => {
    const now = Date.now()
    const cacheValid = Boolean(pipelineCache && now - pipelineCache.cachedAt < PIPELINE_CACHE_TTL_MS)

    if (options?.preferCache && cacheValid && pipelineCache) {
      setPipelineData(pipelineCache.data)
    }

    const hasVisibleData = pipelineDataRef.current !== null || (cacheValid && Boolean(pipelineCache))
    const blockUi = !options?.silent && !hasVisibleData
    if (blockUi) setIsLoading(true)
    else setIsRefreshing(true)

    const currentRequestId = ++requestIdRef.current
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    try {
      const token = await authService.getAccessToken()
      const response = await fetch('/api/v1/editor/pipeline', {
        signal: controller.signal,
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(options?.forceRefresh ? { 'x-sf-force-refresh': '1' } : {}),
        },
      })
      const data = await response.json().catch(() => ({}))
      if (currentRequestId !== requestIdRef.current || controller.signal.aborted) return
      if (!response.ok || !data?.success) {
        throw new Error(data?.detail || data?.message || 'Failed to fetch pipeline data')
      }
      setPipelineData(data.data)
      pipelineCache = { data: data.data, cachedAt: Date.now() }
    } catch (error) {
      if (controller.signal.aborted || currentRequestId !== requestIdRef.current) return
      if (!options?.suppressErrorToast) {
        toast.error(error instanceof Error ? error.message : 'Failed to fetch pipeline data')
      }
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setIsLoading(false)
        setIsRefreshing(false)
      }
    }
  }

  useEffect(() => {
    reloadPipeline({ preferCache: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey])

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  const handleFilterClick = (stage: PipelineStage) => {
    setActiveFilter(stage)
    requestAnimationFrame(() => {
      listRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }

  const clearFilter = () => {
    setActiveFilter(null)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Loading pipeline data...</span>
      </div>
    )
  }

  const renderSectionHeader = (title: string, count: number, filter: PipelineStage) => (
    (activeFilter === filter || !activeFilter) && (
      <div className="flex items-center justify-between mb-2 mt-6 first:mt-0">
        <h4 className="text-md font-semibold text-foreground flex items-center gap-2">
          {title}
          <span className="bg-muted text-muted-foreground py-0.5 px-2 rounded-full text-xs">{count}</span>
        </h4>
      </div>
    )
  )

  const hasData = (stage: string) => (pipelineData?.[stage] || []).length > 0
  const getData = (stage: string) => (pipelineData?.[stage] || [])
  const getDisplayItems = (stage: PipelineStage) => {
    const items = getData(stage)
    const limit = activeFilter ? ACTIVE_FILTER_RENDER_LIMIT : SECTION_PREVIEW_LIMIT
    return items.slice(0, limit)
  }
  const isTruncatedInActiveFilter = (stage: PipelineStage) =>
    activeFilter === stage && getData(stage).length > ACTIVE_FILTER_RENDER_LIMIT

  const handlePublish = async (manuscriptId: string) => {
    const toastId = toast.loading('Publishing...')
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error('Please sign in again.', { id: toastId })
        return
      }
      const response = await fetch('/api/v1/editor/publish', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ manuscript_id: manuscriptId, source: 'editor_pipeline' }),
      })
      const data = await response.json().catch(() => null)
      if (response.status === 403) {
        toast.error('Waiting for Payment.', { id: toastId })
        return
      }
      if (response.status === 400) {
        toast.error(data?.detail || 'Production PDF required.', { id: toastId })
        return
      }
      if (!response.ok || !data?.success) {
        toast.error(data?.detail || data?.message || 'Publish failed.', { id: toastId })
        return
      }
      toast.success('Published.', { id: toastId })
      await reloadPipeline({ silent: true, forceRefresh: true })
    } catch (error) {
      toast.error('Publish failed. Please try again.', { id: toastId })
    }
  }

  const handleConfirmPayment = async (manuscriptId: string) => {
    const toastId = toast.loading('Confirming payment...')
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error('Please sign in again.', { id: toastId })
        return
      }
      const response = await fetch('/api/v1/editor/invoices/confirm', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ manuscript_id: manuscriptId }),
      })
      const data = await response.json().catch(() => null)
      if (!response.ok || !data?.success) {
        toast.error(data?.detail || data?.message || 'Confirm payment failed.', { id: toastId })
        return
      }
      toast.success('Payment confirmed.', { id: toastId })
      await reloadPipeline({ silent: true, forceRefresh: true })
    } catch {
      toast.error('Confirm payment failed. Please try again.', { id: toastId })
    }
  }

  const handleRegenerateInvoicePdf = async (invoiceId: string) => {
    const toastId = toast.loading('Regenerating invoice PDF...')
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error('Please sign in again.', { id: toastId })
        return
      }
      const response = await fetch(`/api/v1/invoices/${encodeURIComponent(invoiceId)}/pdf/regenerate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await response.json().catch(() => null)
      if (!response.ok || !data?.success) {
        toast.error(data?.detail || data?.message || 'Regenerate failed.', { id: toastId })
        return
      }
      toast.success('Invoice PDF regenerated.', { id: toastId })
      await reloadPipeline({ silent: true, forceRefresh: true })
    } catch {
      toast.error('Regenerate failed. Please try again.', { id: toastId })
    }
  }

  return (
    <div className="space-y-6" data-testid="editor-pipeline">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-2xl font-bold text-foreground">Manuscript Pipeline</h2>
        {isRefreshing && !isLoading ? (
          <div className="inline-flex items-center gap-1 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Syncing latest data...
          </div>
        ) : null}
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 待质检 */}
        <button
          type="button"
          onClick={() => handleFilterClick('pending_quality')}
          className={`text-left bg-card rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'pending_quality'
              ? 'border-primary/50 bg-primary/10'
              : 'border-border hover:border-primary/40 hover:bg-primary/10'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-foreground">Pending Quality</h3>
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <div className="text-3xl font-bold text-primary mb-2">
            {getData('pending_quality').length}
          </div>
          <div className="text-sm text-muted-foreground">New submissions</div>
        </button>

        {/* Resubmitted */}
        <button
          type="button"
          onClick={() => handleFilterClick('resubmitted')}
          className={`text-left bg-card rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'resubmitted'
              ? 'border-indigo-400 bg-indigo-50'
              : 'border-border hover:border-indigo-200 hover:bg-indigo-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-foreground">Resubmitted</h3>
            <RefreshCw className="h-5 w-5 text-indigo-600" />
          </div>
          <div className="text-3xl font-bold text-indigo-600 mb-2">
            {getData('resubmitted').length}
          </div>
          <div className="text-sm text-muted-foreground">Revisions received</div>
        </button>

        {/* 评审中 */}
        <button
          type="button"
          onClick={() => handleFilterClick('under_review')}
          className={`text-left bg-card rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'under_review'
              ? 'border-amber-400 bg-amber-50'
              : 'border-border hover:border-amber-200 hover:bg-amber-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-foreground">Under Review</h3>
            <Users className="h-5 w-5 text-amber-600" />
          </div>
          <div className="text-3xl font-bold text-amber-600 mb-2">
            {getData('under_review').length}
          </div>
          <div className="text-sm text-muted-foreground">In peer review</div>
        </button>

        {/* 待录用 */}
        <button
          type="button"
          onClick={() => handleFilterClick('pending_decision')}
          className={`text-left bg-card rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'pending_decision'
              ? 'border-purple-400 bg-purple-50'
              : 'border-border hover:border-purple-200 hover:bg-purple-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-foreground">Pending Decision</h3>
            <CheckCircle2 className="h-5 w-5 text-purple-600" />
          </div>
          <div className="text-3xl font-bold text-purple-600 mb-2">
            {getData('pending_decision').length}
          </div>
          <div className="text-sm text-muted-foreground">Ready for decision</div>
        </button>

        {/* Approved (Waiting for Payment / Ready to Publish) */}
        <button
          type="button"
          onClick={() => handleFilterClick('approved')}
          className={`text-left bg-card rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'approved'
              ? 'border-emerald-400 bg-emerald-50'
              : 'border-border hover:border-emerald-200 hover:bg-emerald-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-foreground">Approved</h3>
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          </div>
          <div className="text-3xl font-bold text-emerald-600 mb-2">
            {getData('approved').length}
          </div>
          <div className="text-sm text-muted-foreground">Waiting for payment / publish</div>
        </button>

        {/* Revision Requested (Waiting) */}
        <button
          type="button"
          onClick={() => handleFilterClick('revision_requested')}
          className={`text-left bg-card rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'revision_requested'
              ? 'border-border bg-muted/40'
              : 'border-border hover:border-border/80 hover:bg-muted/40'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-foreground">Waiting for Author</h3>
            <Clock className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="text-3xl font-bold text-muted-foreground mb-2">
            {getData('revision_requested').length}
          </div>
          <div className="text-sm text-muted-foreground">Revision requested</div>
        </button>

        {/* 已发布 */}
        <button
          type="button"
          onClick={() => handleFilterClick('published')}
          className={`text-left bg-card rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'published'
              ? 'border-emerald-400 bg-emerald-50'
              : 'border-border hover:border-emerald-200 hover:bg-emerald-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-foreground">Published</h3>
            <ArrowRight className="h-5 w-5 text-emerald-600" />
          </div>
          <div className="text-3xl font-bold text-emerald-600 mb-2">
            {getData('published').length}
          </div>
          <div className="text-sm text-muted-foreground">Completed</div>
        </button>

        {/* 已拒稿 */}
        <button
          type="button"
          onClick={() => handleFilterClick('rejected')}
          className={`text-left bg-card rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'rejected'
              ? 'border-rose-400 bg-rose-50'
              : 'border-border hover:border-rose-200 hover:bg-rose-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-foreground">Rejected</h3>
            <FileText className="h-5 w-5 text-rose-600" />
          </div>
          <div className="text-3xl font-bold text-rose-600 mb-2">
            {getData('rejected').length}
          </div>
          <div className="text-sm text-muted-foreground">Archived</div>
        </button>
      </div>

      {/* 详细列表 */}
      <div ref={listRef} className="bg-card rounded-xl border border-border p-6" data-testid="editor-pipeline-list">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h3 className="text-lg font-semibold text-foreground">Recent Activity</h3>
          {activeFilter && (
            <Button variant="ghost" size="sm" onClick={clearFilter}>
              Clear Filter
            </Button>
          )}
        </div>
        
        <div className="space-y-2">
          {/* Empty States */}
          {activeFilter && !hasData(activeFilter) && (
             <div className="rounded-lg border border-dashed border-border p-6 text-center text-muted-foreground">
               No manuscripts in {activeFilter.replace('_', ' ')}.
             </div>
          )}

          {/* Pending Quality */}
          {hasData('pending_quality') && (!activeFilter || activeFilter === 'pending_quality') && (
            <>
              {renderSectionHeader('Pending Quality Check', getData('pending_quality').length, 'pending_quality')}
              {getDisplayItems('pending_quality').map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-border/60 rounded-lg hover:bg-muted/40">
                  <div>
                    <div className="font-medium text-foreground">{manuscript.title}</div>
                    <div className="text-sm text-muted-foreground">
                      Submitted: {manuscript.created_at ? new Date(manuscript.created_at).toLocaleDateString() : '—'}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-primary/10 text-primary text-sm font-medium rounded-full">New</span>
                    <Button size="sm" onClick={() => onAssign?.(manuscript)}>Assign Reviewers</Button>
                  </div>
                </div>
              ))}
              {isTruncatedInActiveFilter('pending_quality') ? (
                <div className="text-xs text-muted-foreground">Showing first {ACTIVE_FILTER_RENDER_LIMIT} manuscripts in this stage.</div>
              ) : null}
            </>
          )}

          {/* Resubmitted */}
          {hasData('resubmitted') && (!activeFilter || activeFilter === 'resubmitted') && (
            <>
              {renderSectionHeader('Resubmitted Revisions', getData('resubmitted').length, 'resubmitted')}
              {getDisplayItems('resubmitted').map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-border/60 rounded-lg hover:bg-muted/40">
                  <div>
                    <div className="font-medium text-foreground">{manuscript.title}</div>
                    <div className="text-sm text-muted-foreground">
                      Resubmitted: {manuscript.updated_at ? new Date(manuscript.updated_at).toLocaleDateString() : '—'}
                      {manuscript.version && ` (v${manuscript.version})`}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-indigo-100 text-indigo-800 text-sm font-medium rounded-full">Resubmitted</span>
                    <Button size="sm" onClick={() => onAssign?.(manuscript)}>Manage Review</Button>
                    <Button size="sm" variant="outline" onClick={() => onDecide?.(manuscript)}>Decide</Button>
                  </div>
                </div>
              ))}
              {isTruncatedInActiveFilter('resubmitted') ? (
                <div className="text-xs text-muted-foreground">Showing first {ACTIVE_FILTER_RENDER_LIMIT} manuscripts in this stage.</div>
              ) : null}
            </>
          )}

          {/* Under Review */}
          {hasData('under_review') && (!activeFilter || activeFilter === 'under_review') && (
            <>
              {renderSectionHeader('Under Review', getData('under_review').length, 'under_review')}
              {getDisplayItems('under_review').map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-border/60 rounded-lg hover:bg-muted/40">
                  <div>
                    <div className="font-medium text-foreground">{manuscript.title}</div>
                    <div className="text-sm text-muted-foreground">Reviewers: {manuscript.review_count || 0}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-amber-100 text-amber-800 text-sm font-medium rounded-full">In Review</span>
                    <Button size="sm" variant="ghost" onClick={() => onAssign?.(manuscript)}>Manage</Button>
                    <Button size="sm" variant="outline" onClick={() => onDecide?.(manuscript)}>View Decision</Button>
                  </div>
                </div>
              ))}
              {isTruncatedInActiveFilter('under_review') ? (
                <div className="text-xs text-muted-foreground">Showing first {ACTIVE_FILTER_RENDER_LIMIT} manuscripts in this stage.</div>
              ) : null}
            </>
          )}

          {/* Pending Decision */}
          {hasData('pending_decision') && (!activeFilter || activeFilter === 'pending_decision') && (
            <>
              {renderSectionHeader('Pending Decision', getData('pending_decision').length, 'pending_decision')}
              {getDisplayItems('pending_decision').map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-border/60 rounded-lg hover:bg-muted/40">
                  <div>
                    <div className="font-medium text-foreground">{manuscript.title}</div>
                    <div className="text-sm text-muted-foreground">Ready for decision</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-purple-100 text-purple-800 text-sm font-medium rounded-full">Action Req</span>
                    <Button size="sm" onClick={() => onDecide?.(manuscript)}>Make Decision</Button>
                  </div>
                </div>
              ))}
              {isTruncatedInActiveFilter('pending_decision') ? (
                <div className="text-xs text-muted-foreground">Showing first {ACTIVE_FILTER_RENDER_LIMIT} manuscripts in this stage.</div>
              ) : null}
            </>
          )}

          {/* Approved */}
          {hasData('approved') && (!activeFilter || activeFilter === 'approved') && (
            <>
              {renderSectionHeader('Approved (Financial Gate)', getData('approved').length, 'approved')}
              {getDisplayItems('approved').map((manuscript: Manuscript) => {
                const amountRaw = manuscript.invoice_amount
                const amountParsed = typeof amountRaw === 'string' ? Number.parseFloat(amountRaw) : Number(amountRaw)
                const amount = Number.isFinite(amountParsed) ? amountParsed : 0
                const invoiceStatusRaw = (manuscript.invoice_status ?? '').toString().trim()
                const invoiceStatus = invoiceStatusRaw ? invoiceStatusRaw.toLowerCase() : 'unknown'
                const invoiceMissing = amountRaw == null && !invoiceStatusRaw

                const waitingPayment = !invoiceMissing && amount > 0 && invoiceStatus !== 'paid'
                const isPaid = !invoiceMissing && (amount <= 0 || invoiceStatus === 'paid')

                return (
                  <div key={manuscript.id} className="flex items-center justify-between p-4 border border-border/60 rounded-lg hover:bg-muted/40">
                    <div>
                      <div className="font-medium text-foreground">{manuscript.title}</div>
                      <div className="text-sm text-muted-foreground">
                        {invoiceMissing
                          ? 'Invoice missing (accept may not have saved APC)'
                          : waitingPayment
                            ? 'Waiting for Payment'
                            : isPaid
                              ? 'Paid'
                              : 'Ready to Publish'}
                        {!invoiceMissing ? ` • APC: $${amount}` : ''}
                        {!invoiceMissing ? ` • Invoice: ${invoiceStatus}` : ''}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-3 py-1 bg-emerald-100 text-emerald-800 text-sm font-medium rounded-full">
                        {getStatusLabel((manuscript.status || 'approved').toString())}
                      </span>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          window.location.href = `/editor/manuscript/${manuscript.id}`
                        }}
                      >
                        Details
                      </Button>
                      <ProductionUploadDialog
                        manuscriptId={manuscript.id}
                        manuscriptTitle={manuscript.title}
                        onUploaded={() => {
                          reloadPipeline({ silent: true, forceRefresh: true, suppressErrorToast: true })
                        }}
                      />
                      {manuscript.invoice_id && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleRegenerateInvoicePdf(manuscript.invoice_id as string)}
                        >
                          Regenerate Invoice
                        </Button>
                      )}
                      {waitingPayment && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleConfirmPayment(manuscript.id)}
                          data-testid="editor-confirm-payment"
                        >
                          Mark Paid
                        </Button>
                      )}
                      <Button
                        size="sm"
                        disabled={
                          waitingPayment ||
                          (manuscript.status || 'approved').toString().trim().toLowerCase() !== 'proofreading'
                        }
                        title={
                          waitingPayment
                            ? 'Waiting for Payment'
                            : (manuscript.status || 'approved').toString().trim().toLowerCase() !== 'proofreading'
                              ? 'Continue production in Details'
                              : 'Publish'
                        }
                        onClick={() => handlePublish(manuscript.id)}
                        data-testid="editor-publish"
                      >
                        Publish
                      </Button>
                    </div>
                  </div>
                )
              })}
              {isTruncatedInActiveFilter('approved') ? (
                <div className="text-xs text-muted-foreground">Showing first {ACTIVE_FILTER_RENDER_LIMIT} manuscripts in this stage.</div>
              ) : null}
            </>
          )}

          {/* Revision Requested */}
          {hasData('revision_requested') && (!activeFilter || activeFilter === 'revision_requested') && (
            <>
              {renderSectionHeader('Waiting for Author', getData('revision_requested').length, 'revision_requested')}
              {getDisplayItems('revision_requested').map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-border/60 rounded-lg hover:bg-muted/40 opacity-75">
                  <div>
                    <div className="font-medium text-foreground">{manuscript.title}</div>
                    <div className="text-sm text-muted-foreground">
                      Requested: {manuscript.updated_at ? new Date(manuscript.updated_at).toLocaleDateString() : '—'}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-muted text-muted-foreground text-sm font-medium rounded-full">Waiting</span>
                    <Button size="sm" variant="ghost" disabled>View Details</Button>
                  </div>
                </div>
              ))}
              {isTruncatedInActiveFilter('revision_requested') ? (
                <div className="text-xs text-muted-foreground">Showing first {ACTIVE_FILTER_RENDER_LIMIT} manuscripts in this stage.</div>
              ) : null}
            </>
          )}

          {/* Published */}
          {hasData('published') && (!activeFilter || activeFilter === 'published') && (
            <>
              {renderSectionHeader('Published', getData('published').length, 'published')}
              {getDisplayItems('published').map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-border/60 rounded-lg hover:bg-muted/40">
                  <div>
                    <div className="font-medium text-foreground">{manuscript.title}</div>
                    <div className="text-sm text-muted-foreground">Published</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-emerald-100 text-emerald-800 text-sm font-medium rounded-full">Published</span>
                  </div>
                </div>
              ))}
              {isTruncatedInActiveFilter('published') ? (
                <div className="text-xs text-muted-foreground">Showing first {ACTIVE_FILTER_RENDER_LIMIT} manuscripts in this stage.</div>
              ) : null}
            </>
          )}

          {/* Rejected */}
          {hasData('rejected') && (!activeFilter || activeFilter === 'rejected') && (
            <>
              {renderSectionHeader('Rejected', getData('rejected').length, 'rejected')}
              {getDisplayItems('rejected').map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-border/60 rounded-lg hover:bg-muted/40 opacity-80">
                  <div>
                    <div className="font-medium text-foreground">{manuscript.title}</div>
                    <div className="text-sm text-muted-foreground">
                      Rejected: {manuscript.updated_at ? new Date(manuscript.updated_at).toLocaleDateString() : '—'}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-rose-100 text-rose-700 text-sm font-medium rounded-full">Rejected</span>
                  </div>
                </div>
              ))}
              {isTruncatedInActiveFilter('rejected') ? (
                <div className="text-xs text-muted-foreground">Showing first {ACTIVE_FILTER_RENDER_LIMIT} manuscripts in this stage.</div>
              ) : null}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
