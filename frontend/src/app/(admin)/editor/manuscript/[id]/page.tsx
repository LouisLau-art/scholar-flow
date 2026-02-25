'use client'

import { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import dynamic from 'next/dynamic'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import { EditorApi } from '@/services/editorApi'
import { authService } from '@/services/auth'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { toast } from 'sonner'
import { Loader2, ArrowLeft } from 'lucide-react'
import { InvoiceInfoModal, type InvoiceInfoForm } from '@/components/editor/InvoiceInfoModal'
import { getStatusLabel } from '@/lib/statusStyles'
import type { EditorRbacContext } from '@/types/rbac'
import { deriveEditorCapability } from '@/lib/rbac'
import {
  allowedNext,
  buildAuthorResponseHistory,
  buildFileHubProps,
  getNextActionCard,
  normalizeWorkflowStatus,
  type ManuscriptDetail,
} from './helpers'
import {
  AuthorResubmissionHistoryCard,
  DetailTopHeader,
  EditorialActionsCard,
  LatestAuthorResubmissionCard,
  MetadataStaffCard,
  NextActionCard,
  PrecheckRoleQueueCard,
  ReviewerFeedbackSummaryCard,
  TaskSlaSummaryCard,
} from './detail-sections'
import type { ReviewerFeedbackItem } from './types'

const InternalNotebook = dynamic(
  () => import('@/components/editor/InternalNotebook').then((mod) => mod.InternalNotebook),
  { ssr: false }
)
const InternalTasksPanel = dynamic(
  () => import('@/components/editor/InternalTasksPanel').then((mod) => mod.InternalTasksPanel),
  { ssr: false }
)
const AuditLogTimeline = dynamic(
  () => import('@/components/editor/AuditLogTimeline').then((mod) => mod.AuditLogTimeline),
  { ssr: false }
)
const FileHubCard = dynamic(
  () => import('@/components/editor/FileHubCard').then((mod) => mod.FileHubCard),
  { ssr: false }
)

const DEFERRED_BLOCK_TIMEOUT_MS = 8_000

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number, timeoutMessage: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error(timeoutMessage)), timeoutMs)
    promise
      .then((value) => resolve(value))
      .catch((error) => reject(error))
      .finally(() => window.clearTimeout(timer))
  })
}

