"use client"

import { useState, useEffect, useMemo } from "react"
import { useRouter } from "next/navigation"
import { Star, FileText, Send } from "lucide-react"
import { toast } from "sonner"
import { authService } from "@/services/auth"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { FileUpload } from "@/components/FileUpload"
import { SafeDialog, SafeDialogContent } from "@/components/ui/safe-dialog"
import { formatDateTimeLocal } from "@/lib/date-display"
import { sanitizeRichHtml } from "@/lib/sanitizeRichHtml"
import { normalizeApiErrorMessage } from "@/lib/normalizeApiError"

export const REVIEW_ATTACHMENT_ACCEPT =
  ".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"

interface ReviewTask {
  assignmentId: string
  manuscript_id: string
  assignment_status?: string | null
  manuscript_title?: string | null
  manuscript_abstract?: string | null
  manuscripts?: {
    title: string
    abstract: string
    file_path?: string | null
  } | null
}

interface ReviewHistoryEmailEvent {
  status?: string | null
  event_type?: string | null
  template_name?: string | null
  created_at?: string | null
  error_message?: string | null
}

interface ReviewHistoryItem {
  assignment_id: string
  manuscript_id: string
  manuscript_title?: string | null
  manuscript_abstract?: string | null
  manuscript_status?: string | null
  assignment_status?: string | null
  assignment_state: 'submitted' | 'declined' | 'cancelled' | string
  round_number?: number | null
  added_on?: string | null
  invited_at?: string | null
  opened_at?: string | null
  accepted_at?: string | null
  declined_at?: string | null
  decline_reason?: string | null
  decline_note?: string | null
  cancelled_at?: string | null
  cancel_reason?: string | null
  cancel_via?: string | null
  last_reminded_at?: string | null
  due_at?: string | null
  report_status?: string | null
  report_submitted_at?: string | null
  comments_for_author?: string | null
  confidential_comments_to_editor?: string | null
  report_attachment_filename?: string | null
  latest_email_status?: string | null
  latest_email_at?: string | null
  latest_email_error?: string | null
  email_events?: ReviewHistoryEmailEvent[]
}

type HistoryTimelineEvent = {
  id: string
  title: string
  timestamp: string
  detail?: string | null
}

function normalizeReviewTask(row: any): ReviewTask | null {
  const assignmentId = String(row?.assignment_id || row?.id || '').trim()
  const manuscriptId = String(row?.manuscript_id || '').trim()
  if (!assignmentId || !manuscriptId) return null

  const nestedManuscript = row?.manuscripts && typeof row.manuscripts === 'object' ? row.manuscripts : null
  const title = String(nestedManuscript?.title || row?.manuscript_title || '').trim()
  const abstract = String(nestedManuscript?.abstract || row?.manuscript_abstract || '').trim()
  const filePathRaw = nestedManuscript?.file_path

  return {
    assignmentId,
    manuscript_id: manuscriptId,
    assignment_status: typeof row?.assignment_status === 'string' ? row.assignment_status : null,
    manuscript_title: title || null,
    manuscript_abstract: abstract || null,
    manuscripts: {
      title,
      abstract,
      file_path: typeof filePathRaw === 'string' && filePathRaw.trim() ? filePathRaw : null,
    },
  }
}

