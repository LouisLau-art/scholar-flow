import { EditorApi, type DecisionSubmissionPayload } from '@/services/editorApi'

/**
 * 兼容历史调用方：逐步迁移到 EditorApi。
 */
export const editorService = {
  getIntakeQueue: async (_page = 1, _pageSize = 20) => [],

  assignAE: async (_manuscriptId: string, _aeId: string) => ({ message: 'AE assigned successfully' }),

  getAEWorkspace: async (_page = 1, _pageSize = 20) => [],

  submitTechnicalCheck: async (_id: string) => ({ message: 'Technical check submitted' }),

  getAcademicQueue: async (_page = 1, _pageSize = 20) => [],

  submitAcademicCheck: async (_id: string, _decision: string) => ({ message: 'Academic check submitted' }),

  // Feature 041
  getDecisionContext: async (manuscriptId: string) => EditorApi.getDecisionContext(manuscriptId),

  submitDecision: async (manuscriptId: string, payload: DecisionSubmissionPayload) =>
    EditorApi.submitDecision(manuscriptId, payload),

  uploadDecisionAttachment: async (manuscriptId: string, file: File) =>
    EditorApi.uploadDecisionAttachment(manuscriptId, file),
}
