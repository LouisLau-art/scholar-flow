import { authService } from '@/services/auth'
import type { AcademicDecision, TechnicalDecision } from '@/types/precheck'
import type {
  CreateInternalCommentPayload,
  CreateInternalTaskPayload,
  UpdateInternalTaskPayload,
  InternalTaskStatus,
} from '@/types/internal-collaboration'
import type {
  FinanceExportResponse,
  FinanceInvoiceListResponse,
  FinanceSortBy,
  FinanceSortOrder,
  FinanceStatusFilter,
} from '@/types/finance'
import type { EditorRbacContext } from '@/types/rbac'

export type ManuscriptsProcessFilters = {
  q?: string
  journalId?: string
  manuscriptId?: string
  statuses?: string[]
  ownerId?: string
  editorId?: string
  overdueOnly?: boolean
}

export type FinanceInvoiceFilters = {
  status?: FinanceStatusFilter
  q?: string
  page?: number
  pageSize?: number
  sortBy?: FinanceSortBy
  sortOrder?: FinanceSortOrder
}

export type EditorRbacContextResponse = {
  success: boolean
  data?: EditorRbacContext
  detail?: string
  message?: string
}

export type DecisionSubmissionPayload = {
  content: string
  decision: 'accept' | 'reject' | 'major_revision' | 'minor_revision'
  is_final: boolean
  decision_stage?: 'first' | 'final'
  attachment_paths: string[]
  last_updated_at: string | null
}

export type ProductionCycleCreatePayload = {
  layout_editor_id: string
  proofreader_author_id: string
  proof_due_at: string
}

export type AssignAEPayload = {
  ae_id: string
  idempotency_key?: string
}

export type SubmitIntakeRevisionPayload = {
  comment: string
  idempotency_key?: string
}

export type SubmitTechnicalCheckPayload = {
  decision: TechnicalDecision
  comment?: string
  idempotency_key?: string
}

export type SubmitAcademicCheckPayload = {
  decision: AcademicDecision
  comment?: string
  idempotency_key?: string
}

async function authedFetch(input: RequestInfo, init?: RequestInit) {
  const token = await authService.getAccessToken()
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (token) headers.Authorization = `Bearer ${token}`
  return fetch(input, { ...init, headers })
}

function getFilenameFromContentDisposition(contentDisposition: string | null) {
  if (!contentDisposition) return 'finance_invoices.csv'
  const m = /filename="?([^"]+)"?/i.exec(contentDisposition)
  return m?.[1] || 'finance_invoices.csv'
}

