'use client'

import { useState, useEffect, useRef } from 'react'
import { FileText, Users, CheckCircle2, ArrowRight, Loader2, RefreshCw, Clock } from 'lucide-react'
import { authService } from '@/services/auth'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import ProductionUploadDialog from '@/components/ProductionUploadDialog'

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

interface EditorPipelineProps {
  onAssign?: (manuscript: Manuscript) => void
  onDecide?: (manuscript: Manuscript) => void
  refreshKey?: number
}

export default function EditorPipeline({ onAssign, onDecide, refreshKey }: EditorPipelineProps) {
  const [pipelineData, setPipelineData] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState<PipelineStage | null>(null)
  const listRef = useRef<HTMLDivElement | null>(null)

  const reloadPipeline = async () => {
    const token = await authService.getAccessToken()
    const response = await fetch('/api/v1/editor/pipeline', {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    })
    const data = await response.json()
    if (data.success) setPipelineData(data.data)
  }

  useEffect(() => {
    async function fetchPipelineData() {
      try {
        await reloadPipeline()
      } catch (error) {
        console.error('Failed to fetch pipeline data:', error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchPipelineData()
  }, [refreshKey])

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
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-slate-600">Loading pipeline data...</span>
      </div>
    )
  }

  const renderSectionHeader = (title: string, count: number, filter: PipelineStage) => (
    (activeFilter === filter || !activeFilter) && (
      <div className="flex items-center justify-between mb-2 mt-6 first:mt-0">
        <h4 className="text-md font-semibold text-slate-700 flex items-center gap-2">
          {title}
          <span className="bg-slate-100 text-slate-600 py-0.5 px-2 rounded-full text-xs">{count}</span>
        </h4>
      </div>
    )
  )

  const hasData = (stage: string) => (pipelineData?.[stage] || []).length > 0
  const getData = (stage: string) => (pipelineData?.[stage] || [])

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
        body: JSON.stringify({ manuscript_id: manuscriptId }),
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
      setPipelineData((prev: any) => prev) // keep state shape
      // 刷新数据
      setIsLoading(true)
      await reloadPipeline()
    } catch (error) {
      toast.error('Publish failed. Please try again.', { id: toastId })
    } finally {
      setIsLoading(false)
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
      setIsLoading(true)
      await reloadPipeline()
    } catch {
      toast.error('Confirm payment failed. Please try again.', { id: toastId })
    } finally {
      setIsLoading(false)
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
      setIsLoading(true)
      await reloadPipeline()
    } catch {
      toast.error('Regenerate failed. Please try again.', { id: toastId })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-6" data-testid="editor-pipeline">
      <h2 className="text-2xl font-bold text-slate-900">Manuscript Pipeline</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 待质检 */}
        <button
          type="button"
          onClick={() => handleFilterClick('pending_quality')}
          className={`text-left bg-white rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'pending_quality'
              ? 'border-blue-400 bg-blue-50'
              : 'border-slate-200 hover:border-blue-200 hover:bg-blue-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Pending Quality</h3>
            <FileText className="h-5 w-5 text-blue-600" />
          </div>
          <div className="text-3xl font-bold text-blue-600 mb-2">
            {getData('pending_quality').length}
          </div>
          <div className="text-sm text-slate-500">New submissions</div>
        </button>

        {/* Resubmitted */}
        <button
          type="button"
          onClick={() => handleFilterClick('resubmitted')}
          className={`text-left bg-white rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'resubmitted'
              ? 'border-indigo-400 bg-indigo-50'
              : 'border-slate-200 hover:border-indigo-200 hover:bg-indigo-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Resubmitted</h3>
            <RefreshCw className="h-5 w-5 text-indigo-600" />
          </div>
          <div className="text-3xl font-bold text-indigo-600 mb-2">
            {getData('resubmitted').length}
          </div>
          <div className="text-sm text-slate-500">Revisions received</div>
        </button>

        {/* 评审中 */}
        <button
          type="button"
          onClick={() => handleFilterClick('under_review')}
          className={`text-left bg-white rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'under_review'
              ? 'border-amber-400 bg-amber-50'
              : 'border-slate-200 hover:border-amber-200 hover:bg-amber-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Under Review</h3>
            <Users className="h-5 w-5 text-amber-600" />
          </div>
          <div className="text-3xl font-bold text-amber-600 mb-2">
            {getData('under_review').length}
          </div>
          <div className="text-sm text-slate-500">In peer review</div>
        </button>

        {/* 待录用 */}
        <button
          type="button"
          onClick={() => handleFilterClick('pending_decision')}
          className={`text-left bg-white rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'pending_decision'
              ? 'border-purple-400 bg-purple-50'
              : 'border-slate-200 hover:border-purple-200 hover:bg-purple-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Pending Decision</h3>
            <CheckCircle2 className="h-5 w-5 text-purple-600" />
          </div>
          <div className="text-3xl font-bold text-purple-600 mb-2">
            {getData('pending_decision').length}
          </div>
          <div className="text-sm text-slate-500">Ready for decision</div>
        </button>

        {/* Approved (Waiting for Payment / Ready to Publish) */}
        <button
          type="button"
          onClick={() => handleFilterClick('approved')}
          className={`text-left bg-white rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'approved'
              ? 'border-emerald-400 bg-emerald-50'
              : 'border-slate-200 hover:border-emerald-200 hover:bg-emerald-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Approved</h3>
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          </div>
          <div className="text-3xl font-bold text-emerald-600 mb-2">
            {getData('approved').length}
          </div>
          <div className="text-sm text-slate-500">Waiting for payment / publish</div>
        </button>

        {/* Revision Requested (Waiting) */}
        <button
          type="button"
          onClick={() => handleFilterClick('revision_requested')}
          className={`text-left bg-white rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'revision_requested'
              ? 'border-slate-400 bg-slate-50'
              : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Waiting for Author</h3>
            <Clock className="h-5 w-5 text-slate-600" />
          </div>
          <div className="text-3xl font-bold text-slate-600 mb-2">
            {getData('revision_requested').length}
          </div>
          <div className="text-sm text-slate-500">Revision requested</div>
        </button>

        {/* 已发布 */}
        <button
          type="button"
          onClick={() => handleFilterClick('published')}
          className={`text-left bg-white rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'published'
              ? 'border-emerald-400 bg-emerald-50'
              : 'border-slate-200 hover:border-emerald-200 hover:bg-emerald-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Published</h3>
            <ArrowRight className="h-5 w-5 text-emerald-600" />
          </div>
          <div className="text-3xl font-bold text-emerald-600 mb-2">
            {getData('published').length}
          </div>
          <div className="text-sm text-slate-500">Completed</div>
        </button>

        {/* 已拒稿 */}
        <button
          type="button"
          onClick={() => handleFilterClick('rejected')}
          className={`text-left bg-white rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'rejected'
              ? 'border-rose-400 bg-rose-50'
              : 'border-slate-200 hover:border-rose-200 hover:bg-rose-50/50'
          }`}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Rejected</h3>
            <FileText className="h-5 w-5 text-rose-600" />
          </div>
          <div className="text-3xl font-bold text-rose-600 mb-2">
            {getData('rejected').length}
          </div>
          <div className="text-sm text-slate-500">Archived</div>
        </button>
      </div>

      {/* 详细列表 */}
      <div ref={listRef} className="bg-white rounded-xl border border-slate-200 p-6" data-testid="editor-pipeline-list">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h3 className="text-lg font-semibold text-slate-900">Recent Activity</h3>
          {activeFilter && (
            <Button variant="ghost" size="sm" onClick={clearFilter}>
              Clear Filter
            </Button>
          )}
        </div>
        
        <div className="space-y-2">
          {/* Empty States */}
          {activeFilter && !hasData(activeFilter) && (
             <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center text-slate-500">
               No manuscripts in {activeFilter.replace('_', ' ')}.
             </div>
          )}

          {/* Pending Quality */}
          {hasData('pending_quality') && (!activeFilter || activeFilter === 'pending_quality') && (
            <>
              {renderSectionHeader('Pending Quality Check', getData('pending_quality').length, 'pending_quality')}
              {getData('pending_quality').slice(0, activeFilter ? undefined : 3).map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
                  <div>
                    <div className="font-medium text-slate-900">{manuscript.title}</div>
                    <div className="text-sm text-slate-500">
                      Submitted: {manuscript.created_at ? new Date(manuscript.created_at).toLocaleDateString() : '—'}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">New</span>
                    <Button size="sm" onClick={() => onAssign?.(manuscript)}>Assign Reviewers</Button>
                  </div>
                </div>
              ))}
            </>
          )}

          {/* Resubmitted */}
          {hasData('resubmitted') && (!activeFilter || activeFilter === 'resubmitted') && (
            <>
              {renderSectionHeader('Resubmitted Revisions', getData('resubmitted').length, 'resubmitted')}
              {getData('resubmitted').slice(0, activeFilter ? undefined : 3).map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
                  <div>
                    <div className="font-medium text-slate-900">{manuscript.title}</div>
                    <div className="text-sm text-slate-500">
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
            </>
          )}

          {/* Under Review */}
          {hasData('under_review') && (!activeFilter || activeFilter === 'under_review') && (
            <>
              {renderSectionHeader('Under Review', getData('under_review').length, 'under_review')}
              {getData('under_review').slice(0, activeFilter ? undefined : 3).map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
                  <div>
                    <div className="font-medium text-slate-900">{manuscript.title}</div>
                    <div className="text-sm text-slate-500">Reviewers: {manuscript.review_count || 0}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-amber-100 text-amber-800 text-sm font-medium rounded-full">In Review</span>
                    <Button size="sm" variant="ghost" onClick={() => onAssign?.(manuscript)}>Manage</Button>
                    <Button size="sm" variant="outline" onClick={() => onDecide?.(manuscript)}>View Decision</Button>
                  </div>
                </div>
              ))}
            </>
          )}

          {/* Pending Decision */}
          {hasData('pending_decision') && (!activeFilter || activeFilter === 'pending_decision') && (
            <>
              {renderSectionHeader('Pending Decision', getData('pending_decision').length, 'pending_decision')}
              {getData('pending_decision').slice(0, activeFilter ? undefined : 3).map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
                  <div>
                    <div className="font-medium text-slate-900">{manuscript.title}</div>
                    <div className="text-sm text-slate-500">Ready for decision</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-purple-100 text-purple-800 text-sm font-medium rounded-full">Action Req</span>
                    <Button size="sm" onClick={() => onDecide?.(manuscript)}>Make Decision</Button>
                  </div>
                </div>
              ))}
            </>
          )}

          {/* Approved */}
          {hasData('approved') && (!activeFilter || activeFilter === 'approved') && (
            <>
              {renderSectionHeader('Approved (Financial Gate)', getData('approved').length, 'approved')}
              {getData('approved').slice(0, activeFilter ? undefined : 3).map((manuscript: Manuscript) => {
                const amountRaw = manuscript.invoice_amount
                const amountParsed = typeof amountRaw === 'string' ? Number.parseFloat(amountRaw) : Number(amountRaw)
                const amount = Number.isFinite(amountParsed) ? amountParsed : 0
                const invoiceStatusRaw = (manuscript.invoice_status ?? '').toString().trim()
                const invoiceStatus = invoiceStatusRaw ? invoiceStatusRaw.toLowerCase() : 'unknown'
                const invoiceMissing = amountRaw == null && !invoiceStatusRaw

                const waitingPayment = !invoiceMissing && amount > 0 && invoiceStatus !== 'paid'
                const isPaid = !invoiceMissing && (amount <= 0 || invoiceStatus === 'paid')

                return (
                  <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
                    <div>
                      <div className="font-medium text-slate-900">{manuscript.title}</div>
                      <div className="text-sm text-slate-500">
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
                      <span className="px-3 py-1 bg-emerald-100 text-emerald-800 text-sm font-medium rounded-full">Approved</span>
                      <ProductionUploadDialog
                        manuscriptId={manuscript.id}
                        manuscriptTitle={manuscript.title}
                        onUploaded={() => {
                          setIsLoading(true)
                          reloadPipeline().finally(() => setIsLoading(false))
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
                        disabled={waitingPayment}
                        title={waitingPayment ? 'Waiting for Payment' : 'Publish'}
                        onClick={() => handlePublish(manuscript.id)}
                        data-testid="editor-publish"
                      >
                        Publish
                      </Button>
                    </div>
                  </div>
                )
              })}
            </>
          )}

          {/* Revision Requested */}
          {hasData('revision_requested') && (!activeFilter || activeFilter === 'revision_requested') && (
            <>
              {renderSectionHeader('Waiting for Author', getData('revision_requested').length, 'revision_requested')}
              {getData('revision_requested').slice(0, activeFilter ? undefined : 3).map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50 opacity-75">
                  <div>
                    <div className="font-medium text-slate-900">{manuscript.title}</div>
                    <div className="text-sm text-slate-500">
                      Requested: {manuscript.updated_at ? new Date(manuscript.updated_at).toLocaleDateString() : '—'}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-slate-100 text-slate-600 text-sm font-medium rounded-full">Waiting</span>
                    <Button size="sm" variant="ghost" disabled>View Details</Button>
                  </div>
                </div>
              ))}
            </>
          )}

          {/* Published */}
          {hasData('published') && (!activeFilter || activeFilter === 'published') && (
            <>
              {renderSectionHeader('Published', getData('published').length, 'published')}
              {getData('published').slice(0, activeFilter ? undefined : 3).map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
                  <div>
                    <div className="font-medium text-slate-900">{manuscript.title}</div>
                    <div className="text-sm text-slate-500">Published</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-emerald-100 text-emerald-800 text-sm font-medium rounded-full">Published</span>
                  </div>
                </div>
              ))}
            </>
          )}

          {/* Rejected */}
          {hasData('rejected') && (!activeFilter || activeFilter === 'rejected') && (
            <>
              {renderSectionHeader('Rejected', getData('rejected').length, 'rejected')}
              {getData('rejected').slice(0, activeFilter ? undefined : 3).map((manuscript: any) => (
                <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50 opacity-80">
                  <div>
                    <div className="font-medium text-slate-900">{manuscript.title}</div>
                    <div className="text-sm text-slate-500">
                      Rejected: {manuscript.updated_at ? new Date(manuscript.updated_at).toLocaleDateString() : '—'}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-rose-100 text-rose-700 text-sm font-medium rounded-full">Rejected</span>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
