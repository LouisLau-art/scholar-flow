import { authService } from '@/services/auth'
import { createDecisionProductionApi } from './editor-api/decision-production'
import { createFinanceApi } from './editor-api/finance'
import { createInternalCollaborationApi } from './editor-api/internal-collaboration'
import { createReviewerLibraryApi } from './editor-api/reviewer-library'
import type {
  AssignAEPayload,
  CachedGetOptions,
  EditorRbacContextResponse,
  IntakeQueueFetchOptions,
  ManuscriptDetailGetOptions,
  ManuscriptsProcessFilters,
  ProcessFetchOptions,
  SubmitAcademicCheckPayload,
  SubmitIntakeRevisionPayload,
  SubmitTechnicalCheckPayload,
  WorkspaceFetchOptions,
} from './editor-api/types'

export type {
  AssignAEPayload,
  CachedGetOptions,
  DecisionSubmissionPayload,
  EditorRbacContextResponse,
  FinanceInvoiceFilters,
  IntakeQueueFetchOptions,
  ManuscriptDetailGetOptions,
  ManuscriptsProcessFilters,
  ProcessFetchOptions,
  ProductionCycleCreatePayload,
  ProductionCycleEditorsUpdatePayload,
  ReviewerLibrarySearchOptions,
  SubmitAcademicCheckPayload,
  SubmitIntakeRevisionPayload,
  SubmitTechnicalCheckPayload,
  WorkspaceFetchOptions,
} from './editor-api/types'

async function authedFetch(input: RequestInfo, init?: RequestInit) {
  const token = await authService.getAccessToken()
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (token) headers.Authorization = `Bearer ${token}`
  return fetch(input, { ...init, headers })
}

const GET_CACHE_TTL_MS = 8_000
const REVIEWER_LIBRARY_CACHE_TTL_MS = 20_000
const AE_WORKSPACE_CACHE_TTL_MS = 15_000
const MANAGING_WORKSPACE_CACHE_TTL_MS = 15_000
const INTAKE_QUEUE_CACHE_TTL_MS = 15_000
const PROCESS_CACHE_TTL_MS = 12_000
const DETAIL_CACHE_TTL_MS = 10_000
const getJsonCache = new Map<string, { expiresAt: number; data: unknown }>()
const getJsonInflight = new Map<string, Promise<unknown>>()
const reviewerSearchCache = new Map<string, { expiresAt: number; data: unknown }>()
const reviewerSearchInflight = new Map<string, Promise<unknown>>()
const aeWorkspaceCache = new Map<string, { expiresAt: number; data: unknown }>()
const aeWorkspaceInflight = new Map<string, Promise<unknown>>()
const managingWorkspaceCache = new Map<string, { expiresAt: number; data: unknown }>()
const managingWorkspaceInflight = new Map<string, Promise<unknown>>()
const intakeQueueCache = new Map<string, { expiresAt: number; data: unknown }>()
const intakeQueueInflight = new Map<string, Promise<unknown>>()
const processRowsCache = new Map<string, { expiresAt: number; data: unknown }>()
const processRowsInflight = new Map<string, Promise<unknown>>()
const detailCache = new Map<string, { expiresAt: number; data: unknown }>()
const detailInflight = new Map<string, Promise<unknown>>()

function invalidateProcessRowsCache() {
  processRowsCache.clear()
  processRowsInflight.clear()
}

function buildDetailCacheKey(manuscriptId: string, options: ManuscriptDetailGetOptions): string {
  const skipCards = options.skipCards ? '1' : '0'
  const includeHeavy = options.includeHeavy ? '1' : '0'
  return `detail|ms=${encodeURIComponent(manuscriptId)}|skipCards=${skipCards}|includeHeavy=${includeHeavy}`
}

function invalidateGetJsonCache(predicate: (key: string) => boolean) {
  for (const key of Array.from(getJsonCache.keys())) {
    if (predicate(key)) getJsonCache.delete(key)
  }
  for (const key of Array.from(getJsonInflight.keys())) {
    if (predicate(key)) getJsonInflight.delete(key)
  }
}

