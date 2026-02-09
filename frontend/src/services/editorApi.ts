import { authService } from '@/services/auth'

export type ManuscriptsProcessFilters = {
  q?: string
  journalId?: string
  manuscriptId?: string
  statuses?: string[]
  ownerId?: string
  editorId?: string
}

export type DecisionSubmissionPayload = {
  content: string
  decision: 'accept' | 'reject' | 'major_revision' | 'minor_revision'
  is_final: boolean
  attachment_paths: string[]
  last_updated_at: string | null
}

async function authedFetch(input: RequestInfo, init?: RequestInit) {
  const token = await authService.getAccessToken()
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (token) headers.Authorization = `Bearer ${token}`
  return fetch(input, { ...init, headers })
}

export const EditorApi = {
  async listJournals() {
    const res = await authedFetch('/api/v1/editor/journals')
    return res.json()
  },

  async listInternalStaff(search?: string) {
    const qs = search ? `?search=${encodeURIComponent(search)}` : ''
    const res = await authedFetch(`/api/v1/editor/internal-staff${qs}`)
    return res.json()
  },

  async getManuscriptsProcess(filters: ManuscriptsProcessFilters) {
    const params = new URLSearchParams()
    if (filters.q) params.set('q', filters.q)
    if (filters.journalId) params.set('journal_id', filters.journalId)
    if (filters.manuscriptId) params.set('manuscript_id', filters.manuscriptId)
    if (filters.ownerId) params.set('owner_id', filters.ownerId)
    if (filters.editorId) params.set('editor_id', filters.editorId)
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

  async confirmInvoicePaid(manuscriptId: string) {
    const res = await authedFetch('/api/v1/editor/invoices/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ manuscript_id: manuscriptId }),
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

  async searchReviewerLibrary(query?: string, limit: number = 50) {
    const params = new URLSearchParams()
    if (query) params.set('query', query)
    params.set('limit', String(limit))
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
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
    return res.json()
  },

  async getAuditLogs(manuscriptId: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/audit-logs`)
    return res.json()
  },
}