export const EditorApi = {
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

  async listJournals() {
    const res = await authedFetch('/api/v1/editor/journals')
    return res.json()
  },

  async getRbacContext(): Promise<EditorRbacContextResponse> {
    const res = await authedFetch('/api/v1/editor/rbac/context')
    return res.json()
  },

  async listInternalStaff(search?: string) {
    const qs = search ? `?search=${encodeURIComponent(search)}` : ''
    const res = await authedFetch(`/api/v1/editor/internal-staff${qs}`)
    return res.json()
  },

  // Feature 044: Pre-check role workflow
  async listAssistantEditors(search?: string) {
    const qs = search ? `?search=${encodeURIComponent(search)}` : ''
    const res = await authedFetch(`/api/v1/editor/assistant-editors${qs}`)
    return res.json()
  },

  async getIntakeQueue(page = 1, pageSize = 20) {
    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('page_size', String(pageSize))
    const res = await authedFetch(`/api/v1/editor/intake?${params.toString()}`)
    return res.json()
  },

  async assignAE(manuscriptId: string, payload: AssignAEPayload) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/assign-ae`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async submitIntakeRevision(manuscriptId: string, payload: SubmitIntakeRevisionPayload) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/intake-return`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async getAEWorkspace(page = 1, pageSize = 20) {
    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('page_size', String(pageSize))
    const res = await authedFetch(`/api/v1/editor/workspace?${params.toString()}`)
    return res.json()
  },

  async submitTechnicalCheck(manuscriptId: string, payload: SubmitTechnicalCheckPayload) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/submit-check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async getAcademicQueue(page = 1, pageSize = 20) {
    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('page_size', String(pageSize))
    const res = await authedFetch(`/api/v1/editor/academic?${params.toString()}`)
    return res.json()
  },

  async submitAcademicCheck(manuscriptId: string, payload: SubmitAcademicCheckPayload) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/academic-check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async getManuscriptsProcess(filters: ManuscriptsProcessFilters) {
    const params = new URLSearchParams()
    if (filters.q) params.set('q', filters.q)
    if (filters.journalId) params.set('journal_id', filters.journalId)
    if (filters.manuscriptId) params.set('manuscript_id', filters.manuscriptId)
    if (filters.ownerId) params.set('owner_id', filters.ownerId)
    if (filters.editorId) params.set('editor_id', filters.editorId)
    if (filters.overdueOnly) params.set('overdue_only', 'true')
    for (const s of filters.statuses || []) params.append('status', s)
    const qs = params.toString()
    const res = await authedFetch(`/api/v1/editor/manuscripts/process${qs ? `?${qs}` : ''}`)
    return res.json()
  },

  async getManuscriptDetail(manuscriptId: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}`)
    return res.json()
  },

  async getDecisionContext(manuscriptId: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/decision-context`)
    return res.json()
  },

  async submitDecision(manuscriptId: string, payload: DecisionSubmissionPayload) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/submit-decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async uploadDecisionAttachment(manuscriptId: string, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/decision-attachments`, {
      method: 'POST',
      body: formData,
    })
    return res.json()
  },

  async getDecisionAttachmentSignedUrl(manuscriptId: string, attachmentId: string) {
    const res = await authedFetch(
      `/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/decision-attachments/${encodeURIComponent(
        attachmentId
      )}/signed-url`
    )
    return res.json()
  },

  async getProductionWorkspaceContext(manuscriptId: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/production-workspace`)
    return res.json()
  },

  async createProductionCycle(manuscriptId: string, payload: ProductionCycleCreatePayload) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/production-cycles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async uploadProductionGalley(
    manuscriptId: string,
    cycleId: string,
    payload: { file: File; version_note: string; proof_due_at?: string }
  ) {
    const formData = new FormData()
    formData.append('file', payload.file)
    formData.append('version_note', payload.version_note)
    if (payload.proof_due_at) formData.append('proof_due_at', payload.proof_due_at)
    const res = await authedFetch(
      `/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/production-cycles/${encodeURIComponent(cycleId)}/galley`,
      {
        method: 'POST',
        body: formData,
      }
    )
    return res.json()
  },

  async getProductionGalleySignedUrl(manuscriptId: string, cycleId: string) {
    const res = await authedFetch(
      `/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/production-cycles/${encodeURIComponent(cycleId)}/galley-signed`
    )
    return res.json()
  },

  async approveProductionCycle(manuscriptId: string, cycleId: string) {
    const res = await authedFetch(
      `/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/production-cycles/${encodeURIComponent(cycleId)}/approve`,
      {
        method: 'POST',
      }
    )
    return res.json()
  },

  async patchManuscriptStatus(manuscriptId: string, status: string, comment?: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, comment }),
    })
    return res.json()
  },

  // Feature 031: Post-Acceptance Workflow
  async advanceProduction(manuscriptId: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/production/advance`, {
      method: 'POST',
    })
    return res.json()
  },

  async revertProduction(manuscriptId: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/production/revert`, {
      method: 'POST',
    })
    return res.json()
  },

  async confirmInvoicePaid(
    manuscriptId: string,
    payload?: {
      expectedStatus?: 'unpaid' | 'paid' | 'waived'
      source?: 'editor_pipeline' | 'finance_page' | 'unknown'
    }
  ) {
    const res = await authedFetch('/api/v1/editor/invoices/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        manuscript_id: manuscriptId,
        expected_status: payload?.expectedStatus,
        source: payload?.source || 'unknown',
      }),
    })
    return res.json()
  },

  async updateInvoiceInfo(
    manuscriptId: string,
    payload: { authors?: string; affiliation?: string; apc_amount?: number; funding_info?: string }
  ) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/invoice-info`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async bindOwner(manuscriptId: string, ownerId: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/bind-owner`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner_id: ownerId }),
    })
    return res.json()
  },

  // Feature 032: Quick Actions
  async quickPrecheck(manuscriptId: string, payload: { decision: 'approve' | 'revision'; comment?: string }) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/quick-precheck`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  // Feature 033: Editor uploads peer review files (internal)
  async uploadPeerReviewFile(manuscriptId: string, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/files/review-attachment`, {
      method: 'POST',
      body: formData,
    })
    return res.json()
  },

  // Feature 030: Reviewer Library
  async addReviewerToLibrary(payload: {
    email: string
    full_name: string
    title: string
    affiliation?: string
    homepage_url?: string
    research_interests?: string[]
  }) {
    const res = await authedFetch('/api/v1/editor/reviewer-library', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async searchReviewerLibrary(query?: string, limit: number = 50, manuscriptId?: string) {
    const params = new URLSearchParams()
    if (query) params.set('query', query)
    params.set('limit', String(limit))
    if (manuscriptId) params.set('manuscript_id', manuscriptId)
    const res = await authedFetch(`/api/v1/editor/reviewer-library?${params.toString()}`)
    return res.json()
  },

  async updateReviewerLibraryItem(reviewerId: string, payload: Record<string, any>) {
    const res = await authedFetch(`/api/v1/editor/reviewer-library/${encodeURIComponent(reviewerId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async deactivateReviewerLibraryItem(reviewerId: string) {
    const res = await authedFetch(`/api/v1/editor/reviewer-library/${encodeURIComponent(reviewerId)}`, {
      method: 'DELETE',
    })
    return res.json()
  },

  // Feature 036: Internal Notebook & Audit
  async getInternalComments(manuscriptId: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/comments`)
    return res.json()
  },

  async postInternalComment(manuscriptId: string, content: string) {
    const payload: CreateInternalCommentPayload = { content }
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async postInternalCommentWithMentions(manuscriptId: string, payload: CreateInternalCommentPayload) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async listInternalTasks(
    manuscriptId: string,
    filters?: {
      status?: InternalTaskStatus
      overdueOnly?: boolean
    }
  ) {
    const params = new URLSearchParams()
    if (filters?.status) params.set('status', filters.status)
    if (filters?.overdueOnly) params.set('overdue_only', 'true')
    const query = params.toString()
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/tasks${query ? `?${query}` : ''}`)
    return res.json()
  },

  async createInternalTask(manuscriptId: string, payload: CreateInternalTaskPayload) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async patchInternalTask(manuscriptId: string, taskId: string, payload: UpdateInternalTaskPayload) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/tasks/${taskId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async getInternalTaskActivity(manuscriptId: string, taskId: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/tasks/${taskId}/activity`)
    return res.json()
  },

  async getAuditLogs(manuscriptId: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/audit-logs`)
    return res.json()
  },
}
