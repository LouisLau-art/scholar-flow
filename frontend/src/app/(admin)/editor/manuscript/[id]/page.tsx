'use client'

import { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import dynamic from 'next/dynamic'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import { EditorApi } from '@/services/editorApi'
import { authService } from '@/services/auth'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { SafeDialog, SafeDialogContent } from '@/components/ui/safe-dialog'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ReviewerEmailPreviewDialog } from '@/components/editor/ReviewerEmailPreviewDialog'
import { toast } from 'sonner'
import { Loader2, ArrowLeft } from 'lucide-react'
import { InvoiceInfoModal, type InvoiceInfoForm } from '@/components/editor/InvoiceInfoModal'
import { getStatusLabel } from '@/lib/statusStyles'
import { formatDateTimeLocal } from '@/lib/date-display'
import { normalizeApiErrorMessage } from '@/lib/normalizeApiError'
import type { EditorRbacContext } from '@/types/rbac'
import { deriveEditorCapability } from '@/lib/rbac'
import {
  allowedNext,
  buildAuthorResponseHistory,
  buildFileHubProps,
  formatReviewerAuditVia,
  formatReviewerEmailEventLabel,
  formatReviewerHistoryAssignmentState,
  formatReviewerHistoryDecisionSummary,
  getNextActionCard,
  normalizeWorkflowStatus,
  resolveReviewerInviteSummaryState,
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
  ReviewerManagementCard,
  ReviewerInviteSummaryCard,
  ReviewerFeedbackSummaryCard,
  TaskSlaSummaryCard,
} from './detail-sections'
import type { ReviewerEmailPreviewData, ReviewerFeedbackItem, ReviewerHistoryItem, ReviewEmailTemplateOption } from './types'

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

const REVIEWER_FEEDBACK_TIMEOUT_MS = 25_000
const CARDS_CONTEXT_TIMEOUT_MS = 35_000
const DEFERRED_DETAIL_TIMEOUT_MS = 35_000
const AUTO_RETRY_BASE_DELAY_MS = 1_200
const REVIEWER_AUTO_RETRY_MAX = 2
const CARDS_AUTO_RETRY_MAX = 3
const DEFERRED_AUTO_RETRY_MAX = 3
const DEFERRED_PREFETCH_DELAY_MS = 900

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number, timeoutMessage: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error(timeoutMessage)), timeoutMs)
    promise
      .then((value) => resolve(value))
      .catch((error) => reject(error))
      .finally(() => window.clearTimeout(timer))
  })
}

type ReviewStageExitTarget = 'first' | 'final' | 'major_revision' | 'minor_revision'
type ReviewStageExitRequestedOutcome = 'major_revision' | 'minor_revision' | 'reject' | 'add_reviewer'

function getReviewStageExitLabel(target: ReviewStageExitTarget): string {
  switch (target) {
    case 'major_revision':
      return 'Major Revision'
    case 'minor_revision':
      return 'Minor Revision'
    case 'final':
      return 'Final Decision'
    case 'first':
    default:
      return 'First Decision'
  }
}

