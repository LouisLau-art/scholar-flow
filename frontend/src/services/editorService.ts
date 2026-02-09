import { EditorApi, type DecisionSubmissionPayload } from '@/services/editorApi'
import type { AcademicDecision, TechnicalDecision } from '@/types/precheck'

/**
 * 兼容历史调用方：逐步迁移到 EditorApi。
 */
export const editorService = {
  getIntakeQueue: async (page = 1, pageSize = 20) => {
    const res = await EditorApi.getIntakeQueue(page, pageSize)
    if (!Array.isArray(res)) {
      throw new Error(res?.detail || res?.message || 'Failed to fetch intake queue')
    }
    return res
  },

  assignAE: async (manuscriptId: string, aeId: string) => {
    const res = await EditorApi.assignAE(manuscriptId, { ae_id: aeId })
    if (!res?.message) {
      throw new Error(res?.detail || res?.message || 'Failed to assign AE')
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
}