function invalidateManuscriptInternalCache(manuscriptId: string) {
  const base = `/api/v1/editor/manuscripts/${manuscriptId}`
  invalidateGetJsonCache((key) =>
    key.startsWith(`${base}/comments`) ||
    key.startsWith(`${base}/tasks`) ||
    key.startsWith(`${base}/audit-logs`) ||
      key.startsWith(`${base}/timeline-context`)
  )
}

function invalidateManuscriptDetailCache(manuscriptId: string) {
  const prefix = `detail|ms=${encodeURIComponent(manuscriptId)}|`
  for (const key of Array.from(detailCache.keys())) {
    if (key.startsWith(prefix)) detailCache.delete(key)
  }
  for (const key of Array.from(detailInflight.keys())) {
    if (key.startsWith(prefix)) detailInflight.delete(key)
  }
}

async function authedGetJsonCached<T = any>(url: string, options: CachedGetOptions = {}): Promise<T> {
  const ttlMs = options.ttlMs ?? GET_CACHE_TTL_MS
  const force = Boolean(options.force)
  const now = Date.now()
  if (!force) {
    const cached = getJsonCache.get(url)
    if (cached && cached.expiresAt > now) {
      return cached.data as T
    }
    const inflight = getJsonInflight.get(url)
    if (inflight) {
      return (await inflight) as T
    }
  }

  const requestPromise = (async () => {
    const res = await authedFetch(url)
    const json = await res.json().catch(() => ({}))
    if (res.ok) {
      getJsonCache.set(url, { expiresAt: Date.now() + ttlMs, data: json })
    }
    return json
  })()
  getJsonInflight.set(url, requestPromise)

  try {
    return (await requestPromise) as T
  } finally {
    if (getJsonInflight.get(url) === requestPromise) {
      getJsonInflight.delete(url)
    }
  }
}

function normalizeReviewerQuery(query?: string): string {
  return String(query || '').trim().toLowerCase()
}

function normalizeRoleScopeKey(scopeKey?: string): string {
  const normalized = String(scopeKey || '')
    .split(',')
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean)
    .sort()
  return normalized.length ? normalized.join(',') : 'global'
}

function buildReviewerSearchCacheKey(params: {
  manuscriptId?: string
  query?: string
  limit: number
  page: number
  roleScopeKey?: string
}) {
  const manuscriptKey = encodeURIComponent(String(params.manuscriptId || '__none__').trim())
  const queryKey = encodeURIComponent(normalizeReviewerQuery(params.query))
  const scopeKey = encodeURIComponent(normalizeRoleScopeKey(params.roleScopeKey))
  return `reviewer-search|ms=${manuscriptKey}|scope=${scopeKey}|limit=${params.limit}|page=${params.page}|q=${queryKey}`
}

function invalidateReviewerSearchCacheByPredicate(predicate: (key: string) => boolean) {
  for (const key of Array.from(reviewerSearchCache.keys())) {
    if (predicate(key)) reviewerSearchCache.delete(key)
  }
  for (const key of Array.from(reviewerSearchInflight.keys())) {
    if (predicate(key)) reviewerSearchInflight.delete(key)
  }
}

function buildWorkspaceCacheKey(kind: 'ae' | 'managing', page: number, pageSize: number, q?: string): string {
  const query = encodeURIComponent(String(q || '').trim().toLowerCase())
  return `workspace|kind=${kind}|page=${page}|pageSize=${pageSize}|q=${query}`
}

function buildIntakeQueueCacheKey(page: number, pageSize: number, filters?: { q?: string; overdueOnly?: boolean }): string {
  const query = encodeURIComponent(String(filters?.q || '').trim().toLowerCase())
  const overdue = filters?.overdueOnly ? '1' : '0'
  return `intake|page=${page}|pageSize=${pageSize}|q=${query}|overdue=${overdue}`
}

function buildProcessCacheKey(filters: ManuscriptsProcessFilters): string {
  const normalizedStatuses = (filters.statuses || [])
    .map((item) => String(item || '').trim().toLowerCase())
    .filter(Boolean)
    .sort()
  return [
    `q=${encodeURIComponent(String(filters.q || '').trim().toLowerCase())}`,
    `journal=${encodeURIComponent(String(filters.journalId || '').trim())}`,
    `manuscript=${encodeURIComponent(String(filters.manuscriptId || '').trim())}`,
    `owner=${encodeURIComponent(String(filters.ownerId || '').trim())}`,
    `editor=${encodeURIComponent(String(filters.editorId || '').trim())}`,
    `overdue=${filters.overdueOnly ? '1' : '0'}`,
    `statuses=${encodeURIComponent(normalizedStatuses.join(','))}`,
  ].join('|')
}

