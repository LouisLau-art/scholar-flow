import type {
  CreateInternalCommentPayload,
  CreateInternalTaskPayload,
  InternalTaskStatus,
  UpdateInternalTaskPayload,
} from '@/types/internal-collaboration'
import type { CachedGetOptions } from './types'

type InternalCollabApiDeps = {
  authedFetch: (input: RequestInfo, init?: RequestInit) => Promise<Response>
  authedGetJsonCached: <T = any>(url: string, options?: CachedGetOptions) => Promise<T>
  invalidateManuscriptInternalCache: (manuscriptId: string) => void
}

export function createInternalCollaborationApi(deps: InternalCollabApiDeps) {
  const { authedFetch, authedGetJsonCached, invalidateManuscriptInternalCache } = deps

  return {
    // Feature 036: Internal Notebook & Audit
    async getInternalComments(manuscriptId: string, options?: CachedGetOptions) {
      return authedGetJsonCached(`/api/v1/editor/manuscripts/${manuscriptId}/comments`, options)
    },

    async postInternalComment(manuscriptId: string, content: string) {
      const payload: CreateInternalCommentPayload = { content }
      const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const json = await res.json()
      if (res.ok && json?.success) invalidateManuscriptInternalCache(manuscriptId)
      return json
    },

    async postInternalCommentWithMentions(manuscriptId: string, payload: CreateInternalCommentPayload) {
      const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const json = await res.json()
      if (res.ok && json?.success) invalidateManuscriptInternalCache(manuscriptId)
      return json
    },

    async listInternalTasks(
      manuscriptId: string,
      filters?: {
        status?: InternalTaskStatus
        overdueOnly?: boolean
      },
      options?: CachedGetOptions
    ) {
      const params = new URLSearchParams()
      if (filters?.status) params.set('status', filters.status)
      if (filters?.overdueOnly) params.set('overdue_only', 'true')
      const query = params.toString()
      return authedGetJsonCached(`/api/v1/editor/manuscripts/${manuscriptId}/tasks${query ? `?${query}` : ''}`, options)
    },

    async createInternalTask(manuscriptId: string, payload: CreateInternalTaskPayload) {
      const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const json = await res.json()
      if (res.ok && json?.success) invalidateManuscriptInternalCache(manuscriptId)
      return json
    },

    async patchInternalTask(manuscriptId: string, taskId: string, payload: UpdateInternalTaskPayload) {
      const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const json = await res.json()
      if (res.ok && json?.success) invalidateManuscriptInternalCache(manuscriptId)
      return json
    },

    async getInternalTaskActivity(manuscriptId: string, taskId: string, options?: CachedGetOptions) {
      return authedGetJsonCached(`/api/v1/editor/manuscripts/${manuscriptId}/tasks/${taskId}/activity`, options)
    },

    async getInternalTasksActivity(
      manuscriptId: string,
      params?: { taskLimit?: number; activityLimit?: number },
      options?: CachedGetOptions
    ) {
      const query = new URLSearchParams()
      if (typeof params?.taskLimit === 'number') query.set('task_limit', String(params.taskLimit))
      if (typeof params?.activityLimit === 'number') query.set('activity_limit', String(params.activityLimit))
      const qs = query.toString()
      return authedGetJsonCached(`/api/v1/editor/manuscripts/${manuscriptId}/tasks/activity${qs ? `?${qs}` : ''}`, options)
    },

    async getTimelineContext(
      manuscriptId: string,
      params?: { taskLimit?: number; activityLimit?: number },
      options?: CachedGetOptions
    ) {
      const query = new URLSearchParams()
      if (typeof params?.taskLimit === 'number') query.set('task_limit', String(params.taskLimit))
      if (typeof params?.activityLimit === 'number') query.set('activity_limit', String(params.activityLimit))
      const qs = query.toString()
      return authedGetJsonCached(`/api/v1/editor/manuscripts/${manuscriptId}/timeline-context${qs ? `?${qs}` : ''}`, options)
    },

    async getAuditLogs(manuscriptId: string, options?: CachedGetOptions) {
      return authedGetJsonCached(`/api/v1/editor/manuscripts/${manuscriptId}/audit-logs`, options)
    },
  }
}