function getReviewStageExitRequestedOutcomeLabel(outcome: ReviewStageExitRequestedOutcome): string {
  switch (outcome) {
    case 'major_revision':
      return 'Major Revision'
    case 'minor_revision':
      return 'Minor Revision'
    case 'reject':
      return 'Reject'
    case 'add_reviewer':
      return 'Add Reviewer'
    default:
      return outcome
  }
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
  const [reviewStageExitDialogOpen, setReviewStageExitDialogOpen] = useState(false)
  const [reviewStageExitTarget, setReviewStageExitTarget] = useState<ReviewStageExitTarget>('first')
  const [reviewStageExitRequestedOutcome, setReviewStageExitRequestedOutcome] =
    useState<ReviewStageExitRequestedOutcome>('major_revision')
  const [reviewStageExitNote, setReviewStageExitNote] = useState('')
  const [reviewStageExitSubmitting, setReviewStageExitSubmitting] = useState(false)
  const [acceptedPendingResolutionByAssignment, setAcceptedPendingResolutionByAssignment] = useState<
    Record<string, 'cancel' | 'wait'>
  >({})
  const [viewerEmail, setViewerEmail] = useState<string>('')
  const [reviewReports, setReviewReports] = useState<ReviewerFeedbackItem[]>([])
  const [reviewsLoading, setReviewsLoading] = useState(false)
  const [reviewsError, setReviewsError] = useState<string | null>(null)
  const [sendingReviewerEmailAssignmentId, setSendingReviewerEmailAssignmentId] = useState<string | null>(null)
  const [reviewerEmailTemplates, setReviewerEmailTemplates] = useState<ReviewEmailTemplateOption[]>([])
  const [selectedReviewerTemplateByAssignment, setSelectedReviewerTemplateByAssignment] = useState<
    Record<string, string>
  >({})
  const [reviewerEmailPreviewOpen, setReviewerEmailPreviewOpen] = useState(false)
  const [reviewerEmailPreviewLoading, setReviewerEmailPreviewLoading] = useState(false)
  const [reviewerEmailPreviewSending, setReviewerEmailPreviewSending] = useState(false)
  const [reviewerEmailPreviewData, setReviewerEmailPreviewData] = useState<ReviewerEmailPreviewData | null>(null)
  const [reviewerEmailPreviewRecipient, setReviewerEmailPreviewRecipient] = useState('')
  const [reviewerEmailPreviewAssignmentId, setReviewerEmailPreviewAssignmentId] = useState('')
  const [reviewerHistoryOpen, setReviewerHistoryOpen] = useState(false)
  const [reviewerHistoryLoading, setReviewerHistoryLoading] = useState(false)
  const [reviewerHistoryError, setReviewerHistoryError] = useState<string | null>(null)
  const [reviewerHistoryRows, setReviewerHistoryRows] = useState<ReviewerHistoryItem[]>([])
  const [reviewerHistoryReviewerId, setReviewerHistoryReviewerId] = useState<string>('')
  const [reviewerHistoryReviewerLabel, setReviewerHistoryReviewerLabel] = useState<string>('')
  const reviewsRetryAttemptRef = useRef(0)
  const reviewsRetryTimerRef = useRef<number | null>(null)
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
  const [deferredLoading, setDeferredLoading] = useState(false)
  const [deferredError, setDeferredError] = useState<string | null>(null)
  const cardsRetryAttemptRef = useRef(0)
  const deferredRetryAttemptRef = useRef(0)
  const cardsRetryTimerRef = useRef<number | null>(null)
  const deferredRetryTimerRef = useRef<number | null>(null)
  const capability = useMemo(() => deriveEditorCapability(rbacContext), [rbacContext])
  const canViewReviewerFeedback =
    capability.canManageReviewers || capability.canRecordFirstDecision || capability.canSubmitFinalDecision
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
  const currentAcademicEditor = useMemo(() => {
    const fromDetail = ms?.academic_editor
    if (fromDetail?.id || fromDetail?.full_name || fromDetail?.email) {
      return fromDetail
    }
    if (ms?.role_queue?.current_role === 'academic' && ms?.role_queue?.current_assignee) {
      return {
        id: ms.role_queue.current_assignee.id,
        full_name: ms.role_queue.current_assignee.full_name,
        email: ms.role_queue.current_assignee.email,
      }
    }
    return null
  }, [ms])
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

  const loadReviewerEmailTemplates = useCallback(async () => {
    try {
      const response = await EditorApi.getReviewEmailTemplates('reviewer_assignment', { ttlMs: 30_000 })
      if (!response?.success) {
        throw new Error(response?.detail || response?.message || 'Failed to load email templates')
      }
      const rows = Array.isArray(response?.data) ? (response.data as ReviewEmailTemplateOption[]) : []
      setReviewerEmailTemplates(rows)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load email templates'
      toast.error(message)
      setReviewerEmailTemplates([])
    }
  }, [])

  const loadReviewReports = useCallback(async (force = false) => {
    if (!id) return
    try {
      setReviewsLoading(true)
      setReviewsError(null)
      const reviewRes = await withTimeout(
        EditorApi.getManuscriptReviews(id, force ? { force: true } : undefined),
        REVIEWER_FEEDBACK_TIMEOUT_MS,
        'Reviewer feedback loading timed out.'
      )
      if (!reviewRes?.success) {
        throw new Error(reviewRes?.detail || reviewRes?.message || 'Failed to load reviewer feedback')
      }
      const rows = Array.isArray(reviewRes?.data) ? (reviewRes.data as ReviewerFeedbackItem[]) : []
      reviewsRetryAttemptRef.current = 0
      setReviewReports(rows)
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to load reviewer feedback'
      const isTimeout = String(message).toLowerCase().includes('timed out')
      if (isTimeout && reviewsRetryAttemptRef.current < REVIEWER_AUTO_RETRY_MAX) {
        const attempt = reviewsRetryAttemptRef.current
        reviewsRetryAttemptRef.current += 1
        if (reviewsRetryTimerRef.current) {
          window.clearTimeout(reviewsRetryTimerRef.current)
        }
        const delay = AUTO_RETRY_BASE_DELAY_MS * 2 ** attempt
        reviewsRetryTimerRef.current = window.setTimeout(() => {
          void loadReviewReports(true)
        }, delay)
        return
      }
      setReviewReports([])
      setReviewsError(message)
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
          CARDS_CONTEXT_TIMEOUT_MS,
          'Task/queue cards loading timed out.'
        )
        if (!cardsRes?.success || !cardsRes?.data) {
          throw new Error(cardsRes?.detail || cardsRes?.message || 'Failed to load cards context')
        }
        cardsRetryAttemptRef.current = 0
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
        const isTimeout = String(message).toLowerCase().includes('timed out')
        if (isTimeout && cardsRetryAttemptRef.current < CARDS_AUTO_RETRY_MAX) {
          const attempt = cardsRetryAttemptRef.current
          cardsRetryAttemptRef.current += 1
          if (cardsRetryTimerRef.current) {
            window.clearTimeout(cardsRetryTimerRef.current)
          }
          const delay = AUTO_RETRY_BASE_DELAY_MS * 2 ** attempt
          cardsRetryTimerRef.current = window.setTimeout(() => {
            void loadCardsContext(true)
          }, delay)
          return
        }
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
        setDeferredLoading(true)
        setDeferredError(null)
        const detailRes = await withTimeout(
          EditorApi.getManuscriptDetail(id, { skipCards: true, includeHeavy: true, force }),
          DEFERRED_DETAIL_TIMEOUT_MS,
          'Deferred detail context loading timed out.'
        )
        if (!detailRes?.success || !detailRes?.data) {
          throw new Error(detailRes?.detail || detailRes?.message || 'Failed to load deferred detail context')
        }
        deferredRetryAttemptRef.current = 0
        mergeDeferredDetailContext(detailRes.data as ManuscriptDetail)
      } catch (e) {
        const message = e instanceof Error ? e.message : 'Deferred detail context loading timed out.'
        const isTimeout = String(message).toLowerCase().includes('timed out')
        if (isTimeout && deferredRetryAttemptRef.current < DEFERRED_AUTO_RETRY_MAX) {
          const attempt = deferredRetryAttemptRef.current
          deferredRetryAttemptRef.current += 1
          if (deferredRetryTimerRef.current) {
            window.clearTimeout(deferredRetryTimerRef.current)
          }
          const delay = AUTO_RETRY_BASE_DELAY_MS * 2 ** attempt
          deferredRetryTimerRef.current = window.setTimeout(() => {
            void loadDeferredDetailContext(true)
          }, delay)
          return
        }
        setDeferredError(message)
        console.warn('[EditorDetail] deferred detail context failed', e)
      } finally {
        setDeferredLoading(false)
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
        reviewsRetryAttemptRef.current = 0
        if (reviewsRetryTimerRef.current) {
          window.clearTimeout(reviewsRetryTimerRef.current)
          reviewsRetryTimerRef.current = null
        }
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
    if (!capability.canManageReviewers) {
      setReviewerEmailTemplates([])
      return
    }
    void loadReviewerEmailTemplates()
  }, [capability.canManageReviewers, loadReviewerEmailTemplates])

  useEffect(() => {
    setReviewsActivated(false)
    setReviewsLoadedOnce(false)
    setCardsActivated(false)
    setDeferredError(null)
    setSelectedReviewerTemplateByAssignment({})
    reviewsRetryAttemptRef.current = 0
    if (reviewsRetryTimerRef.current) {
      window.clearTimeout(reviewsRetryTimerRef.current)
      reviewsRetryTimerRef.current = null
    }
    cardsRetryAttemptRef.current = 0
    deferredRetryAttemptRef.current = 0
    if (cardsRetryTimerRef.current) {
      window.clearTimeout(cardsRetryTimerRef.current)
      cardsRetryTimerRef.current = null
    }
    if (deferredRetryTimerRef.current) {
      window.clearTimeout(deferredRetryTimerRef.current)
      deferredRetryTimerRef.current = null
    }
  }, [id])

  useEffect(() => {
    if (!Array.isArray(ms?.reviewer_invites) || ms.reviewer_invites.length === 0) return
    if (!reviewerEmailTemplates.length) return
    const defaultTemplateKey = String(reviewerEmailTemplates[0]?.template_key || '').trim()
    if (!defaultTemplateKey) return
    setSelectedReviewerTemplateByAssignment((prev) => {
      const next = { ...prev }
      for (const invite of ms.reviewer_invites || []) {
        const assignmentId = String(invite?.id || '').trim()
        if (!assignmentId) continue
        if (!next[assignmentId]) next[assignmentId] = defaultTemplateKey
      }
      return next
    })
  }, [ms?.reviewer_invites, reviewerEmailTemplates])

  useEffect(() => {
    return () => {
      if (cardsRetryTimerRef.current) {
        window.clearTimeout(cardsRetryTimerRef.current)
      }
      if (reviewsRetryTimerRef.current) {
        window.clearTimeout(reviewsRetryTimerRef.current)
      }
      if (deferredRetryTimerRef.current) {
        window.clearTimeout(deferredRetryTimerRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (!canViewReviewerFeedback) return
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
  }, [canViewReviewerFeedback, ms, reviewsActivated])

  useEffect(() => {
    if (!id) return
    if (!canViewReviewerFeedback || reviewsActivated) return
    const normalizedStatus = normalizeWorkflowStatus(String(ms?.status || ''))
    if (!normalizedStatus || normalizedStatus === 'pre_check') return
    const timer = window.setTimeout(() => {
      setReviewsActivated(true)
    }, DEFERRED_PREFETCH_DELAY_MS)
    return () => window.clearTimeout(timer)
  }, [canViewReviewerFeedback, id, ms?.status, reviewsActivated])

  useEffect(() => {
    if (canViewReviewerFeedback) return
    reviewsRetryAttemptRef.current = 0
    if (reviewsRetryTimerRef.current) {
      window.clearTimeout(reviewsRetryTimerRef.current)
      reviewsRetryTimerRef.current = null
    }
    setReviewsActivated(false)
    setReviewsLoadedOnce(false)
    setReviewReports([])
    setReviewsError(null)
    setReviewsLoading(false)
  }, [canViewReviewerFeedback])

  useEffect(() => {
    if (!canViewReviewerFeedback) return
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
  }, [canViewReviewerFeedback, id, loadReviewReports, ms?.status, reviewsActivated, reviewsLoadedOnce])

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
    if (!id || cardsActivated) return
    const timer = window.setTimeout(() => {
      setCardsActivated(true)
    }, DEFERRED_PREFETCH_DELAY_MS)
    return () => window.clearTimeout(timer)
  }, [cardsActivated, id])

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
  const canExitReviewStage =
    ['under_review', 'resubmitted'].includes(statusLower) &&
    (capability.canManageReviewers || capability.canRecordFirstDecision || capability.canSubmitFinalDecision)
  const canOpenDecisionWorkspaceStage = ['decision', 'decision_done'].includes(statusLower)
  const manualNextStatuses = useMemo(
    () => nextStatuses.filter((item) => !(canExitReviewStage && String(item || '').toLowerCase() === 'decision')),
    [canExitReviewStage, nextStatuses]
  )
  const showDirectStatusTransitions = !isPostAcceptance && !['published', 'rejected'].includes(statusLower)
  const displayAuthors =
    (Array.isArray(ms?.authors) ? ms.authors.filter(Boolean).join(', ') : '') ||
    String(invoiceForm.authors || '').trim() ||
    String(ms?.author?.full_name || '').trim() ||
    String(ms?.author?.email || '').trim() ||
    String(ms?.owner?.full_name || '').trim() ||
    String(ms?.owner?.email || '').trim() ||
    '—'
  const correspondingAuthor = Array.isArray(ms?.author_contacts)
    ? ms.author_contacts.find((item) => item?.is_corresponding) || ms.author_contacts[0] || null
    : null
  const correspondingAuthorLabel =
    String(correspondingAuthor?.name || '').trim() ||
    String(correspondingAuthor?.email || '').trim() ||
    String(ms?.author?.full_name || '').trim() ||
    String(ms?.author?.email || '').trim() ||
    '—'
  const submissionEmail =
    String(ms?.submission_email || '').trim() ||
    String(correspondingAuthor?.email || '').trim() ||
    String(ms?.author?.email || '').trim() ||
    '—'
  const nextAction = useMemo(() => getNextActionCard((ms || {}) as ManuscriptDetail, capability), [ms, capability])
  const acceptedPendingInvites = useMemo(
    () =>
      (ms?.reviewer_invites || []).filter((invite) => resolveReviewerInviteSummaryState(invite) === 'accepted'),
    [ms?.reviewer_invites]
  )
  const autoCancelledReviewStageInvites = useMemo(
    () =>
      (ms?.reviewer_invites || []).filter((invite) => {
        const state = resolveReviewerInviteSummaryState(invite)
        return state === 'selected' || state === 'invited' || state === 'opened'
      }),
    [ms?.reviewer_invites]
  )
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

  const handleOpenReviewStageExitDialog = useCallback(() => {
    setReviewStageExitTarget('first')
    setReviewStageExitRequestedOutcome('major_revision')
    setReviewStageExitNote('')
    setAcceptedPendingResolutionByAssignment({})
    setReviewStageExitDialogOpen(true)
  }, [])

  const handleSubmitReviewStageExit = useCallback(async () => {
    if (acceptedPendingInvites.length > 0) {
      const unresolved = acceptedPendingInvites.filter(
        (invite) => !acceptedPendingResolutionByAssignment[String(invite.id || '').trim()]
      )
      if (unresolved.length > 0) {
        toast.error('Please explicitly handle every accepted reviewer before leaving under_review.')
        return
      }
      const waiting = acceptedPendingInvites.filter(
        (invite) => acceptedPendingResolutionByAssignment[String(invite.id || '').trim()] === 'wait'
      )
      if (waiting.length > 0) {
        toast.error('Some accepted reviewers are still marked as waiting. Close this dialog and stay in under_review.')
        return
      }
    }

    setReviewStageExitSubmitting(true)
    try {
      if (reviewStageExitTarget === 'first' && !reviewStageExitRequestedOutcome) {
        toast.error('Please select an AE recommendation before sending to First Decision.')
        return
      }
      const res = await EditorApi.exitReviewStage(id, {
        target_stage: reviewStageExitTarget,
        requested_outcome: reviewStageExitTarget === 'first' ? reviewStageExitRequestedOutcome : undefined,
        note: reviewStageExitNote.trim() || undefined,
        accepted_pending_resolutions: acceptedPendingInvites.map((invite) => ({
          assignment_id: String(invite.id || ''),
          action: acceptedPendingResolutionByAssignment[String(invite.id || '').trim()] || 'wait',
          reason:
            acceptedPendingResolutionByAssignment[String(invite.id || '').trim()] === 'cancel'
              ? reviewStageExitNote.trim() || undefined
              : undefined,
        })),
      })
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || 'Failed to exit review stage')
      }
      const targetLabel = getReviewStageExitLabel(reviewStageExitTarget)
      const requestedOutcomeLabel =
        reviewStageExitTarget === 'first'
          ? getReviewStageExitRequestedOutcomeLabel(reviewStageExitRequestedOutcome)
          : null
      toast.success(
        `Moved manuscript to ${targetLabel}${requestedOutcomeLabel ? ` (${requestedOutcomeLabel})` : ''}. Auto-cancelled ${
          res?.data?.auto_cancelled_assignment_ids?.length || 0
        } reviewer(s).`
      )
      const failedCancellationEmails = Array.isArray(res?.data?.cancellation_email_failed_assignment_ids)
        ? res.data.cancellation_email_failed_assignment_ids.length
        : 0
      if (failedCancellationEmails > 0) {
        toast.warning(`${failedCancellationEmails} cancellation email(s) failed. Reviewer access is still revoked.`)
      }
      setReviewStageExitDialogOpen(false)
      setReviewStageExitRequestedOutcome('major_revision')
      setReviewStageExitNote('')
      setAcceptedPendingResolutionByAssignment({})
      await refreshDetail({ force: true })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to exit review stage')
    } finally {
      setReviewStageExitSubmitting(false)
    }
  }, [
    acceptedPendingInvites,
    acceptedPendingResolutionByAssignment,
    id,
    refreshDetail,
    reviewStageExitNote,
    reviewStageExitRequestedOutcome,
    reviewStageExitTarget,
  ])

  const handleOpenProductionWorkspace = useCallback(() => {
    router.push(`/editor/production/${encodeURIComponent(id)}`)
  }, [id, router])

  const handleProductionStatusChange = useCallback((next: string) => {
    setMs((prev) => (prev ? { ...prev, status: next } : prev))
  }, [])

  const handleRetryReviews = useCallback(() => {
    reviewsRetryAttemptRef.current = 0
    if (reviewsRetryTimerRef.current) {
      window.clearTimeout(reviewsRetryTimerRef.current)
      reviewsRetryTimerRef.current = null
    }
    setReviewsError(null)
    void loadReviewReports(true).finally(() => setReviewsLoadedOnce(true))
  }, [loadReviewReports])

  const handleSendReviewerTemplateEmail = useCallback(
    async (args: { assignmentId: string; reviewerId: string; templateKey: string }) => {
      const assignmentId = String(args.assignmentId || '').trim()
      const templateKey = String(args.templateKey || '').trim()
      if (!assignmentId) return
      if (!templateKey) {
        toast.error('Please select an email template.')
        return
      }
      setReviewerEmailPreviewAssignmentId(assignmentId)
      setReviewerEmailPreviewOpen(true)
      setReviewerEmailPreviewLoading(true)
      setSendingReviewerEmailAssignmentId(assignmentId)
      try {
        const res = await EditorApi.previewReviewerAssignmentEmail(assignmentId, { template_key: templateKey })
        if (!res?.success) {
          throw new Error(normalizeApiErrorMessage(res, 'Failed to preview reviewer email'))
        }
        setReviewerEmailPreviewData((res.data as ReviewerEmailPreviewData) || null)
        setReviewerEmailPreviewRecipient(String(res?.data?.recipient_email || '').trim())
      } catch (e) {
        setReviewerEmailPreviewOpen(false)
        setReviewerEmailPreviewData(null)
        setReviewerEmailPreviewRecipient('')
        setReviewerEmailPreviewAssignmentId('')
        toast.error(e instanceof Error ? e.message : 'Failed to preview reviewer email')
      } finally {
        setReviewerEmailPreviewLoading(false)
        setSendingReviewerEmailAssignmentId(null)
      }
    },
    []
  )

  const handleCloseReviewerEmailPreview = useCallback(() => {
    if (reviewerEmailPreviewSending) return
    setReviewerEmailPreviewOpen(false)
    setReviewerEmailPreviewLoading(false)
    setReviewerEmailPreviewData(null)
    setReviewerEmailPreviewRecipient('')
    setReviewerEmailPreviewAssignmentId('')
  }, [reviewerEmailPreviewSending])

  const handleConfirmReviewerTemplateEmail = useCallback(async () => {
    const assignmentId = String(reviewerEmailPreviewAssignmentId || '').trim()
    const templateKey = String(reviewerEmailPreviewData?.template_key || '').trim()
    const recipientEmail = String(reviewerEmailPreviewRecipient || '').trim()
    if (!assignmentId || !templateKey || !recipientEmail) {
      toast.error('Reviewer email preview is incomplete.')
      return
    }
    setReviewerEmailPreviewSending(true)
    setSendingReviewerEmailAssignmentId(assignmentId)
    try {
      const res = await EditorApi.sendReviewerAssignmentEmail(assignmentId, {
        template_key: templateKey,
        recipient_email: recipientEmail,
      })
      if (!res?.success) {
        throw new Error(normalizeApiErrorMessage(res, 'Failed to send reviewer email'))
      }
      const deliveryStatus = String(res?.data?.delivery_status || '').trim().toLowerCase()
      const templateLabel = res?.data?.template_display_name || templateKey
      const previewSend = Boolean(res?.data?.preview_send)
      if (deliveryStatus === 'sent') {
        if (previewSend) {
          toast.success(`Preview email "${templateLabel}" sent to ${recipientEmail}. Assignment status unchanged.`)
        } else {
          toast.success(`Template "${templateLabel}" sent.`)
        }
      } else if (deliveryStatus === 'failed') {
        toast.error(res?.data?.delivery_error || `Template "${templateLabel}" failed to send.`)
      } else {
        toast.message(`Template "${templateLabel}" accepted. Delivery pending.`)
      }
      handleCloseReviewerEmailPreview()
      await refreshDetail({ force: true })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to send reviewer email')
    } finally {
      setReviewerEmailPreviewSending(false)
      setSendingReviewerEmailAssignmentId(null)
    }
  }, [
    handleCloseReviewerEmailPreview,
    refreshDetail,
    reviewerEmailPreviewAssignmentId,
    reviewerEmailPreviewData?.template_key,
    reviewerEmailPreviewRecipient,
  ])

  const handleReviewerTemplateChange = useCallback((args: { assignmentId: string; templateKey: string }) => {
    const assignmentId = String(args.assignmentId || '').trim()
    const templateKey = String(args.templateKey || '').trim()
    if (!assignmentId || !templateKey) return
    setSelectedReviewerTemplateByAssignment((prev) => ({ ...prev, [assignmentId]: templateKey }))
  }, [])

  const loadReviewerHistory = useCallback(
    async (reviewerId: string, reviewerLabel: string, force = false) => {
      const safeReviewerId = String(reviewerId || '').trim()
      if (!safeReviewerId) return
      setReviewerHistoryOpen(true)
      setReviewerHistoryReviewerId(safeReviewerId)
      setReviewerHistoryReviewerLabel(String(reviewerLabel || '').trim() || 'Reviewer')
      setReviewerHistoryLoading(true)
      setReviewerHistoryError(null)
      try {
        const historyRes = await EditorApi.getReviewerHistory(safeReviewerId, {
          limit: 50,
          force,
        })
        if (!historyRes?.success) {
          throw new Error(historyRes?.detail || historyRes?.message || 'Failed to load reviewer history')
        }
        const rows = Array.isArray(historyRes?.data) ? (historyRes.data as ReviewerHistoryItem[]) : []
        setReviewerHistoryRows(rows)
      } catch (e) {
        setReviewerHistoryRows([])
        setReviewerHistoryError(e instanceof Error ? e.message : 'Failed to load reviewer history')
      } finally {
        setReviewerHistoryLoading(false)
      }
    },
    []
  )

  const handleOpenReviewerHistory = useCallback(
    (args: { reviewerId: string; reviewerLabel: string }) => {
      void loadReviewerHistory(args.reviewerId, args.reviewerLabel, true)
    },
    [loadReviewerHistory]
  )

  const handleRetryCardsContext = useCallback(() => {
    cardsRetryAttemptRef.current = 0
    setCardsError(null)
    void loadCardsContext(true)
  }, [loadCardsContext])

  const handleRetryDeferredContext = useCallback(() => {
    deferredRetryAttemptRef.current = 0
    setDeferredError(null)
    void loadDeferredDetailContext(true)
  }, [loadDeferredDetailContext])


  if (loading) {
    return (
      <div className="min-h-screen bg-muted/40">
        <SiteHeader />
        <div className="mx-auto max-w-7xl px-4 py-16 flex items-center justify-center text-muted-foreground gap-2">
          <Loader2 className="h-5 w-5 animate-spin" /> Loading…
        </div>
      </div>
    )
  }

  if (!ms) {
    return (
      <div className="min-h-screen bg-muted/40">
        <SiteHeader />
        <div className="mx-auto max-w-7xl px-4 py-16 space-y-4">
          <div className="text-muted-foreground">Manuscript not found.</div>
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
    <div className="min-h-screen bg-muted/40 pb-20">
      <SiteHeader />
      <DetailTopHeader
        journalTitle={ms.journals?.title}
        manuscriptTitle={ms.title}
        status={status}
        updatedAt={ms.updated_at}
        onBack={handleBack}
        onBackToList={() => router.push(fallbackPath)}
      />

      <main className="mx-auto sf-max-w-1600 px-4 py-8 grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 space-y-6">
          <MetadataStaffCard
            manuscriptId={id}
            displayAuthors={displayAuthors}
            affiliation={invoiceForm.affiliation}
            correspondingAuthorLabel={correspondingAuthorLabel}
            submissionEmail={submissionEmail}
            specialIssue={ms.special_issue}
            submittedAt={ms.created_at}
            owner={ms.owner}
            canBindOwner={capability.canBindOwner}
            onOwnerBound={() => void refreshDetail({ force: true })}
            currentAcademicEditor={currentAcademicEditor}
            canBindAcademicEditor={capability.canBindAcademicEditor}
            onAcademicEditorBound={() => void refreshDetail({ force: true })}
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

          <ReviewerManagementCard
            reviewerInvites={ms.reviewer_invites || []}
            deferredLoaded={Boolean(ms.is_deferred_context_loaded)}
            deferredLoading={deferredLoading}
            loadError={deferredError}
            onRetry={handleRetryDeferredContext}
            canManageReviewerOutreach={capability.canManageReviewers}
            sendingAssignmentId={sendingReviewerEmailAssignmentId}
            emailTemplateOptions={reviewerEmailTemplates}
            selectedTemplateByAssignment={selectedReviewerTemplateByAssignment}
            onTemplateChange={handleReviewerTemplateChange}
            onSendTemplateEmail={handleSendReviewerTemplateEmail}
            onOpenHistory={handleOpenReviewerHistory}
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

          <ReviewerInviteSummaryCard
            reviewerInvites={ms.reviewer_invites || []}
            deferredLoaded={Boolean(ms.is_deferred_context_loaded)}
            deferredLoading={deferredLoading}
            loadError={deferredError}
            onRetry={handleRetryDeferredContext}
          />

          <ReviewerFeedbackSummaryCard
            canViewReviewerFeedback={canViewReviewerFeedback}
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
            canExitReviewStage={canExitReviewStage}
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
            nextStatuses={manualNextStatuses}
            transitioning={transitioning}
            currentAeId={currentAeId}
            onReviewerChanged={() => void refreshDetail({ force: true })}
            onOpenReviewStageExitDialog={handleOpenReviewStageExitDialog}
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

      <ReviewerEmailPreviewDialog
        open={reviewerEmailPreviewOpen}
        loading={reviewerEmailPreviewLoading}
        sending={reviewerEmailPreviewSending}
        preview={reviewerEmailPreviewData}
        recipientEmail={reviewerEmailPreviewRecipient}
        onRecipientEmailChange={setReviewerEmailPreviewRecipient}
        onClose={handleCloseReviewerEmailPreview}
        onSend={handleConfirmReviewerTemplateEmail}
      />

      <SafeDialog
        open={reviewStageExitDialogOpen}
        onClose={() => {
          if (reviewStageExitSubmitting) return
          setReviewStageExitDialogOpen(false)
        }}
        closeDisabled={reviewStageExitSubmitting}
      >
        <SafeDialogContent className="sm:max-w-2xl" closeDisabled={reviewStageExitSubmitting}>
          <DialogHeader>
            <DialogTitle>Exit Review Stage</DialogTitle>
            <DialogDescription>
              离开 `under_review / resubmitted` 前，系统会自动终止未接受邀请的 reviewer；已接受但未提交的 reviewer 需要你显式处理。
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-5">
            <div className="space-y-2">
              <div className="text-sm font-medium text-foreground">Next action</div>
              <RadioGroup
                value={reviewStageExitTarget}
                onValueChange={(value) => {
                  const nextTarget = value as ReviewStageExitTarget
                  setReviewStageExitTarget(nextTarget)
                  if (nextTarget !== 'first') {
                    setReviewStageExitRequestedOutcome('major_revision')
                  }
                }}
                className="grid gap-2"
              >
                <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border px-3 py-3">
                  <RadioGroupItem id="review-stage-target-major" value="major_revision" className="mt-1" />
                  <div className="space-y-1">
                    <Label htmlFor="review-stage-target-major" className="cursor-pointer font-medium">
                      Direct Major Revision
                    </Label>
                    <div className="text-xs text-muted-foreground">
                      AE 直接把稿件推进到 `major_revision`，作者可立即开始修改。
                    </div>
                  </div>
                </label>
                <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border px-3 py-3">
                  <RadioGroupItem id="review-stage-target-minor" value="minor_revision" className="mt-1" />
                  <div className="space-y-1">
                    <Label htmlFor="review-stage-target-minor" className="cursor-pointer font-medium">
                      Direct Minor Revision
                    </Label>
                    <div className="text-xs text-muted-foreground">
                      AE 直接把稿件推进到 `minor_revision`，不必先进入 decision queue。
                    </div>
                  </div>
                </label>
                <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border px-3 py-3">
                  <RadioGroupItem id="review-stage-target-first" value="first" className="mt-1" />
                  <div className="space-y-1">
                    <Label htmlFor="review-stage-target-first" className="cursor-pointer font-medium">
                      Send to First Decision
                    </Label>
                    <div className="text-xs text-muted-foreground">
                      进入 `decision` 队列，由学术编辑/主编处理 major revision / minor revision / reject / add reviewer。
                    </div>
                  </div>
                </label>
                <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border px-3 py-3">
                  <RadioGroupItem id="review-stage-target-final" value="final" className="mt-1" />
                  <div className="space-y-1">
                    <Label htmlFor="review-stage-target-final" className="cursor-pointer font-medium">
                      Send to Final Decision
                    </Label>
                    <div className="text-xs text-muted-foreground">
                      直接进入 `decision_done` 队列，可供终轮决策使用。
                    </div>
                  </div>
                </label>
              </RadioGroup>
            </div>

            {reviewStageExitTarget === 'first' ? (
              <div className="space-y-2 rounded-md border border-border bg-muted/20 p-3">
                <div className="text-sm font-medium text-foreground">AE recommendation for First Decision</div>
                <div className="text-xs text-muted-foreground">
                  AE 不直接做 reject；这里只是把推荐结论连同稿件一并提交给学术编辑/主编。
                </div>
                <RadioGroup
                  value={reviewStageExitRequestedOutcome}
                  onValueChange={(value) =>
                    setReviewStageExitRequestedOutcome(value as ReviewStageExitRequestedOutcome)
                  }
                  className="grid gap-2 pt-1"
                >
                  <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border px-3 py-3">
                    <RadioGroupItem id="review-stage-outcome-major" value="major_revision" className="mt-1" />
                    <div className="space-y-1">
                      <Label htmlFor="review-stage-outcome-major" className="cursor-pointer font-medium">
                        Recommend Major Revision
                      </Label>
                      <div className="text-xs text-muted-foreground">建议学术编辑/主编考虑大修。</div>
                    </div>
                  </label>
                  <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border px-3 py-3">
                    <RadioGroupItem id="review-stage-outcome-minor" value="minor_revision" className="mt-1" />
                    <div className="space-y-1">
                      <Label htmlFor="review-stage-outcome-minor" className="cursor-pointer font-medium">
                        Recommend Minor Revision
                      </Label>
                      <div className="text-xs text-muted-foreground">建议学术编辑/主编考虑小修。</div>
                    </div>
                  </label>
                  <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border px-3 py-3">
                    <RadioGroupItem id="review-stage-outcome-reject" value="reject" className="mt-1" />
                    <div className="space-y-1">
                      <Label htmlFor="review-stage-outcome-reject" className="cursor-pointer font-medium">
                        Recommend Reject
                      </Label>
                      <div className="text-xs text-muted-foreground">建议学术编辑/主编考虑拒稿。</div>
                    </div>
                  </label>
                  <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border px-3 py-3">
                    <RadioGroupItem id="review-stage-outcome-add-reviewer" value="add_reviewer" className="mt-1" />
                    <div className="space-y-1">
                      <Label htmlFor="review-stage-outcome-add-reviewer" className="cursor-pointer font-medium">
                        Recommend Add Reviewer
                      </Label>
                      <div className="text-xs text-muted-foreground">建议学术编辑/主编补充新的 reviewer 再做判断。</div>
                    </div>
                  </label>
                </RadioGroup>
              </div>
            ) : null}

            <div className="space-y-2 rounded-md border border-border bg-muted/30 p-3">
              <div className="text-sm font-medium text-foreground">Automatic cleanup</div>
              <div className="text-sm text-muted-foreground">
                {autoCancelledReviewStageInvites.length === 0
                  ? '当前没有 selected / invited / opened reviewer 需要自动 cancel。'
                  : `系统会自动 cancel ${autoCancelledReviewStageInvites.length} 位 selected / invited / opened reviewer。`}
              </div>
            </div>

            {acceptedPendingInvites.length > 0 ? (
              <div className="space-y-3 rounded-md border border-border bg-muted/20 p-3">
                <div className="space-y-1">
                  <div className="text-sm font-medium text-foreground">Accepted but not submitted</div>
                  <div className="text-xs text-muted-foreground">
                    这些 reviewer 已接受邀请。若要离开当前外审阶段，必须明确将其取消；若仍要等待，请关闭此弹窗并继续停留在 under_review。
                  </div>
                </div>
                <div className="space-y-2">
                  {acceptedPendingInvites.map((invite) => {
                    const assignmentId = String(invite.id || '').trim()
                    const selectedAction = acceptedPendingResolutionByAssignment[assignmentId] || ''
                    return (
                      <div key={assignmentId} className="rounded-md border border-border bg-background px-3 py-3">
                        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                          <div>
                            <div className="text-sm font-medium text-foreground">
                              {invite.reviewer_name || invite.reviewer_email || 'Reviewer'}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {invite.reviewer_email || 'No email'} · Due {invite.due_at ? formatDateTimeLocal(invite.due_at) : '—'}
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <Button
                              type="button"
                              size="sm"
                              variant={selectedAction === 'cancel' ? 'default' : 'outline'}
                              onClick={() =>
                                setAcceptedPendingResolutionByAssignment((prev) => ({ ...prev, [assignmentId]: 'cancel' }))
                              }
                            >
                              Cancel reviewer
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant={selectedAction === 'wait' ? 'default' : 'outline'}
                              onClick={() =>
                                setAcceptedPendingResolutionByAssignment((prev) => ({ ...prev, [assignmentId]: 'wait' }))
                              }
                            >
                              Keep waiting
                            </Button>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : null}

            <div className="space-y-2">
              <div className="text-sm font-medium text-foreground">Audit note / cancel reason</div>
              <Textarea
                value={reviewStageExitNote}
                onChange={(event) => setReviewStageExitNote(event.target.value)}
                rows={4}
                placeholder="Explain why review stage is being closed and why any accepted reviewers are being cancelled..."
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                if (reviewStageExitSubmitting) return
                setReviewStageExitDialogOpen(false)
              }}
              disabled={reviewStageExitSubmitting}
            >
              Cancel
            </Button>
            <Button onClick={() => void handleSubmitReviewStageExit()} disabled={reviewStageExitSubmitting}>
              {reviewStageExitSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Continue
            </Button>
          </DialogFooter>
        </SafeDialogContent>
      </SafeDialog>

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
              <div className="text-sm font-medium text-foreground">Reason</div>
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

      <Dialog open={reviewerHistoryOpen} onOpenChange={setReviewerHistoryOpen}>
        <DialogContent className="max-w-5xl">
          <DialogHeader>
            <DialogTitle>Invitations History ({reviewerHistoryReviewerLabel || 'Reviewer'})</DialogTitle>
            <DialogDescription>
              Reviewer ID: {reviewerHistoryReviewerId || '—'}
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[60vh] overflow-auto rounded-md border border-border">
            {reviewerHistoryLoading ? (
              <div className="flex items-center gap-2 px-4 py-8 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading reviewer history...
              </div>
            ) : reviewerHistoryError ? (
              <div className="space-y-3 px-4 py-6">
                <div className="text-sm text-destructive">{reviewerHistoryError}</div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => void loadReviewerHistory(reviewerHistoryReviewerId, reviewerHistoryReviewerLabel, true)}
                >
                  Retry
                </Button>
              </div>
            ) : reviewerHistoryRows.length === 0 ? (
              <div className="px-4 py-8 text-sm text-muted-foreground">No invitation history yet.</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-card">
                  <tr className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="px-3 py-2 text-left font-semibold">Manuscript</th>
                    <th className="px-3 py-2 text-left font-semibold">Status</th>
                    <th className="px-3 py-2 text-left font-semibold">Round / Due</th>
                    <th className="px-3 py-2 text-left font-semibold">Added On</th>
                    <th className="px-3 py-2 text-left font-semibold">Added By</th>
                    <th className="px-3 py-2 text-left font-semibold">Added Via</th>
                    <th className="px-3 py-2 text-left font-semibold">Email Actions</th>
                    <th className="px-3 py-2 text-left font-semibold">Decision / Submitted</th>
                    <th className="px-3 py-2 text-left font-semibold">Manuscript Status</th>
                  </tr>
                </thead>
                <tbody>
                  {reviewerHistoryRows.map((row, idx) => {
                    const rowKey = String(row.assignment_id || `history-${idx}`)
                    const emailEvents = Array.isArray(row.email_events) ? row.email_events : []
                    const addedByLabel =
                      String(row.added_by?.full_name || '').trim() ||
                      String(row.added_by?.email || '').trim() ||
                      '—'
                    const invitedByLabel =
                      String(row.invited_by?.full_name || '').trim() || String(row.invited_by?.email || '').trim()
                    const addedViaLabel = formatReviewerAuditVia(row.added_via)
                    const invitedViaLabel = formatReviewerAuditVia(row.invited_via)
                    const emailActionLines =
                      emailEvents.length > 0
                        ? emailEvents.map((event) => {
                            const createdAt = event?.created_at ? formatDateTimeLocal(event.created_at) : '—'
                            const error = String(event?.error_message || '').trim()
                            return `${formatReviewerEmailEventLabel(event)} · ${createdAt}${error ? ` · ${error}` : ''}`
                          })
                        : [
                            invitedByLabel
                              ? `Invited by ${invitedByLabel}${invitedViaLabel ? ` via ${invitedViaLabel}` : ''}`
                              : invitedViaLabel
                                ? `Invited via ${invitedViaLabel}`
                                : '',
                            row.invited_at ? `Invitation recorded ${formatDateTimeLocal(row.invited_at)}` : '',
                            row.last_reminded_at ? `Reminder recorded ${formatDateTimeLocal(row.last_reminded_at)}` : '',
                          ].filter(Boolean)
                    const roundText =
                      typeof row.round_number === 'number'
                        ? `Round ${row.round_number}`
                        : row.round_number != null && Number.isFinite(Number(row.round_number))
                          ? `Round ${Number(row.round_number)}`
                          : '—'
                    const dueText = row.due_at ? formatDateTimeLocal(row.due_at) : '—'
                    const decisionText = formatReviewerHistoryDecisionSummary(row)
                    return (
                      <tr key={rowKey} className="border-b border-border/60 last:border-0 align-top">
                        <td className="px-3 py-2.5">
                          <div className="font-medium text-foreground">{row.manuscript_title || row.manuscript_id || '—'}</div>
                          {row.manuscript_id ? <div className="text-xs text-muted-foreground">{row.manuscript_id}</div> : null}
                        </td>
                        <td className="px-3 py-2.5">{formatReviewerHistoryAssignmentState(row)}</td>
                        <td className="px-3 py-2.5">
                          <div>{roundText}</div>
                          <div className="text-xs text-muted-foreground">Due {dueText}</div>
                        </td>
                        <td className="px-3 py-2.5">{row.added_on ? formatDateTimeLocal(row.added_on) : '—'}</td>
                        <td className="px-3 py-2.5">{addedByLabel}</td>
                        <td className="px-3 py-2.5">{addedViaLabel || '—'}</td>
                        <td className="px-3 py-2.5">
                          {emailActionLines.length > 0 ? (
                            <div className="space-y-1">
                              {emailActionLines.map((line, lineIdx) => (
                                <div key={`${rowKey}-email-line-${lineIdx}`}>{line}</div>
                              ))}
                            </div>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td className="px-3 py-2.5">
                          <div>{decisionText}</div>
                          <div className="text-xs text-muted-foreground">
                            {row.report_submitted_at ? formatDateTimeLocal(row.report_submitted_at) : '—'}
                          </div>
                        </td>
                        <td className="px-3 py-2.5">{row.manuscript_status || '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