function getFilenameFromContentDisposition(contentDisposition: string | null) {
  if (!contentDisposition) return 'finance_invoices.csv'
  const m = /filename="?([^"]+)"?/i.exec(contentDisposition)
  return m?.[1] || 'finance_invoices.csv'
}

const financeApi = createFinanceApi({
  authedFetch,
  getFilenameFromContentDisposition,
})

const reviewerLibraryApi = createReviewerLibraryApi({
  authedFetch,
  buildReviewerSearchCacheKey,
  normalizeRoleScopeKey,
  invalidateReviewerSearchCacheByPredicate,
  reviewerSearchCache,
  reviewerSearchInflight,
  reviewerLibraryCacheTtlMs: REVIEWER_LIBRARY_CACHE_TTL_MS,
})

const internalCollaborationApi = createInternalCollaborationApi({
  authedFetch,
  authedGetJsonCached,
  invalidateManuscriptInternalCache,
})

const decisionProductionApi = createDecisionProductionApi({
  authedFetch,
  invalidateManuscriptDetailCache,
  invalidateProcessRowsCache,
})

export const EditorApi = {
  ...financeApi,

  async listJournals() {
    const res = await authedFetch('/api/v1/editor/journals')
    return res.json()
  },

  async getRbacContext(options?: CachedGetOptions): Promise<EditorRbacContextResponse> {
    return authedGetJsonCached('/api/v1/editor/rbac/context', options)
  },

  async listInternalStaff(
    search?: string,
    options?: { excludeCurrentUser?: boolean },
    cacheOptions?: CachedGetOptions
  ) {
    const params = new URLSearchParams()
    if (search) params.set('search', search)
    if (options?.excludeCurrentUser) params.set('exclude_current_user', 'true')
    const qs = params.toString()
    return authedGetJsonCached(`/api/v1/editor/internal-staff${qs ? `?${qs}` : ''}`, cacheOptions)
  },

  // Feature 044: Pre-check role workflow
  async listAssistantEditors(search?: string) {
    const qs = search ? `?search=${encodeURIComponent(search)}` : ''
    const res = await authedFetch(`/api/v1/editor/assistant-editors${qs}`)
    return res.json()
  },

  async getIntakeQueue(
    page = 1,
    pageSize = 20,
    filters?: { q?: string; overdueOnly?: boolean },
    options?: IntakeQueueFetchOptions
  ) {
    const force = Boolean(options?.force)
    const ttlMs = options?.ttlMs ?? INTAKE_QUEUE_CACHE_TTL_MS
    const cacheKey = buildIntakeQueueCacheKey(page, pageSize, filters)
    const now = Date.now()
    if (!force) {
      const cached = intakeQueueCache.get(cacheKey)
      if (cached && cached.expiresAt > now) {
        return cached.data
      }
      const inflight = intakeQueueInflight.get(cacheKey)
      if (inflight) return inflight
    }

    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('page_size', String(pageSize))
    if (filters?.q) params.set('q', filters.q)
    if (filters?.overdueOnly) params.set('overdue_only', 'true')
    const requestPromise = (async () => {
      const res = await authedFetch(`/api/v1/editor/intake?${params.toString()}`, {
        signal: options?.signal,
        headers: force ? { 'x-sf-force-refresh': '1' } : undefined,
      })
      const json = await res.json().catch(() => [])
      if (res.ok && Array.isArray(json)) {
        intakeQueueCache.set(cacheKey, {
          expiresAt: Date.now() + ttlMs,
          data: json,
        })
      }
      return json
    })()
    intakeQueueInflight.set(cacheKey, requestPromise)
    try {
      return await requestPromise
    } finally {
      if (intakeQueueInflight.get(cacheKey) === requestPromise) {
        intakeQueueInflight.delete(cacheKey)
      }
    }
  },

  async assignAE(manuscriptId: string, payload: AssignAEPayload) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/assign-ae`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const json = await res.json()
    if (res.ok) {
      intakeQueueCache.clear()
      intakeQueueInflight.clear()
      invalidateProcessRowsCache()
      invalidateManuscriptDetailCache(manuscriptId)
    }
    return json
  },

  async submitIntakeRevision(manuscriptId: string, payload: SubmitIntakeRevisionPayload) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/intake-return`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const json = await res.json()
    if (res.ok) {
      intakeQueueCache.clear()
      intakeQueueInflight.clear()
      invalidateProcessRowsCache()
      invalidateManuscriptDetailCache(manuscriptId)
    }
    return json
  },

  async getAEWorkspace(page = 1, pageSize = 20, options?: WorkspaceFetchOptions) {
    const force = Boolean(options?.force)
    const ttlMs = options?.ttlMs ?? AE_WORKSPACE_CACHE_TTL_MS
    const cacheKey = buildWorkspaceCacheKey('ae', page, pageSize)
    const now = Date.now()
    if (!force) {
      const cached = aeWorkspaceCache.get(cacheKey)
      if (cached && cached.expiresAt > now) {
        return cached.data
      }
      const inflight = aeWorkspaceInflight.get(cacheKey)
      if (inflight) return inflight
    }

    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('page_size', String(pageSize))
    const requestPromise = (async () => {
      const res = await authedFetch(`/api/v1/editor/workspace?${params.toString()}`, {
        signal: options?.signal,
        headers: force ? { 'x-sf-force-refresh': '1' } : undefined,
      })
      const json = await res.json().catch(() => [])
      if (res.ok && Array.isArray(json)) {
        aeWorkspaceCache.set(cacheKey, {
          expiresAt: Date.now() + ttlMs,
          data: json,
        })
      }
      return json
    })()
    aeWorkspaceInflight.set(cacheKey, requestPromise)
    try {
      return await requestPromise
    } finally {
      if (aeWorkspaceInflight.get(cacheKey) === requestPromise) {
        aeWorkspaceInflight.delete(cacheKey)
      }
    }
  },

  async getManagingWorkspace(
    page = 1,
    pageSize = 20,
    q?: string,
    options?: WorkspaceFetchOptions
  ) {
    const force = Boolean(options?.force)
    const ttlMs = options?.ttlMs ?? MANAGING_WORKSPACE_CACHE_TTL_MS
    const cacheKey = buildWorkspaceCacheKey('managing', page, pageSize, q)
    const now = Date.now()
    if (!force) {
      const cached = managingWorkspaceCache.get(cacheKey)
      if (cached && cached.expiresAt > now) {
        return cached.data
      }
      const inflight = managingWorkspaceInflight.get(cacheKey)
      if (inflight) return inflight
    }

    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('page_size', String(pageSize))
    if (q && String(q).trim()) params.set('q', String(q).trim())
    const requestPromise = (async () => {
      const res = await authedFetch(`/api/v1/editor/managing-workspace?${params.toString()}`, {
        signal: options?.signal,
        headers: force ? { 'x-sf-force-refresh': '1' } : undefined,
      })
      const json = await res.json().catch(() => [])
      if (res.ok && Array.isArray(json)) {
        managingWorkspaceCache.set(cacheKey, {
          expiresAt: Date.now() + ttlMs,
          data: json,
        })
      }
      return json
    })()
    managingWorkspaceInflight.set(cacheKey, requestPromise)
    try {
      return await requestPromise
    } finally {
      if (managingWorkspaceInflight.get(cacheKey) === requestPromise) {
        managingWorkspaceInflight.delete(cacheKey)
      }
    }
  },

  async submitTechnicalCheck(manuscriptId: string, payload: SubmitTechnicalCheckPayload) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/submit-check`, {
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

  async getAcademicQueue(page = 1, pageSize = 20) {
    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('page_size', String(pageSize))
    const res = await authedFetch(`/api/v1/editor/academic?${params.toString()}`)
    return res.json()
  },

  async getFinalDecisionQueue(page = 1, pageSize = 20) {
    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('page_size', String(pageSize))
    const res = await authedFetch(`/api/v1/editor/final-decision?${params.toString()}`)
    return res.json()
  },

  async submitAcademicCheck(manuscriptId: string, payload: SubmitAcademicCheckPayload) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/academic-check`, {
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

  async getManuscriptsProcess(filters: ManuscriptsProcessFilters, options?: ProcessFetchOptions) {
    const force = Boolean(options?.force)
    const ttlMs = options?.ttlMs ?? PROCESS_CACHE_TTL_MS
    const cacheKey = buildProcessCacheKey(filters)
    const now = Date.now()
    if (!force) {
      const cached = processRowsCache.get(cacheKey)
      if (cached && cached.expiresAt > now) {
        return cached.data
      }
      const inflight = processRowsInflight.get(cacheKey)
      if (inflight) return inflight
    }

    const params = new URLSearchParams()
    if (filters.q) params.set('q', filters.q)
    if (filters.journalId) params.set('journal_id', filters.journalId)
    if (filters.manuscriptId) params.set('manuscript_id', filters.manuscriptId)
    if (filters.ownerId) params.set('owner_id', filters.ownerId)
    if (filters.editorId) params.set('editor_id', filters.editorId)
    if (filters.overdueOnly) params.set('overdue_only', 'true')
    for (const s of filters.statuses || []) params.append('status', s)
    const qs = params.toString()
    const requestPromise = (async () => {
      const res = await authedFetch(`/api/v1/editor/manuscripts/process${qs ? `?${qs}` : ''}`, {
        signal: options?.signal,
        headers: force ? { 'x-sf-force-refresh': '1' } : undefined,
      })
      const json = await res.json().catch(() => ({}))
      if (res.ok && (json as { success?: boolean })?.success !== false) {
        processRowsCache.set(cacheKey, {
          expiresAt: Date.now() + ttlMs,
          data: json,
        })
      }
      return json
    })()
    processRowsInflight.set(cacheKey, requestPromise)
    try {
      return await requestPromise
    } finally {
      if (processRowsInflight.get(cacheKey) === requestPromise) {
        processRowsInflight.delete(cacheKey)
      }
    }
  },

  async getManuscriptDetail(manuscriptId: string, options: ManuscriptDetailGetOptions = {}) {
    const params = new URLSearchParams()
    if (options?.skipCards) params.set('skip_cards', 'true')
    if (options?.includeHeavy) params.set('include_heavy', 'true')
    const qs = params.toString()
    const url = `/api/v1/editor/manuscripts/${manuscriptId}${qs ? `?${qs}` : ''}`
    const cacheKey = buildDetailCacheKey(manuscriptId, options)
    const ttlMs = options.ttlMs ?? DETAIL_CACHE_TTL_MS
    const force = Boolean(options.force)
    const now = Date.now()
    if (!force) {
      const cached = detailCache.get(cacheKey)
      if (cached && cached.expiresAt > now) return cached.data
      const inflight = detailInflight.get(cacheKey)
      if (inflight) return inflight
    }
    const requestPromise = (async () => {
      const res = await authedFetch(url, {
        headers: force ? { 'x-sf-force-refresh': '1' } : undefined,
      })
      const json = await res.json().catch(() => ({}))
      if (res.ok) {
        detailCache.set(cacheKey, {
          expiresAt: Date.now() + ttlMs,
          data: json,
        })
      }
      return json
    })()
    detailInflight.set(cacheKey, requestPromise)
    try {
      return await requestPromise
    } finally {
      if (detailInflight.get(cacheKey) === requestPromise) {
        detailInflight.delete(cacheKey)
      }
    }
  },

  async getManuscriptCardsContext(manuscriptId: string, options?: CachedGetOptions) {
    return authedGetJsonCached(`/api/v1/editor/manuscripts/${encodeURIComponent(manuscriptId)}/cards-context`, options)
  },

  async getManuscriptReviews(manuscriptId: string, options?: CachedGetOptions) {
    return authedGetJsonCached(`/api/v1/manuscripts/${encodeURIComponent(manuscriptId)}/reviews`, options)
  },
  ...decisionProductionApi,

  ...reviewerLibraryApi,

  invalidateAEWorkspaceCache() {
    aeWorkspaceCache.clear()
    aeWorkspaceInflight.clear()
  },

  invalidateManagingWorkspaceCache() {
    managingWorkspaceCache.clear()
    managingWorkspaceInflight.clear()
  },

  invalidateIntakeQueueCache() {
    intakeQueueCache.clear()
    intakeQueueInflight.clear()
  },

  invalidateManuscriptsProcessCache() {
    invalidateProcessRowsCache()
  },

  ...internalCollaborationApi,
}
