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
  collaborator_editor_ids?: string[]
  proofreader_author_id: string
  proof_due_at: string
}

export type ProductionCycleEditorsUpdatePayload = {
  layout_editor_id?: string
  collaborator_editor_ids?: string[] | null
}

export type AssignAEPayload = {
  ae_id: string
  owner_id?: string
  start_external_review?: boolean
  bind_owner_if_empty?: boolean
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

type CachedGetOptions = {
  ttlMs?: number
  force?: boolean
}

type ReviewerLibrarySearchOptions = {
  ttlMs?: number
  force?: boolean
  disableCache?: boolean
  roleScopeKey?: string
  page?: number
}

type WorkspaceFetchOptions = CachedGetOptions & {
  signal?: AbortSignal
}

type IntakeQueueFetchOptions = CachedGetOptions & {
  signal?: AbortSignal
}

type ProcessFetchOptions = CachedGetOptions & {
  signal?: AbortSignal
}

type ManuscriptDetailGetOptions = CachedGetOptions & {
  skipCards?: boolean
  includeHeavy?: boolean
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

  async searchReviewerLibrary(
    query?: string,
    limit: number = 50,
    manuscriptId?: string,
    options: ReviewerLibrarySearchOptions = {}
  ) {
    const page = Math.max(1, Number.isFinite(Number(options.page)) ? Number(options.page) : 1)
    const ttlMs = options.ttlMs ?? REVIEWER_LIBRARY_CACHE_TTL_MS
    const force = Boolean(options.force)
    const useCache = !options.disableCache
    const cacheKey = buildReviewerSearchCacheKey({
      manuscriptId,
      query,
      limit,
      page,
      roleScopeKey: options.roleScopeKey,
    })

    if (useCache && !force) {
      const cached = reviewerSearchCache.get(cacheKey)
      if (cached && cached.expiresAt > Date.now()) {
        return cached.data
      }
      const inflight = reviewerSearchInflight.get(cacheKey)
      if (inflight) {
        return inflight
      }
    }

    const params = new URLSearchParams()
    if (query) params.set('query', query)
    params.set('limit', String(limit))
    params.set('page', String(page))
    if (manuscriptId) params.set('manuscript_id', manuscriptId)
    const requestPromise = (async () => {
      const res = await authedFetch(`/api/v1/editor/reviewer-library?${params.toString()}`)
      const json = await res.json().catch(() => ({}))
      if (res.ok && useCache) {
        reviewerSearchCache.set(cacheKey, {
          expiresAt: Date.now() + ttlMs,
          data: json,
        })
      }
      return json
    })()
    reviewerSearchInflight.set(cacheKey, requestPromise)
    try {
      return await requestPromise
    } finally {
      if (reviewerSearchInflight.get(cacheKey) === requestPromise) {
        reviewerSearchInflight.delete(cacheKey)
      }
    }
  },

  invalidateReviewerSearchCache(filters?: { manuscriptId?: string; roleScopeKey?: string }) {
    if (!filters?.manuscriptId && !filters?.roleScopeKey) {
      reviewerSearchCache.clear()
      reviewerSearchInflight.clear()
      return
    }

    const manuscriptToken = filters?.manuscriptId
      ? `ms=${encodeURIComponent(String(filters.manuscriptId).trim())}`
      : null
    const scopeToken = filters?.roleScopeKey
      ? `scope=${encodeURIComponent(normalizeRoleScopeKey(filters.roleScopeKey))}`
      : null

    invalidateReviewerSearchCacheByPredicate((key) => {
      if (manuscriptToken && !key.includes(manuscriptToken)) return false
      if (scopeToken && !key.includes(scopeToken)) return false
      return true
    })
  },

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