function normalizeReviewHistoryItem(row: any): ReviewHistoryItem | null {
  const assignmentId = String(row?.assignment_id || row?.id || '').trim()
  const manuscriptId = String(row?.manuscript_id || '').trim()
  const assignmentState = String(row?.assignment_state || '').trim().toLowerCase()
  if (!assignmentId || !manuscriptId || !assignmentState) return null

  return {
    assignment_id: assignmentId,
    manuscript_id: manuscriptId,
    manuscript_title: typeof row?.manuscript_title === 'string' ? row.manuscript_title : null,
    manuscript_abstract: typeof row?.manuscript_abstract === 'string' ? row.manuscript_abstract : null,
    manuscript_status: typeof row?.manuscript_status === 'string' ? row.manuscript_status : null,
    assignment_status: typeof row?.assignment_status === 'string' ? row.assignment_status : null,
    assignment_state: assignmentState,
    round_number: typeof row?.round_number === 'number' ? row.round_number : null,
    added_on: typeof row?.added_on === 'string' ? row.added_on : null,
    invited_at: typeof row?.invited_at === 'string' ? row.invited_at : null,
    opened_at: typeof row?.opened_at === 'string' ? row.opened_at : null,
    accepted_at: typeof row?.accepted_at === 'string' ? row.accepted_at : null,
    declined_at: typeof row?.declined_at === 'string' ? row.declined_at : null,
    decline_reason: typeof row?.decline_reason === 'string' ? row.decline_reason : null,
    decline_note: typeof row?.decline_note === 'string' ? row.decline_note : null,
    cancelled_at: typeof row?.cancelled_at === 'string' ? row.cancelled_at : null,
    cancel_reason: typeof row?.cancel_reason === 'string' ? row.cancel_reason : null,
    cancel_via: typeof row?.cancel_via === 'string' ? row.cancel_via : null,
    last_reminded_at: typeof row?.last_reminded_at === 'string' ? row.last_reminded_at : null,
    due_at: typeof row?.due_at === 'string' ? row.due_at : null,
    report_status: typeof row?.report_status === 'string' ? row.report_status : null,
    report_submitted_at: typeof row?.report_submitted_at === 'string' ? row.report_submitted_at : null,
    comments_for_author: typeof row?.comments_for_author === 'string' ? row.comments_for_author : null,
    confidential_comments_to_editor:
      typeof row?.confidential_comments_to_editor === 'string' ? row.confidential_comments_to_editor : null,
    report_attachment_filename:
      typeof row?.report_attachment_filename === 'string' ? row.report_attachment_filename : null,
    latest_email_status: typeof row?.latest_email_status === 'string' ? row.latest_email_status : null,
    latest_email_at: typeof row?.latest_email_at === 'string' ? row.latest_email_at : null,
    latest_email_error: typeof row?.latest_email_error === 'string' ? row.latest_email_error : null,
    email_events: Array.isArray(row?.email_events)
      ? row.email_events.map((event: any) => ({
          status: typeof event?.status === 'string' ? event.status : null,
          event_type: typeof event?.event_type === 'string' ? event.event_type : null,
          template_name: typeof event?.template_name === 'string' ? event.template_name : null,
          created_at: typeof event?.created_at === 'string' ? event.created_at : null,
          error_message: typeof event?.error_message === 'string' ? event.error_message : null,
        }))
      : [],
  }
}

function formatDateTime(value?: string | null): string {
  return formatDateTimeLocal(value)
}

function historyStateLabel(state: string): string {
  switch (state) {
    case 'submitted':
      return 'Submitted'
    case 'declined':
      return 'Declined'
    case 'cancelled':
      return 'Cancelled'
    default:
      return state || 'Archived'
  }
}

function historyStateVariant(state: string): 'default' | 'secondary' | 'outline' {
  switch (state) {
    case 'submitted':
      return 'default'
    case 'declined':
      return 'secondary'
    default:
      return 'outline'
  }
}

function buildHistoryTimeline(item: ReviewHistoryItem): HistoryTimelineEvent[] {
  const events: HistoryTimelineEvent[] = []
  const maybePush = (id: string, title: string, timestamp?: string | null, detail?: string | null) => {
    if (!timestamp) return
    events.push({ id, title, timestamp, detail })
  }

  maybePush(`invited-${item.assignment_id}`, 'Invitation sent', item.invited_at)
  maybePush(`opened-${item.assignment_id}`, 'Invitation opened', item.opened_at)
  maybePush(`accepted-${item.assignment_id}`, 'Invitation accepted', item.accepted_at)
  maybePush(`submitted-${item.assignment_id}`, 'Review submitted', item.report_submitted_at)
  maybePush(
    `declined-${item.assignment_id}`,
    'Invitation declined',
    item.declined_at,
    item.decline_reason || item.decline_note || null,
  )
  maybePush(
    `cancelled-${item.assignment_id}`,
    'Assignment cancelled',
    item.cancelled_at,
    item.cancel_reason || item.cancel_via || null,
  )
  maybePush(`reminded-${item.assignment_id}`, 'Reminder recorded', item.last_reminded_at)

  for (const [index, event] of (item.email_events || []).entries()) {
    const status = String(event.status || '').trim().toLowerCase()
    const eventType = String(event.event_type || '').trim().toLowerCase()
    const title =
      eventType === 'reminder'
        ? status === 'failed'
          ? 'Reminder failed'
          : 'Reminder sent'
        : status === 'failed'
          ? 'Invitation failed'
          : 'Invitation email processed'
    const detail = event.error_message || event.template_name || null
    maybePush(`email-${item.assignment_id}-${index}`, title, event.created_at, detail)
  }

  return events.sort((left, right) => {
    const leftTs = Date.parse(left.timestamp)
    const rightTs = Date.parse(right.timestamp)
    return Number.isNaN(rightTs) || Number.isNaN(leftTs) ? 0 : rightTs - leftTs
  })
}

