import type {
  DecisionSubmissionPayload,
  ProductionCycleCreatePayload,
  ProductionCycleEditorsUpdatePayload,
} from './types'

type DecisionProductionApiDeps = {
  authedFetch: (input: RequestInfo, init?: RequestInit) => Promise<Response>
  invalidateManuscriptDetailCache: (manuscriptId: string) => void
  invalidateProcessRowsCache: () => void
}

export function createDecisionProductionApi(deps: DecisionProductionApiDeps) {
  const { authedFetch, invalidateManuscriptDetailCache, invalidateProcessRowsCache } = deps

  return {
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
      const json = await res.json()
      if (res.ok) invalidateManuscriptDetailCache(manuscriptId)
      return json
    },

    async updateProductionCycleEditors(manuscriptId: string, cycleId: string, payload: ProductionCycleEditorsUpdatePayload) {
      const res = await authedFetch(
        `/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/production-cycles/${encodeURIComponent(cycleId)}/editors`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }
      )
      const json = await res.json()
      if (res.ok) invalidateManuscriptDetailCache(manuscriptId)
      return json
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
      const json = await res.json()
      if (res.ok) invalidateManuscriptDetailCache(manuscriptId)
      return json
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
      const json = await res.json()
      if (res.ok) invalidateManuscriptDetailCache(manuscriptId)
      return json
    },

    async listMyProductionQueue(limit = 50) {
      const qs = new URLSearchParams()
      qs.set('limit', String(limit))
      const res = await authedFetch(`/api/v1/editor/production/queue?${qs.toString()}`)
      return res.json()
    },

    async patchManuscriptStatus(manuscriptId: string, status: string, comment?: string) {
      const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, comment }),
      })
      const json = await res.json()
      if (res.ok) {
        invalidateProcessRowsCache()
        invalidateManuscriptDetailCache(manuscriptId)
      }
      return json
    },

    // Feature 031: Post-Acceptance Workflow
    async advanceProduction(manuscriptId: string) {
      const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/production/advance`, {
        method: 'POST',
      })
      const json = await res.json()
      if (res.ok) invalidateManuscriptDetailCache(manuscriptId)
      return json
    },

    async revertProduction(manuscriptId: string) {
      const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/production/revert`, {
        method: 'POST',
      })
      const json = await res.json()
      if (res.ok) invalidateManuscriptDetailCache(manuscriptId)
      return json
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
      const json = await res.json()
      if (res.ok) invalidateManuscriptDetailCache(manuscriptId)
      return json
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
      const json = await res.json()
      if (res.ok) invalidateManuscriptDetailCache(manuscriptId)
      return json
    },

    async bindOwner(manuscriptId: string, ownerId: string) {
      const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/bind-owner`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner_id: ownerId }),
      })
      const json = await res.json()
      if (res.ok) {
        invalidateProcessRowsCache()
        invalidateManuscriptDetailCache(manuscriptId)
      }
      return json
    },

    // Feature 032: Quick Actions
    async quickPrecheck(manuscriptId: string, payload: { decision: 'approve' | 'revision'; comment?: string }) {
      const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/quick-precheck`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const json = await res.json()
      if (res.ok) {
        invalidateProcessRowsCache()
        invalidateManuscriptDetailCache(manuscriptId)
      }
      return json
    },

    // Feature 033: Editor uploads peer review files (internal)
    async uploadPeerReviewFile(manuscriptId: string, file: File) {
      const formData = new FormData()
      formData.append('file', file)
      const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/files/review-attachment`, {
        method: 'POST',
        body: formData,
      })
      const json = await res.json()
      if (res.ok) invalidateManuscriptDetailCache(manuscriptId)
      return json
    },

    async uploadCoverLetterFile(manuscriptId: string, file: File) {
      const formData = new FormData()
      formData.append('file', file)
      const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/files/cover-letter`, {
        method: 'POST',
        body: formData,
      })
      const json = await res.json()
      if (res.ok) invalidateManuscriptDetailCache(manuscriptId)
      return json
    },
  }
}