export default function EditorManuscriptDetailPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const id = String((params as any).id || '')
  const from = String(searchParams?.get('from') || '').trim().toLowerCase()
  const fallbackPath =
    from === 'intake'
      ? '/editor/intake'
      : from === 'workspace'
      ? '/editor/workspace'
      : from === 'managing-workspace'
      ? '/editor/managing-workspace'
      : from === 'academic'
      ? '/editor/academic'
      : '/editor/process'

  const [loading, setLoading] = useState(true)
  const [ms, setMs] = useState<ManuscriptDetail | null>(null)
  const [rbacContext, setRbacContext] = useState<EditorRbacContext | null>(null)
  const [transitioning, setTransitioning] = useState<string | null>(null)
  const [pendingTransition, setPendingTransition] = useState<string | null>(null)
  const [transitionDialogOpen, setTransitionDialogOpen] = useState(false)
  const [transitionReason, setTransitionReason] = useState('')
  const [viewerEmail, setViewerEmail] = useState<string>('')
  const [reviewReports, setReviewReports] = useState<ReviewerFeedbackItem[]>([])
  const [reviewsLoading, setReviewsLoading] = useState(false)
  const [reviewsError, setReviewsError] = useState<string | null>(null)
  const reviewCardRef = useRef<HTMLDivElement | null>(null)
  const [reviewsActivated, setReviewsActivated] = useState(false)
  const [reviewsLoadedOnce, setReviewsLoadedOnce] = useState(false)

  const [invoiceOpen, setInvoiceOpen] = useState(false)
  const [invoiceForm, setInvoiceForm] = useState<InvoiceInfoForm>({
    authors: '',
    affiliation: '',
    apcAmount: '',
    fundingInfo: '',
  })
  const [invoiceSaving, setInvoiceSaving] = useState(false)
  const cardsSectionRef = useRef<HTMLDivElement | null>(null)
  const [cardsActivated, setCardsActivated] = useState(false)
  const [cardsLoading, setCardsLoading] = useState(false)
  const [cardsError, setCardsError] = useState<string | null>(null)
  const capability = useMemo(() => deriveEditorCapability(rbacContext), [rbacContext])
  const normalizedRoles = useMemo(() => rbacContext?.normalized_roles || [], [rbacContext])
  const canManualStatusTransition = useMemo(
    () => normalizedRoles.includes('admin') || normalizedRoles.includes('managing_editor'),
    [normalizedRoles]
  )
  const canAssignAE = useMemo(
    () => normalizedRoles.includes('managing_editor') || normalizedRoles.includes('admin'),
    [normalizedRoles]
  )
  const canOpenProductionWorkspace = useMemo(
    () =>
      normalizedRoles.includes('admin') ||
      normalizedRoles.includes('managing_editor') ||
      normalizedRoles.includes('editor_in_chief') ||
      normalizedRoles.includes('production_editor'),
    [normalizedRoles]
  )
  const currentAeId = String(
    ms?.assistant_editor_id || ms?.role_queue?.current_assignee?.id || ''
  ).trim()
  const currentAeName = String(
    ms?.role_queue?.current_assignee?.full_name ||
      ms?.role_queue?.current_assignee?.email ||
      ms?.assistant_editor?.full_name ||
      ms?.assistant_editor?.email ||
      ''
  ).trim()
  const requiresTransitionReason = useMemo(() => {
    const target = String(pendingTransition || '').toLowerCase()
    return ['minor_revision', 'major_revision', 'rejected', 'approved'].includes(target)
  }, [pendingTransition])

  const applyDetail = useCallback((detail: ManuscriptDetail) => {
    setMs(detail)
    const meta = (detail?.invoice_metadata as any) || {}
    const authorNameFallback = String(
      detail?.author?.full_name || detail?.author?.email || detail?.owner?.full_name || detail?.owner?.email || ''
    ).trim()
    const authorAffiliationFallback = String(detail?.author?.affiliation || '').trim()
    setInvoiceForm({
      authors: String(meta.authors || authorNameFallback || ''),
      affiliation: String(meta.affiliation || authorAffiliationFallback || ''),
      apcAmount: meta.apc_amount != null ? String(meta.apc_amount) : '',
      fundingInfo: String(meta.funding_info || ''),
    })
  }, [])

  const mergeDeferredDetailContext = useCallback((detail: ManuscriptDetail) => {
    setMs((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        is_deferred_context_loaded: detail.is_deferred_context_loaded ?? prev.is_deferred_context_loaded ?? true,
        files: detail.files ?? prev.files,
        signed_files: detail.signed_files ?? prev.signed_files,
        reviewer_invites: detail.reviewer_invites ?? prev.reviewer_invites,
        author_response_history: detail.author_response_history ?? prev.author_response_history,
        latest_author_response_letter: detail.latest_author_response_letter ?? prev.latest_author_response_letter,
        latest_author_response_submitted_at:
          detail.latest_author_response_submitted_at ?? prev.latest_author_response_submitted_at,
        latest_author_response_round: detail.latest_author_response_round ?? prev.latest_author_response_round,
      }
    })
  }, [])

  const loadRbacContext = useCallback(async () => {
    const rbacRes = await EditorApi.getRbacContext()
    if (rbacRes?.success && rbacRes?.data) {
      setRbacContext(rbacRes.data)
    } else {
      setRbacContext(null)
    }
  }, [])

  const loadReviewReports = useCallback(async () => {
    if (!id) return
    try {
      setReviewsLoading(true)
      setReviewsError(null)
      const reviewRes = await withTimeout(
        EditorApi.getManuscriptReviews(id),
        DEFERRED_BLOCK_TIMEOUT_MS,
        'Reviewer feedback loading timed out.'
      )
      if (!reviewRes?.success) {
        throw new Error(reviewRes?.detail || reviewRes?.message || 'Failed to load reviewer feedback')
      }
      const rows = Array.isArray(reviewRes?.data) ? (reviewRes.data as ReviewerFeedbackItem[]) : []
      setReviewReports(rows)
    } catch (e) {
      setReviewReports([])
      setReviewsError(e instanceof Error ? e.message : 'Failed to load reviewer feedback')
    } finally {
      setReviewsLoading(false)
    }
  }, [id])

  const loadCardsContext = useCallback(
    async (force = false) => {
      if (!id) return
      try {
        setCardsLoading(true)
        setCardsError(null)
        const cardsRes = await withTimeout(
          EditorApi.getManuscriptCardsContext(id, { force }),
          DEFERRED_BLOCK_TIMEOUT_MS,
          'Task/queue cards loading timed out.'
        )
        if (!cardsRes?.success || !cardsRes?.data) {
          throw new Error(cardsRes?.detail || cardsRes?.message || 'Failed to load cards context')
        }
        setMs((prev) => {
          if (!prev) return prev
          return {
            ...prev,
            task_summary: cardsRes.data.task_summary ?? prev.task_summary,
            role_queue: cardsRes.data.role_queue ?? prev.role_queue,
          }
        })
      } catch (e) {
        const message = e instanceof Error ? e.message : 'Failed to load cards context'
        setCardsError(message)
      } finally {
        setCardsLoading(false)
      }
    },
    [id]
  )

  const loadDeferredDetailContext = useCallback(
    async (force = false) => {
      if (!id) return
      try {
        const detailRes = await withTimeout(
          EditorApi.getManuscriptDetail(id, { skipCards: true, includeHeavy: true, force }),
          DEFERRED_BLOCK_TIMEOUT_MS,
          'Deferred detail context loading timed out.'
        )
        if (!detailRes?.success || !detailRes?.data) {
          throw new Error(detailRes?.detail || detailRes?.message || 'Failed to load deferred detail context')
        }
        mergeDeferredDetailContext(detailRes.data as ManuscriptDetail)
      } catch (e) {
        console.warn('[EditorDetail] deferred detail context failed', e)
      }
    },
    [id, mergeDeferredDetailContext]
  )

  const refreshCardsIfVisible = useCallback(() => {
    if (!cardsActivated || !id) return
    void loadCardsContext(true)
  }, [cardsActivated, id, loadCardsContext])

  const refreshDetail = useCallback(async (options?: { force?: boolean }) => {
    if (!id) return
    const force = Boolean(options?.force)
    try {
      const detailRes = await EditorApi.getManuscriptDetail(id, { skipCards: true, force })
      if (!detailRes?.success) {
        throw new Error(detailRes?.detail || detailRes?.message || 'Manuscript not found')
      }
      const detail = detailRes.data as ManuscriptDetail
      applyDetail(detail)
      if (!detail?.is_deferred_context_loaded) {
        void loadDeferredDetailContext(force)
      }
      if (cardsActivated) {
        void loadCardsContext(force)
      }
      const normalizedStatus = normalizeWorkflowStatus(String(detail?.status || ''))
      if (normalizedStatus === 'pre_check') {
        setReviewReports([])
        setReviewsError(null)
        setReviewsLoading(false)
        setReviewsLoadedOnce(false)
      } else if (!reviewsActivated) {
        setReviewsLoadedOnce(false)
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to load manuscript')
      setMs(null)
    }
  }, [applyDetail, cardsActivated, id, loadCardsContext, loadDeferredDetailContext, reviewsActivated])

  async function load() {
    try {
      setLoading(true)
      // 与详情并发启动 RBAC 请求，减少首屏等待链路。
      void loadRbacContext().catch(() => setRbacContext(null))
      await refreshDetail()
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

  useEffect(() => {
    setReviewsActivated(false)
    setReviewsLoadedOnce(false)
    setCardsActivated(false)
  }, [id])

  useEffect(() => {
    if (reviewsActivated) return
    const node = reviewCardRef.current
    if (!node) return
    if (typeof IntersectionObserver === 'undefined') {
      setReviewsActivated(true)
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setReviewsActivated(true)
          observer.disconnect()
        }
      },
      { rootMargin: '200px 0px' }
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [ms, reviewsActivated])

  useEffect(() => {
    if (!reviewsActivated || reviewsLoadedOnce || !id) return
    const normalizedStatus = normalizeWorkflowStatus(String(ms?.status || ''))
    if (!normalizedStatus || normalizedStatus === 'pre_check') {
      setReviewReports([])
      setReviewsError(null)
      setReviewsLoading(false)
      setReviewsLoadedOnce(true)
      return
    }
    void loadReviewReports().finally(() => setReviewsLoadedOnce(true))
  }, [id, loadReviewReports, ms?.status, reviewsActivated, reviewsLoadedOnce])

  useEffect(() => {
    if (cardsActivated) return
    const node = cardsSectionRef.current
    if (!node) return
    if (typeof IntersectionObserver === 'undefined') {
      setCardsActivated(true)
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setCardsActivated(true)
          observer.disconnect()
        }
      },
      { rootMargin: '200px 0px' }
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [cardsActivated, ms])

  useEffect(() => {
    if (!cardsActivated || !id) return
    void loadCardsContext()
  }, [cardsActivated, id, loadCardsContext])

  useEffect(() => {
    let mounted = true
    authService
      .getSession()
      .then((session) => {
        if (!mounted) return
        setViewerEmail(String(session?.user?.email || '').trim())
      })
      .catch(() => {})
    return () => {
      mounted = false
    }
  }, [])

  // --- Derived State ---
  const status = String(ms?.status || '')
  const statusLower = normalizeWorkflowStatus(status)
  const isPrecheckActive = statusLower === 'pre_check'
  const isPostAcceptance = ['approved', 'layout', 'english_editing', 'proofreading', 'published'].includes(statusLower)
  const nextStatuses = useMemo(() => allowedNext(status), [status])
  const canAssignReviewersStage = ['under_review', 'resubmitted'].includes(statusLower)
  const canOpenDecisionWorkspaceStage = ['under_review', 'resubmitted', 'decision', 'decision_done'].includes(statusLower)
  const showDirectStatusTransitions = !isPostAcceptance && !['published', 'rejected'].includes(statusLower)
  const displayAuthors =
    String(invoiceForm.authors || '').trim() ||
    String(ms?.author?.full_name || '').trim() ||
    String(ms?.author?.email || '').trim() ||
    String(ms?.owner?.full_name || '').trim() ||
    String(ms?.owner?.email || '').trim() ||
    '—'
  const nextAction = useMemo(() => getNextActionCard((ms || {}) as ManuscriptDetail, capability), [ms, capability])
  const authorResponseHistory = useMemo(() => buildAuthorResponseHistory(ms), [ms])
  const latestAuthorResponse = authorResponseHistory[0] || null
  const roleQueueAssigneeText =
    ms?.role_queue?.current_assignee?.full_name ||
    ms?.role_queue?.current_assignee?.email ||
    ms?.role_queue?.current_assignee?.id ||
    ms?.role_queue?.current_assignee_label ||
    '—'

  // --- File Processing ---
  const fileHubProps = useMemo(() => buildFileHubProps(ms?.files), [ms?.files])

  const handleBack = useCallback(() => {
    if (typeof window !== 'undefined' && window.history.length > 1) {
      router.back()
      return
    }
    router.push(fallbackPath)
  }, [router, fallbackPath])

  const getTransitionActionLabel = useCallback(
    (nextStatus: string) => {
      const next = String(nextStatus || '').toLowerCase()
      if (statusLower === 'pre_check' && next === 'minor_revision') {
        return 'Request Technical Return'
      }
      if (statusLower === 'pre_check' && next === 'under_review') {
        return 'Move to Under Review'
      }
      return `Move to ${getStatusLabel(nextStatus)}`
    },
    [statusLower]
  )

  const openTransitionDialog = useCallback(
    (nextStatus: string) => {
      if (!canManualStatusTransition) {
        toast.error('Only Managing Editor/Admin can change status directly.')
        return
      }
      const target = String(nextStatus || '').toLowerCase().trim()
      if (statusLower === 'pre_check' && target === 'under_review' && !currentAeId) {
        toast.error('Please assign an Assistant Editor before moving to Under Review.')
        return
      }
      setPendingTransition(nextStatus)
      setTransitionReason('')
      setTransitionDialogOpen(true)
    },
    [canManualStatusTransition, currentAeId, statusLower]
  )

  const submitStatusTransition = useCallback(async () => {
    const target = String(pendingTransition || '').toLowerCase().trim()
    if (!target) return
    try {
      if (requiresTransitionReason && !transitionReason.trim()) {
        toast.error('This transition requires a reason.')
        return
      }
      setTransitioning(target)
      const res = await EditorApi.patchManuscriptStatus(id, target, transitionReason.trim() || undefined)
      if (!res?.success) throw new Error(res?.detail || res?.message || 'Failed')
      toast.success(`Moved to ${getStatusLabel(target)}`)
      setTransitionDialogOpen(false)
      setPendingTransition(null)
      setTransitionReason('')
      await refreshDetail({ force: true })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Transition failed')
    } finally {
      setTransitioning(null)
    }
  }, [id, pendingTransition, refreshDetail, requiresTransitionReason, transitionReason])

  const handleOpenInvoice = useCallback(() => {
    if (!capability.canUpdateInvoiceInfo) {
      toast.error('You do not have permission to edit invoice info.')
      return
    }
    setInvoiceOpen(true)
  }, [capability.canUpdateInvoiceInfo])

  const handleOpenDecisionWorkspace = useCallback(() => {
    router.push(`/editor/decision/${encodeURIComponent(id)}`)
  }, [id, router])

  const handleOpenProductionWorkspace = useCallback(() => {
    router.push(`/editor/production/${encodeURIComponent(id)}`)
  }, [id, router])

  const handleProductionStatusChange = useCallback((next: string) => {
    setMs((prev) => (prev ? { ...prev, status: next } : prev))
  }, [])

  const handleRetryReviews = useCallback(() => {
    setReviewsError(null)
    setReviewsLoadedOnce(false)
  }, [])

  const handleRetryCardsContext = useCallback(() => {
    void loadCardsContext(true)
  }, [loadCardsContext])


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
        <div className="mx-auto max-w-7xl px-4 py-16 space-y-4">
          <div className="text-slate-600">Manuscript not found.</div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" className="gap-1.5" onClick={handleBack}>
              <ArrowLeft className="h-4 w-4" />
              返回上一页
            </Button>
            <Button variant="secondary" size="sm" onClick={() => router.push(fallbackPath)}>
              回到列表
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      <SiteHeader />
      <DetailTopHeader
        journalTitle={ms.journals?.title}
        manuscriptTitle={ms.title}
        status={status}
        updatedAt={ms.updated_at}
        onBack={handleBack}
        onBackToList={() => router.push(fallbackPath)}
      />

      <main className="mx-auto max-w-[1600px] px-4 py-8 grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 space-y-6">
          <MetadataStaffCard
            manuscriptId={id}
            displayAuthors={displayAuthors}
            affiliation={invoiceForm.affiliation}
            submittedAt={ms.created_at}
            owner={ms.owner}
            canBindOwner={capability.canBindOwner}
            onOwnerBound={() => void refreshDetail({ force: true })}
            currentAeId={currentAeId}
            currentAeName={currentAeName}
            canAssignAE={canAssignAE}
            onAeAssigned={() => void refreshDetail({ force: true })}
            canUpdateInvoiceInfo={capability.canUpdateInvoiceInfo}
            invoiceStatus={ms.invoice?.status}
            invoiceAmount={ms.invoice?.amount}
            apcAmount={invoiceForm.apcAmount}
            onOpenInvoice={handleOpenInvoice}
          />

          <FileHubCard
            manuscriptId={id}
            manuscriptFiles={fileHubProps.manuscriptFiles}
            coverFiles={fileHubProps.coverFiles}
            reviewFiles={fileHubProps.reviewFiles}
            onUploadReviewFile={() => void refreshDetail({ force: true })}
            onUploadCoverLetter={() => void refreshDetail({ force: true })}
          />

          <AuthorResubmissionHistoryCard authorResponseHistory={authorResponseHistory} />

          <div className="h-[620px]">
            <InternalNotebook
              manuscriptId={id}
              currentUserId={rbacContext?.user_id}
              currentUserEmail={viewerEmail}
              onCommentPosted={refreshCardsIfVisible}
            />
          </div>

          <InternalTasksPanel manuscriptId={id} onChanged={refreshCardsIfVisible} />
        </div>

        <div className="lg:col-span-4 space-y-6">
          <NextActionCard nextAction={nextAction} />

          <LatestAuthorResubmissionCard
            latestAuthorResponse={latestAuthorResponse}
            historyCount={authorResponseHistory.length}
          />

          <ReviewerFeedbackSummaryCard
            reviewCardRef={reviewCardRef}
            reviewsActivated={reviewsActivated}
            reviewsLoading={reviewsLoading}
            reviewsError={reviewsError}
            reviewReports={reviewReports}
            onRetry={handleRetryReviews}
          />

          <EditorialActionsCard
            manuscriptId={id}
            isPostAcceptance={isPostAcceptance}
            canAssignReviewersStage={canAssignReviewersStage}
            canOpenDecisionWorkspaceStage={canOpenDecisionWorkspaceStage}
            canManageReviewers={capability.canManageReviewers}
            viewerRoles={normalizedRoles}
            canRecordFirstDecision={capability.canRecordFirstDecision}
            canSubmitFinalDecision={capability.canSubmitFinalDecision}
            canOpenProductionWorkspace={canOpenProductionWorkspace}
            statusLower={statusLower}
            finalPdfPath={ms.final_pdf_path}
            invoice={ms.invoice}
            showDirectStatusTransitions={showDirectStatusTransitions}
            canManualStatusTransition={canManualStatusTransition}
            nextStatuses={nextStatuses}
            transitioning={transitioning}
            currentAeId={currentAeId}
            onReviewerChanged={() => void refreshDetail({ force: true })}
            onOpenDecisionWorkspace={handleOpenDecisionWorkspace}
            onOpenProductionWorkspace={handleOpenProductionWorkspace}
            onProductionStatusChange={handleProductionStatusChange}
            onReload={() => void refreshDetail({ force: true })}
            onOpenTransitionDialog={openTransitionDialog}
            getTransitionActionLabel={getTransitionActionLabel}
          />

          <TaskSlaSummaryCard
            cardsSectionRef={cardsSectionRef}
            cardsActivated={cardsActivated}
            cardsLoading={cardsLoading}
            cardsError={cardsError}
            taskSummary={ms.task_summary}
            onRetry={handleRetryCardsContext}
          />

          <PrecheckRoleQueueCard
            cardsActivated={cardsActivated}
            cardsLoading={cardsLoading}
            cardsError={cardsError}
            isPrecheckActive={isPrecheckActive}
            roleQueue={ms.role_queue}
            roleQueueAssigneeText={roleQueueAssigneeText}
            statusLower={statusLower}
            onRetry={handleRetryCardsContext}
          />

          <AuditLogTimeline
            manuscriptId={id}
            authorResponses={authorResponseHistory}
            reviewerInvites={ms.reviewer_invites || []}
          />
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
            await refreshDetail({ force: true })
          } catch (e) {
            toast.error(e instanceof Error ? e.message : 'Save failed')
          } finally {
            setInvoiceSaving(false)
          }
        }}
      />

      <Dialog open={transitionDialogOpen} onOpenChange={setTransitionDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Confirm Status Transition</DialogTitle>
            <DialogDescription>
              {pendingTransition
                ? `You are moving this manuscript from "${getStatusLabel(status)}" to "${getStatusLabel(pendingTransition)}".`
                : 'Please confirm status transition.'}
            </DialogDescription>
          </DialogHeader>

          {requiresTransitionReason ? (
            <div className="space-y-2">
              <div className="text-sm font-medium text-slate-700">Reason</div>
              <Textarea
                placeholder={`Enter reason for ${pendingTransition ? getStatusLabel(pendingTransition) : 'this transition'}...`}
                value={transitionReason}
                onChange={(event) => setTransitionReason(event.target.value)}
                rows={4}
              />
            </div>
          ) : null}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                if (transitioning) return
                setTransitionDialogOpen(false)
                setPendingTransition(null)
                setTransitionReason('')
              }}
              disabled={Boolean(transitioning)}
            >
              Cancel
            </Button>
            <Button onClick={submitStatusTransition} disabled={Boolean(transitioning)}>
              {transitioning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
