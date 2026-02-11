import { EditorApi, type DecisionSubmissionPayload } from '@/services/editorApi'
import type { AcademicDecision, TechnicalDecision } from '@/types/precheck'
import type { CreateInternalTaskPayload, InternalTaskStatus, UpdateInternalTaskPayload } from '@/types/internal-collaboration'
import type { FinanceStatusFilter } from '@/types/finance'

/**
 * 兼容历史调用方：逐步迁移到 EditorApi。
 */
export const editorService = {
  listFinanceInvoices: async (filters?: {
    status?: FinanceStatusFilter
    q?: string
    page?: number
    pageSize?: number
    sortBy?: 'updated_at' | 'amount' | 'status'
    sortOrder?: 'asc' | 'desc'
  }) => {
    const res = await EditorApi.listFinanceInvoices(filters)
    if (!res?.success) {
      throw new Error(res?.detail || res?.message || 'Failed to fetch finance invoices')
    }
    return { data: res.data || [], meta: res.meta }
  },

  exportFinanceInvoices: async (filters?: {
    status?: FinanceStatusFilter
    q?: string
    sortBy?: 'updated_at' | 'amount' | 'status'
    sortOrder?: 'asc' | 'desc'
  }) => {
    return EditorApi.exportFinanceInvoices(filters)
  },

  confirmFinanceInvoicePaid: async (
    manuscriptId: string,
    payload?: { expectedStatus?: 'unpaid' | 'paid' | 'waived'; source?: 'editor_pipeline' | 'finance_page' | 'unknown' }
  ) => {
    const res = await EditorApi.confirmInvoicePaid(manuscriptId, payload)
    if (!res?.success) {
      throw new Error(res?.detail || res?.message || 'Failed to confirm invoice')
    }
    return res.data
  },

  getIntakeQueue: async (page = 1, pageSize = 20, filters?: { q?: string; overdueOnly?: boolean }) => {
    const res = await EditorApi.getIntakeQueue(page, pageSize, filters)
    if (!Array.isArray(res)) {
      throw new Error(res?.detail || res?.message || 'Failed to fetch intake queue')
    }
    return res
  },

  assignAE: async (
    manuscriptId: string,
    aeId: string,
    options?: { startExternalReview?: boolean; bindOwnerIfEmpty?: boolean }
  ) => {
    const res = await EditorApi.assignAE(manuscriptId, {
      ae_id: aeId,
      start_external_review: options?.startExternalReview ?? false,
      bind_owner_if_empty: options?.bindOwnerIfEmpty ?? false,
    })
    if (!res?.message) {
      throw new Error(res?.detail || res?.message || 'Failed to assign AE')
    }
    return res
  },

  submitIntakeRevision: async (manuscriptId: string, comment: string) => {
    const res = await EditorApi.submitIntakeRevision(manuscriptId, { comment })
    if (!res?.message) {
      throw new Error(res?.detail || res?.message || 'Failed to submit intake revision')
    }
    return res
  },

  getAEWorkspace: async (page = 1, pageSize = 20) => {
    const res = await EditorApi.getAEWorkspace(page, pageSize)
    if (!Array.isArray(res)) {
      throw new Error(res?.detail || res?.message || 'Failed to fetch AE workspace')
    }
    return res
  },

  submitTechnicalCheck: async (id: string, payload?: { decision?: TechnicalDecision; comment?: string }) => {
    const res = await EditorApi.submitTechnicalCheck(id, {
      decision: payload?.decision || 'pass',
      comment: payload?.comment,
    })
    if (!res?.message) {
      throw new Error(res?.detail || res?.message || 'Failed to submit technical check')
    }
    return res
  },

  getAcademicQueue: async (page = 1, pageSize = 20) => {
    const res = await EditorApi.getAcademicQueue(page, pageSize)
    if (!Array.isArray(res)) {
      throw new Error(res?.detail || res?.message || 'Failed to fetch academic queue')
    }
    return res
  },

  submitAcademicCheck: async (id: string, decision: AcademicDecision, comment?: string) => {
    const res = await EditorApi.submitAcademicCheck(id, { decision, comment })
    if (!res?.message) {
      throw new Error(res?.detail || res?.message || 'Failed to submit academic check')
    }
    return res
  },

  // Feature 041
  getDecisionContext: async (manuscriptId: string) => EditorApi.getDecisionContext(manuscriptId),

  submitDecision: async (manuscriptId: string, payload: DecisionSubmissionPayload) =>
    EditorApi.submitDecision(manuscriptId, payload),

  uploadDecisionAttachment: async (manuscriptId: string, file: File) =>
    EditorApi.uploadDecisionAttachment(manuscriptId, file),

  getInternalComments: async (manuscriptId: string) => {
    const res = await EditorApi.getInternalComments(manuscriptId)
    if (!res?.success) {
      throw new Error(res?.detail || res?.message || 'Failed to load comments')
    }
    return res.data || []
  },

  postInternalComment: async (manuscriptId: string, content: string, mentionUserIds: string[] = []) => {
    const res = await EditorApi.postInternalCommentWithMentions(manuscriptId, {
      content,
      mention_user_ids: mentionUserIds,
    })
    if (!res?.success) {
      const detail = res?.detail
      if (detail && typeof detail === 'object' && Array.isArray((detail as { invalid_user_ids?: unknown[] }).invalid_user_ids)) {
        throw new Error('Contains invalid mentions')
      }
      throw new Error(res?.detail || res?.message || 'Failed to post comment')
    }
    return res.data
  },

  listInternalTasks: async (manuscriptId: string, filters?: { status?: InternalTaskStatus; overdueOnly?: boolean }) => {
    const res = await EditorApi.listInternalTasks(manuscriptId, filters)
    if (!res?.success) {
      throw new Error(res?.detail || res?.message || 'Failed to load internal tasks')
    }
    return res.data || []
  },

  createInternalTask: async (manuscriptId: string, payload: CreateInternalTaskPayload) => {
    const res = await EditorApi.createInternalTask(manuscriptId, payload)
    if (!res?.success) {
      throw new Error(res?.detail || res?.message || 'Failed to create internal task')
    }
    return res.data
  },

  patchInternalTask: async (manuscriptId: string, taskId: string, payload: UpdateInternalTaskPayload) => {
    const res = await EditorApi.patchInternalTask(manuscriptId, taskId, payload)
    if (!res?.success) {
      throw new Error(res?.detail || res?.message || 'Failed to update internal task')
    }
    return res.data
  },

  getInternalTaskActivity: async (manuscriptId: string, taskId: string) => {
    const res = await EditorApi.getInternalTaskActivity(manuscriptId, taskId)
    if (!res?.success) {
      throw new Error(res?.detail || res?.message || 'Failed to load internal task activity')
    }
    return res.data || []
  },
}
