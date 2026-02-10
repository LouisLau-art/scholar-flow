'use client'

import { useEffect, useState, useMemo, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import { EditorApi } from '@/services/editorApi'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from 'sonner'
import { Loader2, Calendar, User, DollarSign, ArrowRight, AlertTriangle } from 'lucide-react'
import { InvoiceInfoModal, type InvoiceInfoForm } from '@/components/editor/InvoiceInfoModal'
import { ReviewerAssignmentSearch } from '@/components/editor/ReviewerAssignmentSearch'
import { ProductionStatusCard } from '@/components/editor/ProductionStatusCard'
import { getStatusLabel, getStatusColor } from '@/lib/statusStyles'
import { BindingOwnerDropdown } from '@/components/editor/BindingOwnerDropdown'
import { InternalNotebook } from '@/components/editor/InternalNotebook'
import { InternalTasksPanel } from '@/components/editor/InternalTasksPanel'
import { AuditLogTimeline } from '@/components/editor/AuditLogTimeline'
import { FileHubCard, type FileItem } from '@/components/editor/FileHubCard'
import { filterFilesByType, type ManuscriptFile } from './utils'
import { format } from 'date-fns'
import type { EditorRbacContext } from '@/types/rbac'
import { deriveEditorCapability } from '@/lib/rbac'

// ... (Reuse types and logic)
type ManuscriptDetail = {
  id: string
  title?: string | null
  abstract?: string | null
  status?: string | null
  created_at?: string | null
  updated_at?: string | null
  final_pdf_path?: string | null
  owner?: { full_name?: string | null; email?: string | null } | null
  editor?: { full_name?: string | null; email?: string | null } | null
  invoice_metadata?: { authors?: string; affiliation?: string; apc_amount?: number; funding_info?: string } | null
  invoice?: { status?: string | null; amount?: number | string | null } | null
  signed_files?: any
  files?: ManuscriptFile[] | null
  journals?: { title?: string } | null
  role_queue?: {
    current_role?: string | null
    current_assignee?: { id: string; full_name?: string | null; email?: string | null } | null
    assigned_at?: string | null
    technical_completed_at?: string | null
    academic_completed_at?: string | null
  } | null
  precheck_timeline?: Array<{
    id: string
    created_at?: string | null
    payload?: { action?: string; decision?: string } | null
    comment?: string | null
  }> | null
  reviewer_invites?: Array<{
    id: string
    reviewer_name?: string | null
    reviewer_email?: string | null
    status: string
    due_at?: string | null
    invited_at?: string | null
    opened_at?: string | null
    accepted_at?: string | null
    declined_at?: string | null
    submitted_at?: string | null
    decline_reason?: string | null
  }> | null
  task_summary?: {
    open_tasks_count?: number
    overdue_tasks_count?: number
    is_overdue?: boolean
    nearest_due_at?: string | null
  } | null
}

function allowedNext(status: string): string[] {
  const s = (status || '').toLowerCase()
  if (s === 'pre_check') return ['under_review', 'minor_revision']
  if (s === 'under_review') return ['decision']
  if (s === 'resubmitted') return ['under_review', 'decision']
  if (s === 'decision') return ['decision_done']
  if (s === 'decision_done') return ['approved', 'major_revision', 'minor_revision', 'rejected']
  return []
}

function getNextActionCard(
  manuscript: ManuscriptDetail,
  capability: ReturnType<typeof deriveEditorCapability>
): { phase: string; title: string; description: string; blockers: string[] } {
  const status = String(manuscript.status || '').toLowerCase()
  const blockers: string[] = []
  const amount = Number(manuscript.invoice?.amount ?? manuscript.invoice_metadata?.apc_amount ?? 0)
  const invoiceStatus = String(manuscript.invoice?.status || '').toLowerCase()

  if (status === 'pre_check') {
    return {
      phase: 'Pre-check',
      title: '先完成入口技术审查，再决定分配 AE 或退回作者',
      description: '当前阶段不应直接进入终审动作。请先确认材料完整性与格式规范。',
      blockers,
    }
  }

  if (status === 'under_review' || status === 'resubmitted') {
    if ((manuscript.reviewer_invites || []).length === 0) blockers.push('尚未发出审稿邀请')
    return {
      phase: 'External Review',
      title: '推进外审并收集可决策意见',
      description: 'AE 需跟进邀请接受率与审稿提交率，达到阈值后进入 Decision。',
      blockers,
    }
  }

  if (status === 'decision' || status === 'decision_done') {
    if (!(capability.canRecordFirstDecision || capability.canSubmitFinalDecision)) {
      blockers.push('当前账号无决策权限')
    }
    return {
      phase: 'Decision',
      title: '在 Decision Workspace 完成首轮/终轮学术决策',
      description: '请确保审稿依据充分并写明决策理由，关键状态流转需保留审计痕迹。',
      blockers,
    }
  }

  if (['approved', 'layout', 'english_editing', 'proofreading'].includes(status)) {
    if (amount > 0 && invoiceStatus !== 'paid') blockers.push('Payment Gate 未满足（发票未确认 paid）')
    if (!manuscript.final_pdf_path) blockers.push('Proof Gate 未满足（final PDF 尚未上传）')
    return {
      phase: 'Production',
      title: '并行推进 Production 与 Finance，满足双门禁后发布',
      description: '发布前必须同时满足付款确认与校对完成条件。',
      blockers,
    }
  }

  if (status === 'published') {
    return {
      phase: 'Published',
      title: '稿件已发布',
      description: '当前进入公开传播阶段，可继续跟踪下载与引用。',
      blockers,
    }
  }

  return {
    phase: 'Workflow',
    title: '请按当前状态继续推进流程',
    description: '若出现状态异常，请先在审计日志核对最近一次流转。',
    blockers,
  }
}

export default function EditorManuscriptDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = String((params as any).id || '')

  const [loading, setLoading] = useState(true)
  const [ms, setMs] = useState<ManuscriptDetail | null>(null)
  const [rbacContext, setRbacContext] = useState<EditorRbacContext | null>(null)
  const [transitioning, setTransitioning] = useState<string | null>(null)

  const [invoiceOpen, setInvoiceOpen] = useState(false)
  const [invoiceForm, setInvoiceForm] = useState<InvoiceInfoForm>({
    authors: '',
    affiliation: '',
    apcAmount: '',
    fundingInfo: '',
  })
  const [invoiceSaving, setInvoiceSaving] = useState(false)
  const capability = useMemo(() => deriveEditorCapability(rbacContext), [rbacContext])

  const loadRbacContext = useCallback(async () => {
    const rbacRes = await EditorApi.getRbacContext()
    if (rbacRes?.success && rbacRes?.data) {
      setRbacContext(rbacRes.data)
    } else {
      setRbacContext(null)
    }
  }, [])

  const refreshDetail = useCallback(async () => {
    if (!id) return
    try {
      const detailRes = await EditorApi.getManuscriptDetail(id)
      if (!detailRes?.success) {
        throw new Error(detailRes?.detail || detailRes?.message || 'Manuscript not found')
      }
      const detail = detailRes.data
      setMs(detail)

      const meta = (detail?.invoice_metadata as any) || {}
      const ownerFallback = String(detail?.owner?.full_name || detail?.owner?.email || '').trim()
      setInvoiceForm({
        authors: String(meta.authors || ownerFallback || ''),
        affiliation: String(meta.affiliation || ''),
        apcAmount: meta.apc_amount != null ? String(meta.apc_amount) : '',
        fundingInfo: String(meta.funding_info || ''),
      })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to load manuscript')
      setMs(null)
    }
  }, [id])

  async function load() {
    try {
      setLoading(true)
      const detailRes = await EditorApi.getManuscriptDetail(id)
      if (!detailRes?.success) throw new Error(detailRes?.detail || detailRes?.message || 'Manuscript not found')
      const detail = detailRes.data
      setMs(detail)
      await loadRbacContext()

      const meta = (detail?.invoice_metadata as any) || {}
      const ownerFallback = String(detail?.owner?.full_name || detail?.owner?.email || '').trim()
      setInvoiceForm({
        authors: String(meta.authors || ownerFallback || ''),
        affiliation: String(meta.affiliation || ''),
        apcAmount: meta.apc_amount != null ? String(meta.apc_amount) : '',
        fundingInfo: String(meta.funding_info || ''),
      })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to load manuscript')
      setMs(null)
      setRbacContext(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!id) return
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  // --- Derived State ---
  const status = String(ms?.status || '')
  const statusLower = status.toLowerCase()
  const isPostAcceptance = ['approved', 'layout', 'english_editing', 'proofreading', 'published'].includes(statusLower)
  const nextStatuses = useMemo(() => allowedNext(status), [status])
  const canAssignReviewersStage = ['under_review', 'resubmitted'].includes(statusLower)
  const canOpenDecisionWorkspaceStage = ['under_review', 'resubmitted', 'decision', 'decision_done'].includes(statusLower)
  const showDirectStatusTransitions = !isPostAcceptance && !['published', 'rejected'].includes(statusLower)
  const displayAuthors =
    String(invoiceForm.authors || '').trim() ||
    String(ms?.owner?.full_name || '').trim() ||
    String(ms?.owner?.email || '').trim() ||
    '—'
  const nextAction = useMemo(() => getNextActionCard((ms || {}) as ManuscriptDetail, capability), [ms, capability])

  // --- File Processing ---
  const mapFile = (f: ManuscriptFile, type: FileItem['type']): FileItem => ({
    id: String(f.id),
    label: f.label || 'Unknown File',
    type,
    url: f.signed_url || undefined,
    date: f.created_at ? format(new Date(f.created_at), 'yyyy-MM-dd') : undefined,
  })

  const fileHubProps = useMemo(() => {
    const rawFiles = ms?.files || []
    return {
      manuscriptFiles: filterFilesByType(rawFiles, 'manuscript').map((f) => mapFile(f, 'pdf')),
      coverFiles: filterFilesByType(rawFiles, 'cover_letter').map((f) => mapFile(f, 'doc')),
      reviewFiles: filterFilesByType(rawFiles, 'review_attachment').map((f) => mapFile(f, 'pdf')),
    }
  }, [ms?.files])


  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50">
        <SiteHeader />
        <div className="mx-auto max-w-7xl px-4 py-16 flex items-center justify-center text-slate-500 gap-2">
          <Loader2 className="h-5 w-5 animate-spin" /> Loading…
        </div>
      </div>
    )
  }

  if (!ms) {
    return (
      <div className="min-h-screen bg-slate-50">
        <SiteHeader />
        <div className="mx-auto max-w-7xl px-4 py-16 text-slate-600">Manuscript not found.</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      <SiteHeader />
      
      {/* Top Header Sticky */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-10 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="flex items-center gap-3 overflow-hidden">
            <span className="bg-blue-600 text-white px-2 py-1 rounded text-xs font-bold whitespace-nowrap">
                {ms.journals?.title?.substring(0, 4).toUpperCase() || 'MS'}
            </span>
            <h1 className="font-bold text-slate-900 truncate max-w-xl text-lg" title={ms.title || ''}>
                {ms.title || 'Untitled Manuscript'}
            </h1>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(status)}`}>
                {getStatusLabel(status)}
            </span>
        </div>
        <div className="text-xs text-slate-500 flex items-center gap-2 whitespace-nowrap">
            <Calendar className="h-3 w-3" />
            Updated: <span className="font-mono font-medium text-slate-700">{ms.updated_at ? format(new Date(ms.updated_at), 'yyyy-MM-dd HH:mm') : '-'}</span>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] px-4 py-8 grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN (8/12) */}
        <div className="lg:col-span-8 space-y-6">
            
            {/* 1. Basic Info Card (Metadata) */}
            <Card className="shadow-sm">
                <CardHeader className="py-4 border-b bg-slate-50/30">
                     <CardTitle className="text-sm font-bold uppercase tracking-wide flex items-center gap-2 text-slate-700">
                        <User className="h-4 w-4" /> Metadata & Staff
                     </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-6">
                        <div>
                            <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Authors</div>
                            <div className="font-medium text-slate-900 text-sm">
                                {displayAuthors}
                            </div>
                            <div className="text-xs text-slate-500 mt-1">{invoiceForm.affiliation || 'No affiliation'}</div>
                        </div>
                        <div className="text-right">
                             <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Submitted</div>
                             <div className="font-medium text-slate-900 text-sm">
                                {ms.created_at ? format(new Date(ms.created_at), 'yyyy-MM-dd') : '-'}
                             </div>
                        </div>
                    </div>
                    
                    {/* Staff Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-lg border border-slate-100">
                        {/* Owner Binding */}
                        <div>
                            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Owner (Sales)</div>
                            <BindingOwnerDropdown
                              manuscriptId={id}
                              currentOwner={ms.owner as any}
                              onBound={load}
                              disabled={!capability.canBindOwner}
                            />
                        </div>
                        
                        {/* AE Info */}
                        <div>
                            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Assistant Editor</div>
                            <div className="flex items-center gap-2 h-9">
                                {ms.editor ? (
                                    <>
                                        <div className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-bold">
                                            {(ms.editor.full_name || ms.editor.email || 'E').substring(0, 1).toUpperCase()}
                                        </div>
                                        <span className="text-sm font-medium truncate">{ms.editor.full_name || ms.editor.email}</span>
                                    </>
                                ) : (
                                    <span className="text-sm text-slate-400 italic">Unassigned</span>
                                )}
                            </div>
                        </div>

                        {/* Finance Status */}
                        <div
                          className={`p-1 rounded -m-1 transition ${capability.canUpdateInvoiceInfo ? 'cursor-pointer hover:bg-slate-100' : 'cursor-not-allowed opacity-70'}`}
                          onClick={() => {
                            if (!capability.canUpdateInvoiceInfo) {
                              toast.error('You do not have permission to edit invoice info.')
                              return
                            }
                            setInvoiceOpen(true)
                          }}
                        >
                            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                                APC Status <DollarSign className="h-3 w-3" />
                            </div>
                            <div className="flex items-center gap-2 h-9">
                                {ms.invoice?.status === 'paid' ? (
                                    <span className="text-sm font-bold text-green-600 flex items-center gap-1">
                                        PAID <span className="text-xs font-normal text-slate-500">(${ms.invoice.amount})</span>
                                    </span>
                                ) : (
                                    <span className="text-sm font-bold text-orange-600 flex items-center gap-1">
                                        {ms.invoice?.status ? ms.invoice.status.toUpperCase() : 'PENDING'} 
                                        <span className="text-xs font-normal text-slate-500">(${invoiceForm.apcAmount || '0'})</span>
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* 2. File Hub */}
            <FileHubCard 
                manuscriptId={id} 
                manuscriptFiles={fileHubProps.manuscriptFiles}
                coverFiles={fileHubProps.coverFiles}
                reviewFiles={fileHubProps.reviewFiles}
                onUploadReviewFile={load}
            />

            {/* 3. Internal Notebook */}
            <div className="h-[500px]">
                <InternalNotebook manuscriptId={id} currentUserId={rbacContext?.user_id} onCommentPosted={refreshDetail} />
            </div>

            {/* 4. Internal Tasks */}
            <InternalTasksPanel manuscriptId={id} onChanged={refreshDetail} />

        </div>

        {/* RIGHT COLUMN (4/12) */}
        <div className="lg:col-span-4 space-y-6">
            <Card className="shadow-sm border-slate-200">
                <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center justify-between">
                      <span>Next Action</span>
                      <Badge variant="secondary">{nextAction.phase}</Badge>
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                    <div className="text-sm font-semibold text-slate-900">{nextAction.title}</div>
                    <div className="text-sm text-slate-600">{nextAction.description}</div>
                    {nextAction.blockers.length > 0 && (
                      <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 space-y-1">
                        <div className="text-xs font-semibold text-rose-700 flex items-center gap-1">
                          <AlertTriangle className="h-3.5 w-3.5" />
                          Blocking Conditions
                        </div>
                        {nextAction.blockers.map((item) => (
                          <div key={item} className="text-xs text-rose-700">
                            - {item}
                          </div>
                        ))}
                      </div>
                    )}
                </CardContent>
            </Card>
            
            {/* Action Panel / Workflow */}
            <Card className="border-t-4 border-t-purple-500 shadow-sm">
                <CardHeader>
                    <CardTitle className="text-lg">Editorial Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Reviewer Assignment */}
                    {!isPostAcceptance && canAssignReviewersStage && (
                        <div className="pt-2 pb-4 border-b border-slate-100">
                            <div className="text-xs font-semibold text-slate-500 mb-2">ASSIGN REVIEWERS</div>
                            <ReviewerAssignmentSearch
                              manuscriptId={id}
                              onChanged={load}
                              disabled={!capability.canRecordFirstDecision}
                            />
                        </div>
                    )}
                    {!isPostAcceptance && !canAssignReviewersStage && (
                      <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                        当前阶段不开放审稿人分配。请先按流程推进到 `under_review / resubmitted`。
                      </div>
                    )}

                    {!isPostAcceptance && canOpenDecisionWorkspaceStage && (
                      <Button
                        className="w-full justify-between"
                        variant="secondary"
                        disabled={!(capability.canRecordFirstDecision || capability.canSubmitFinalDecision)}
                        onClick={() => {
                          router.push(`/editor/decision/${encodeURIComponent(id)}`)
                        }}
                      >
                        Open Decision Workspace
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    )}
                    {!isPostAcceptance && !canOpenDecisionWorkspaceStage && (
                      <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                        Decision Workspace 仅在 `under_review / resubmitted / decision / decision_done` 阶段开放。
                      </div>
                    )}

                    {/* Status Transitions */}
                    {isPostAcceptance ? (
                        <div className="space-y-3">
                            <Button
                              className="w-full justify-between"
                              variant="secondary"
                              onClick={() => {
                                router.push(`/editor/production/${encodeURIComponent(id)}`)
                              }}
                            >
                              Open Production Workspace
                              <ArrowRight className="h-4 w-4" />
                            </Button>
                            <ProductionStatusCard
                                manuscriptId={id}
                                status={statusLower || 'approved'}
                                finalPdfPath={ms?.final_pdf_path}
                                invoice={ms?.invoice}
                                onStatusChange={(next) => {
                                    setMs((prev) => (prev ? { ...prev, status: next } : prev))
                                }}
                                onReload={load}
                            />
                        </div>
                    ) : showDirectStatusTransitions ? (
                        <div className="space-y-2">
                             <div className="text-xs font-semibold text-slate-500 mb-2">CHANGE STATUS</div>
                             {nextStatuses.length === 0 ? (
                                <div className="text-sm text-slate-400 italic">No next status available.</div>
                             ) : (
                                nextStatuses.map((s) => (
                                    <Button
                                        key={s}
                                        className="w-full justify-between"
                                        variant="outline"
                                        disabled={transitioning === s}
                                        onClick={async () => {
                                            try {
                                                const confirmText = `确认将状态修改为「${getStatusLabel(s)}」吗？`
                                                if (!window.confirm(confirmText)) return
                                                let comment: string | undefined
                                                if (['minor_revision', 'major_revision', 'rejected', 'approved'].includes(s)) {
                                                  const input = window.prompt(`请输入流转原因（${getStatusLabel(s)}）：`) ?? ''
                                                  if (!input.trim()) {
                                                    toast.error('该流转需要填写原因。')
                                                    return
                                                  }
                                                  comment = input.trim()
                                                }
                                                setTransitioning(s)
                                                const res = await EditorApi.patchManuscriptStatus(id, s, comment)
                                                if (!res?.success) throw new Error(res?.detail || res?.message || 'Failed')
                                                toast.success(`Moved to ${getStatusLabel(s)}`)
                                                await refreshDetail()
                                            } catch (e) {
                                                toast.error(e instanceof Error ? e.message : 'Transition failed')
                                            } finally {
                                                setTransitioning(null)
                                            }
                                        }}
                                    >
                                        <span>Move to {getStatusLabel(s)}</span>
                                        {transitioning === s ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4 opacity-50" />}
                                    </Button>
                                ))
                             )}
                        </div>
                    ) : (
                      <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                        当前状态为流程终态，已关闭手动状态流转。
                      </div>
                    )}
                </CardContent>
            </Card>

            <Card className="shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg">Task SLA Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-600">Open Tasks</span>
                  <span className="font-medium text-slate-900">{ms.task_summary?.open_tasks_count ?? 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-600">Overdue Tasks</span>
                  <span className={`font-medium ${ms.task_summary?.is_overdue ? 'text-rose-700' : 'text-slate-900'}`}>
                    {ms.task_summary?.overdue_tasks_count ?? 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-600">Nearest Due</span>
                  <span className="font-medium text-slate-900">
                    {ms.task_summary?.nearest_due_at ? format(new Date(ms.task_summary.nearest_due_at), 'yyyy-MM-dd HH:mm') : '—'}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Audit Log Timeline */}
            <Card className="shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg">Pre-check Role Queue</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-slate-700">Current Role:</span>{' '}
                    <span className="text-slate-900">{(ms.role_queue?.current_role || '—').replaceAll('_', ' ')}</span>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Current Assignee:</span>{' '}
                    <span className="text-slate-900">
                      {ms.role_queue?.current_assignee?.full_name ||
                        ms.role_queue?.current_assignee?.email ||
                        ms.role_queue?.current_assignee?.id ||
                        '—'}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Assigned At:</span>{' '}
                    <span className="text-slate-900">
                      {ms.role_queue?.assigned_at ? format(new Date(ms.role_queue.assigned_at), 'yyyy-MM-dd HH:mm') : '—'}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Technical Completed:</span>{' '}
                    <span className="text-slate-900">
                      {ms.role_queue?.technical_completed_at
                        ? format(new Date(ms.role_queue.technical_completed_at), 'yyyy-MM-dd HH:mm')
                        : '—'}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Academic Completed:</span>{' '}
                    <span className="text-slate-900">
                      {ms.role_queue?.academic_completed_at
                        ? format(new Date(ms.role_queue.academic_completed_at), 'yyyy-MM-dd HH:mm')
                        : '—'}
                    </span>
                  </div>
                </div>
                {(ms.precheck_timeline || []).length > 0 ? (
                  <div className="mt-4 border-t pt-3 space-y-2">
                    {(ms.precheck_timeline || []).map((event) => (
                      <div key={event.id} className="rounded-md border border-slate-200 p-2 text-xs text-slate-600">
                        <div className="font-medium text-slate-800">
                          {event.payload?.action || 'precheck_event'}
                          {event.payload?.decision ? ` (${event.payload.decision})` : ''}
                        </div>
                        <div>{event.created_at ? format(new Date(event.created_at), 'yyyy-MM-dd HH:mm') : '—'}</div>
                        {event.comment ? <div className="mt-1">{event.comment}</div> : null}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-3 text-xs text-slate-400 italic">No pre-check timeline events.</div>
                )}
              </CardContent>
            </Card>

            {/* Audit Log Timeline */}
            <Card className="shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg">Reviewer Invite Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                {(ms.reviewer_invites || []).length === 0 ? (
                  <div className="text-sm text-slate-400 italic">No reviewer invitations yet.</div>
                ) : (
                  <div className="space-y-3">
                    {(ms.reviewer_invites || []).map((item) => (
                      <div key={item.id} className="rounded-md border border-slate-200 p-3 text-sm">
                        <div className="flex items-center justify-between gap-3">
                          <div className="font-medium text-slate-800 truncate">
                            {item.reviewer_name || item.reviewer_email || item.id}
                          </div>
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold uppercase text-slate-700">
                            {item.status}
                          </span>
                        </div>
                        <div className="mt-2 grid grid-cols-1 gap-1 text-xs text-slate-500">
                          <div>Invited: {item.invited_at ? format(new Date(item.invited_at), 'yyyy-MM-dd HH:mm') : '-'}</div>
                          <div>Opened: {item.opened_at ? format(new Date(item.opened_at), 'yyyy-MM-dd HH:mm') : '-'}</div>
                          <div>Accepted: {item.accepted_at ? format(new Date(item.accepted_at), 'yyyy-MM-dd HH:mm') : '-'}</div>
                          <div>Declined: {item.declined_at ? format(new Date(item.declined_at), 'yyyy-MM-dd HH:mm') : '-'}</div>
                          <div>Submitted: {item.submitted_at ? format(new Date(item.submitted_at), 'yyyy-MM-dd HH:mm') : '-'}</div>
                          <div>Due: {item.due_at ? format(new Date(item.due_at), 'yyyy-MM-dd HH:mm') : '-'}</div>
                          {item.decline_reason ? <div>Decline reason: {item.decline_reason}</div> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Audit Log Timeline */}
            <AuditLogTimeline manuscriptId={id} />

        </div>
      </main>

      {/* Invoice Modal (Hidden) */}
      <InvoiceInfoModal
        open={invoiceOpen}
        onOpenChange={setInvoiceOpen}
        form={invoiceForm}
        onChange={(patch) => setInvoiceForm((prev) => ({ ...prev, ...patch }))}
        saving={invoiceSaving}
        onSave={async () => {
          if (!capability.canUpdateInvoiceInfo) {
            toast.error('You do not have permission to update invoice info.')
            return
          }
          try {
            setInvoiceSaving(true)
            const apc = invoiceForm.apcAmount.trim() ? Number(invoiceForm.apcAmount) : undefined
            const res = await EditorApi.updateInvoiceInfo(id, {
              authors: invoiceForm.authors || undefined,
              affiliation: invoiceForm.affiliation || undefined,
              apc_amount: Number.isFinite(apc as number) ? (apc as number) : undefined,
              funding_info: invoiceForm.fundingInfo || undefined,
            })
            if (!res?.success) throw new Error(res?.detail || res?.message || 'Save failed')
            toast.success('Invoice info updated')
            setInvoiceOpen(false)
            await refreshDetail()
          } catch (e) {
            toast.error(e instanceof Error ? e.message : 'Save failed')
          } finally {
            setInvoiceSaving(false)
          }
        }}
      />
    </div>
  )
}