type ReviewData = {
  novelty: number
  rigor: number
  language: number
  commentsForAuthor: string
  confidentialCommentsToEditor: string
  attachment: File | null
}

async function uploadReviewAttachment(taskId: string, token: string, file: File): Promise<string> {
  const formData = new FormData()
  formData.set("attachment", file)
  const uploadRes = await fetch(`/api/v1/reviews/assignments/${encodeURIComponent(taskId)}/attachment`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })
  const uploadJson = await uploadRes.json().catch(() => null)
  if (!uploadRes.ok || !uploadJson?.success || !uploadJson?.data?.attachment_path) {
    throw new Error(normalizeApiErrorMessage(uploadJson, "Attachment upload failed."))
  }
  return String(uploadJson.data.attachment_path)
}

async function submitStructuredReview(params: {
  taskId: string
  token: string
  reviewData: ReviewData
  attachmentPath: string | null
}): Promise<void> {
  const { taskId, token, reviewData, attachmentPath } = params
  const response = await fetch("/api/v1/reviews/submit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      assignment_id: taskId,
      scores: { novelty: reviewData.novelty, rigor: reviewData.rigor, language: reviewData.language },
      comments_for_author: reviewData.commentsForAuthor,
      confidential_comments_to_editor: reviewData.confidentialCommentsToEditor || null,
      attachment_path: attachmentPath,
    }),
  })
  const result = await response.json().catch(() => null)
  if (!response.ok || !result?.success) {
    throw new Error(normalizeApiErrorMessage(result, "Submit failed. Please try again."))
  }
}

function ReviewModal({
  task,
  onClose,
  onSubmitted,
}: {
  task: ReviewTask
  onClose: () => void
  onSubmitted: () => void
}) {
  const [latestRevision, setLatestRevision] = useState<any>(null)
  const [revisionLoading, setRevisionLoading] = useState(false)
  const [reviewData, setReviewData] = useState<ReviewData>({
    novelty: 3,
    rigor: 3,
    language: 3,
    commentsForAuthor: '',
    confidentialCommentsToEditor: '',
    attachment: null,
  })

  useEffect(() => {
    let cancelled = false
    const loadRevisionContext = async () => {
      setLatestRevision(null)
      if (!task?.manuscript_id) return
      setRevisionLoading(true)
      try {
        const token = await authService.getAccessToken()
        if (!token) return
        const res = await fetch(`/api/v1/manuscripts/${encodeURIComponent(task.manuscript_id)}/versions`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const json = await res.json().catch(() => null)
        if (!res.ok || !json?.success) return

        const versions = Array.isArray(json?.data?.versions) ? json.data.versions : []
        const revisions = Array.isArray(json?.data?.revisions) ? json.data.revisions : []
        const latestVersion = versions.reduce((acc: any, cur: any) => {
          if (!acc) return cur
          if ((cur?.version_number ?? 0) > (acc?.version_number ?? 0)) return cur
          return acc
        }, null as any)
        const verNum = Number(latestVersion?.version_number ?? 0)
        if (verNum <= 1) return
        const linked = revisions.find((r: any) => Number(r?.round_number ?? 0) === verNum - 1) || null
        if (cancelled) return
        setLatestRevision(linked)
      } finally {
        if (!cancelled) setRevisionLoading(false)
      }
    }
    loadRevisionContext()
    return () => {
      cancelled = true
    }
  }, [task?.manuscript_id])

  const sanitizedResponseLetter = useMemo(
    () => sanitizeRichHtml(String(latestRevision?.response_letter || '')),
    [latestRevision?.response_letter]
  )

  const handleSubmit = async () => {
    if (!reviewData.commentsForAuthor.trim()) {
      toast.error("Comments for the Authors is required.")
      return
    }

    const toastId = toast.loading("Submitting review...")
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error("Please sign in again.", { id: toastId })
        return
      }

      let attachmentPath: string | null = null
      if (reviewData.attachment) {
        attachmentPath = await uploadReviewAttachment(task.assignmentId, token, reviewData.attachment)
      }

      await submitStructuredReview({
        taskId: task.assignmentId,
        token,
        reviewData,
        attachmentPath,
      })
      toast.success("Review submitted. Thank you!", { id: toastId })
      onClose()
      onSubmitted()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Submit failed. Please try again.", { id: toastId })
    }
  }

  return (
    <Dialog open onOpenChange={(open) => (!open ? onClose() : undefined)}>
      <DialogContent className="w-full sf-max-w-720 min-h-[600px] max-h-[92vh] overflow-y-auto rounded-3xl bg-card p-6 shadow-2xl sm:p-8">
        <DialogHeader className="sr-only">
          <DialogTitle>Structured Peer Review</DialogTitle>
          <DialogDescription>Submit structured review scores and comments for the selected manuscript.</DialogDescription>
        </DialogHeader>
        <div className="mb-6">
          <h4 className="font-serif text-2xl">Structured Peer Review</h4>
          <p className="text-sm text-muted-foreground">
            Submit your professional assessment for &quot;{task.manuscripts?.title}&quot;
          </p>
        </div>

        {/* 复审上下文：大修/小修的编辑请求与作者回应（含图片） */}
        {revisionLoading ? (
          <div className="mb-6 rounded-2xl border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
            正在加载修回上下文…
          </div>
        ) : latestRevision?.editor_comment || latestRevision?.response_letter ? (
          <div className="mb-6 space-y-3">
            {latestRevision?.editor_comment ? (
              <div className="rounded-2xl border border-amber-100 bg-amber-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-amber-800">
                  Editor Request{latestRevision?.decision_type ? ` (${String(latestRevision.decision_type)})` : ''}
                </div>
                <div className="mt-2 whitespace-pre-wrap text-sm text-foreground">
                  {latestRevision.editor_comment}
                </div>
              </div>
            ) : null}
            {latestRevision?.response_letter ? (
              <div className="rounded-2xl border border-border bg-muted/40 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-foreground">
                  Author Response
                </div>
                <div
                  className="mt-2 prose prose-sm max-w-none text-foreground prose-img:max-w-full prose-img:h-auto prose-img:rounded-md"
                  dangerouslySetInnerHTML={{ __html: sanitizedResponseLetter }}
                />
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="py-2 space-y-6 sm:space-y-8">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <Label className="font-semibold text-foreground">Novelty & Originality</Label>
              <span className="text-primary font-mono font-bold text-xl">{reviewData.novelty}/5</span>
            </div>
            <Input
              type="range"
              min="1"
              max="5"
              value={reviewData.novelty}
              onChange={(e) => setReviewData({ ...reviewData, novelty: parseInt(e.target.value) })}
              className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
            />
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <Label className="font-semibold text-foreground">Technical Rigor</Label>
              <span className="text-primary font-mono font-bold text-xl">{reviewData.rigor}/5</span>
            </div>
            <Input
              type="range"
              min="1"
              max="5"
              value={reviewData.rigor}
              onChange={(e) => setReviewData({ ...reviewData, rigor: parseInt(e.target.value) })}
              className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
            />
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <Label className="font-semibold text-foreground">Language Quality</Label>
              <span className="text-primary font-mono font-bold text-xl">{reviewData.language}/5</span>
            </div>
            <Input
              type="range"
              min="1"
              max="5"
              value={reviewData.language}
              onChange={(e) => setReviewData({ ...reviewData, language: parseInt(e.target.value) })}
              className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
            />
          </div>

          <div className="space-y-3">
            <Label className="font-semibold text-foreground">Comments for the Authors</Label>
            <Textarea
              placeholder="Provide detailed feedback for the authors..."
              className="min-h-[140px] sm:min-h-[160px] w-full rounded-2xl border border-border p-3 focus:ring-2 focus:ring-primary"
              value={reviewData.commentsForAuthor}
              onChange={(e) => setReviewData({ ...reviewData, commentsForAuthor: e.target.value })}
            />
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <Label className="font-semibold text-foreground">Confidential Comments to the Editor</Label>
              <span className="text-xs font-semibold text-red-600">Authors will NOT see this</span>
            </div>
            <Textarea
              placeholder="Optional notes for editor only..."
              className="min-h-[110px] w-full rounded-2xl border border-border p-3 focus:ring-2 focus:ring-primary"
              value={reviewData.confidentialCommentsToEditor}
              onChange={(e) => setReviewData({ ...reviewData, confidentialCommentsToEditor: e.target.value })}
            />
          </div>

          <FileUpload
            label="Upload Review Attachment (Optional)"
            helperText="Only Editors and you (the Reviewer) can download this file. Accepted formats: .pdf, .doc, .docx."
            accept={REVIEW_ATTACHMENT_ACCEPT}
            file={reviewData.attachment}
            onFileSelected={(file) => setReviewData({ ...reviewData, attachment: file })}
          />
        </div>

        <div className="mt-8 flex flex-col-reverse sm:flex-row justify-end gap-3">
          <Button onClick={onClose} variant="ghost" className="w-full sm:w-auto">
            Cancel
          </Button>
          <Button onClick={handleSubmit} className="w-full sm:w-auto">
            Submit Decision <Send className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default function ReviewerDashboard() {
  const router = useRouter()
  const [tasks, setTasks] = useState<ReviewTask[]>([])
  const [historyItems, setHistoryItems] = useState<ReviewHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedTask, setSelectedTask] = useState<ReviewTask | null>(null)
  const [selectedHistoryItem, setSelectedHistoryItem] = useState<ReviewHistoryItem | null>(null)
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewTitle, setPreviewTitle] = useState("")
  const [previewLoading, setPreviewLoading] = useState(false)
  const [openingAssignmentId, setOpeningAssignmentId] = useState<string | null>(null)

  const fetchTasks = async () => {
    try {
      const session = await authService.getSession()
      const userId = session?.user?.id
      if (!userId) {
        setTasks([])
        toast.error("Please sign in to view reviewer tasks.")
        return
      }
      const token = await authService.getAccessToken()
      const res = await fetch(`/api/v1/reviews/my-tasks?user_id=${encodeURIComponent(userId)}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      const historyRes = await fetch(`/api/v1/reviews/my-history?user_id=${encodeURIComponent(userId)}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      const [data, historyData] = await Promise.all([res.json(), historyRes.json()])
      const rows = Array.isArray(data?.data) ? data.data : []
      const historyRows = Array.isArray(historyData?.data) ? historyData.data : []
      setTasks(rows.map(normalizeReviewTask).filter((task: ReviewTask | null): task is ReviewTask => Boolean(task)))
      setHistoryItems(
        historyRows
          .map(normalizeReviewHistoryItem)
          .filter((item: ReviewHistoryItem | null): item is ReviewHistoryItem => Boolean(item))
      )
    } catch (e) {
      toast.error("Failed to load tasks.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTasks()
  }, [])

  const handleOpenPreview = async (task: ReviewTask) => {
    if (!task?.manuscripts?.file_path) {
      toast.error("该稿件没有可预览的 PDF（file_path 为空）。请让 Editor 重新上传/绑定文件。")
      return
    }
    setIsPreviewOpen(true)
    setPreviewTitle(task?.manuscripts?.title || "Full Text Preview")
    setPreviewUrl(null)
    setPreviewLoading(true)
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error("Please sign in again.")
        return
      }
      const res = await fetch(`/api/v1/manuscripts/${encodeURIComponent(task.manuscript_id)}/pdf-signed`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const json = await res.json().catch(() => null)
      if (!res.ok || !json?.success || !json?.data?.signed_url) {
        toast.error(json?.detail || json?.message || "Preview not available. Please download the PDF.")
        return
      }
      setPreviewUrl(json.data.signed_url)
    } catch (e) {
      toast.error("Preview failed. Please try again.")
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleClosePreview = () => {
    setIsPreviewOpen(false)
    setPreviewUrl(null)
    setPreviewTitle("")
  }

  const handleOpenReviewerWorkspace = async (task: ReviewTask) => {
    const assignmentId = task.assignmentId
    if (!assignmentId) {
      toast.error("Missing reviewer assignment id.")
      return
    }
    const toastId = toast.loading("Opening reviewer workspace...")
    setOpeningAssignmentId(assignmentId)
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error("Please sign in again.", { id: toastId })
        return
      }
      const res = await fetch(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/session`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      })
      const json = await res.json().catch(() => null)
      if (!res.ok || !json?.success) {
        toast.error(normalizeApiErrorMessage(json, "Failed to open reviewer workspace."), { id: toastId })
        return
      }
      const redirectUrl = typeof json?.data?.redirect_url === 'string' ? json.data.redirect_url.trim() : ''
      if (!redirectUrl) {
        toast.error("Failed to determine next reviewer step.", { id: toastId })
        return
      }
      toast.success(
        redirectUrl.startsWith('/review/invite') ? "Invitation page ready." : "Workspace ready.",
        { id: toastId }
      )
      router.push(redirectUrl)
    } catch {
      toast.error("Failed to open reviewer workspace.", { id: toastId })
    } finally {
      setOpeningAssignmentId(null)
    }
  }

  const handleOpenHistorySubmission = async (item: ReviewHistoryItem) => {
    const assignmentId = item.assignment_id
    if (!assignmentId) {
      toast.error("Missing reviewer assignment id.")
      return
    }
    const toastId = toast.loading("Opening submitted review...")
    setOpeningAssignmentId(assignmentId)
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error("Please sign in again.", { id: toastId })
        return
      }
      const res = await fetch(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/session`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      })
      const json = await res.json().catch(() => null)
      if (!res.ok || !json?.success) {
        toast.error(normalizeApiErrorMessage(json, "Failed to open submitted review."), { id: toastId })
        return
      }
      const redirectUrl = typeof json?.data?.redirect_url === 'string' ? json.data.redirect_url.trim() : ''
      if (!redirectUrl) {
        toast.error("Failed to determine submitted review entry.", { id: toastId })
        return
      }
      toast.success("Submitted review ready.", { id: toastId })
      router.push(redirectUrl)
    } catch {
      toast.error("Failed to open submitted review.", { id: toastId })
    } finally {
      setOpeningAssignmentId(null)
    }
  }

  const activeTaskCount = tasks.length
  const submittedHistoryCount = historyItems.filter((item) => item.assignment_state === 'submitted').length

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1">
            <h2 className="font-serif text-2xl text-foreground">Reviewer Dashboard</h2>
            <p className="text-sm text-muted-foreground">
              Track your active reviews and revisit your own completed review history.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{activeTaskCount} active</Badge>
            <Badge variant="secondary">{submittedHistoryCount} submitted</Badge>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-border bg-card p-10 text-center text-muted-foreground">
          Loading reviewer assignments…
        </div>
      ) : null}
      
      {!loading && tasks.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-card p-10 text-center text-muted-foreground">
          No review tasks assigned to your account yet. Ask the editor to assign you as a reviewer.
        </div>
      ) : !loading ? (
        <div className="grid gap-4">
          {tasks.map((task) => (
            <div key={task.assignmentId} className="rounded-2xl border border-border bg-card hover:shadow-md transition-shadow">
            <div className="flex flex-row items-start justify-between space-y-0 p-6">
              <div className="space-y-1">
                <h3 className="text-xl font-serif font-semibold">{task.manuscripts?.title || task.manuscript_title || "Untitled Manuscript"}</h3>
                <p className="line-clamp-2 italic text-sm text-muted-foreground">{task.manuscripts?.abstract || task.manuscript_abstract || "No abstract available."}</p>
              </div>
              <span className="bg-primary text-white text-xs font-semibold px-3 py-1 rounded-full">PENDING REVIEW</span>
            </div>
            <div className="flex justify-end gap-3 pt-4 border-t border-border/60 p-6">
              <Button
                onClick={() => handleOpenPreview(task)}
                variant="outline"
                size="sm"
                className="gap-2"
                disabled={!task.manuscripts?.file_path}
              >
                <FileText className="h-4 w-4" /> Read Full Text
              </Button>
              
              <Button
                onClick={() => handleOpenReviewerWorkspace(task)}
                size="sm"
                className="gap-2"
                disabled={openingAssignmentId === task.assignmentId}
              >
                <Star className="h-4 w-4" /> {openingAssignmentId === task.assignmentId ? "Opening…" : "Start Review"}
              </Button>
            </div>
            </div>
          ))}
        </div>
      ) : null}

      {!loading ? (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-serif text-xl text-foreground">My Review History</h3>
              <p className="text-sm text-muted-foreground">
                Review your own archived assignments, submitted comments, and communication timeline.
              </p>
            </div>
          </div>

          {historyItems.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border bg-card p-8 text-center text-muted-foreground">
              No archived review history yet.
            </div>
          ) : (
            <div className="grid gap-4">
              {historyItems.map((item) => (
                <div key={item.assignment_id} className="rounded-2xl border border-border bg-card p-6">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="font-serif text-lg text-foreground">
                          {item.manuscript_title || 'Untitled Manuscript'}
                        </h4>
                        <Badge variant={historyStateVariant(item.assignment_state)}>
                          {historyStateLabel(item.assignment_state)}
                        </Badge>
                        {typeof item.round_number === 'number' ? (
                          <Badge variant="outline">Round {item.round_number}</Badge>
                        ) : null}
                      </div>
                      <p className="line-clamp-2 text-sm text-muted-foreground">
                        {item.manuscript_abstract || 'No abstract available.'}
                      </p>
                      <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted-foreground">
                        <span>Invited: {formatDateTime(item.invited_at)}</span>
                        <span>Due: {formatDateTime(item.due_at)}</span>
                        <span>
                          {item.assignment_state === 'submitted'
                            ? `Submitted: ${formatDateTime(item.report_submitted_at)}`
                            : item.assignment_state === 'declined'
                              ? `Declined: ${formatDateTime(item.declined_at)}`
                              : `Cancelled: ${formatDateTime(item.cancelled_at)}`}
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-wrap justify-end gap-2">
                      <Button type="button" variant="outline" size="sm" onClick={() => setSelectedHistoryItem(item)}>
                        View Details
                      </Button>
                      {item.assignment_state === 'submitted' ? (
                        <Button
                          type="button"
                          size="sm"
                          onClick={() => handleOpenHistorySubmission(item)}
                          disabled={openingAssignmentId === item.assignment_id}
                        >
                          {openingAssignmentId === item.assignment_id ? 'Opening…' : 'View Submitted Review'}
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      ) : null}

      <Dialog open={isPreviewOpen} onOpenChange={(open) => (!open ? handleClosePreview() : undefined)}>
        <DialogContent className="h-[80vh] max-h-[90vh] w-full max-w-5xl rounded-3xl bg-card p-6 shadow-2xl sm:p-8 flex flex-col">
            <DialogHeader className="sr-only">
              <DialogTitle>Full Text Preview</DialogTitle>
              <DialogDescription>Preview manuscript PDF in an embedded viewer.</DialogDescription>
            </DialogHeader>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h4 className="font-serif text-2xl text-foreground">Full Text Preview</h4>
                <p className="text-sm text-muted-foreground">{previewTitle || "Manuscript preview"}</p>
              </div>
              <Button
                onClick={handleClosePreview}
                variant="outline"
                size="sm"
              >
                Close
              </Button>
            </div>

            <div className="mt-6 flex-1 min-h-0 rounded-2xl bg-muted border border-border overflow-hidden">
              {previewLoading ? (
                <div className="h-full flex items-center justify-center text-muted-foreground font-medium">
                  Loading preview…
                </div>
              ) : previewUrl ? (
                <iframe src={previewUrl} className="w-full h-full border-0" title="PDF Preview" />
              ) : (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
                    <p className="text-muted-foreground font-medium">No PDF available for preview.</p>
                  </div>
                </div>
              )}
            </div>
            <p className="mt-4 text-xs text-muted-foreground">Preview links expire in 5 minutes.</p>
        </DialogContent>
      </Dialog>

      {isModalOpen && selectedTask && (
        <ReviewModal
          key={selectedTask.manuscript_id}
          task={selectedTask}
          onClose={() => {
            setIsModalOpen(false)
            setSelectedTask(null)
          }}
          onSubmitted={() => fetchTasks()}
        />
      )}

      <SafeDialog open={Boolean(selectedHistoryItem)} onClose={() => setSelectedHistoryItem(null)}>
        <SafeDialogContent className="sm:max-w-3xl">
          {selectedHistoryItem ? (
            <>
              <DialogHeader>
                <DialogTitle>{selectedHistoryItem.manuscript_title || 'Review History'}</DialogTitle>
                <DialogDescription>
                  Archived reviewer-only record for round {selectedHistoryItem.round_number ?? '—'}.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6">
                <div className="grid gap-3 rounded-2xl border border-border bg-muted/30 p-4 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={historyStateVariant(selectedHistoryItem.assignment_state)}>
                      {historyStateLabel(selectedHistoryItem.assignment_state)}
                    </Badge>
                    {selectedHistoryItem.report_attachment_filename ? (
                      <Badge variant="outline">Attachment: {selectedHistoryItem.report_attachment_filename}</Badge>
                    ) : null}
                  </div>
                  <p className="text-muted-foreground">
                    {selectedHistoryItem.manuscript_abstract || 'No abstract available.'}
                  </p>
                  <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-2">
                    <span>Invited: {formatDateTime(selectedHistoryItem.invited_at)}</span>
                    <span>Opened: {formatDateTime(selectedHistoryItem.opened_at)}</span>
                    <span>Accepted: {formatDateTime(selectedHistoryItem.accepted_at)}</span>
                    <span>Due: {formatDateTime(selectedHistoryItem.due_at)}</span>
                  </div>
                </div>

                <div className="grid gap-6 md:grid-cols-2">
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold text-foreground">Comments for Authors</h4>
                    <div className="min-h-[140px] rounded-2xl border border-border bg-background p-4 text-sm text-foreground whitespace-pre-wrap">
                      {selectedHistoryItem.comments_for_author || 'No author-facing comments were recorded.'}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold text-foreground">Confidential Comments to Editor</h4>
                    <div className="min-h-[140px] rounded-2xl border border-border bg-background p-4 text-sm text-foreground whitespace-pre-wrap">
                      {selectedHistoryItem.confidential_comments_to_editor || 'No confidential editor note was recorded.'}
                    </div>
                  </div>
                </div>

                {(selectedHistoryItem.assignment_state === 'declined' || selectedHistoryItem.assignment_state === 'cancelled') ? (
                  <div className="rounded-2xl border border-border bg-muted/20 p-4 text-sm">
                    <h4 className="mb-2 font-semibold text-foreground">Closure Context</h4>
                    <div className="space-y-2 text-muted-foreground">
                      {selectedHistoryItem.decline_reason ? <p>Decline reason: {selectedHistoryItem.decline_reason}</p> : null}
                      {selectedHistoryItem.decline_note ? <p>Decline note: {selectedHistoryItem.decline_note}</p> : null}
                      {selectedHistoryItem.cancel_reason ? <p>Cancel reason: {selectedHistoryItem.cancel_reason}</p> : null}
                      {selectedHistoryItem.cancel_via ? <p>Cancel via: {selectedHistoryItem.cancel_via}</p> : null}
                    </div>
                  </div>
                ) : null}

                <div className="space-y-3">
                  <h4 className="text-sm font-semibold text-foreground">Communication Timeline</h4>
                  <div className="space-y-3">
                    {buildHistoryTimeline(selectedHistoryItem).length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-border p-4 text-sm text-muted-foreground">
                        No communication events recorded for this assignment.
                      </div>
                    ) : (
                      buildHistoryTimeline(selectedHistoryItem).map((event) => (
                        <div key={event.id} className="rounded-2xl border border-border bg-background p-4">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div className="space-y-1">
                              <p className="text-sm font-medium text-foreground">{event.title}</p>
                              {event.detail ? <p className="text-xs text-muted-foreground">{event.detail}</p> : null}
                            </div>
                            <p className="text-xs text-muted-foreground">{formatDateTime(event.timestamp)}</p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </SafeDialogContent>
      </SafeDialog>
    </div>
  )
}
