import type {
  AssignAEPayload,
  CachedGetOptions,
  IntakeQueueFetchOptions,
  ManuscriptDetailGetOptions,
  ManuscriptsProcessFilters,
  ProcessFetchOptions,
  SubmitAcademicCheckPayload,
  SubmitIntakeRevisionPayload,
  SubmitTechnicalCheckPayload,
  WorkspaceFetchOptions,
} from './types'

type CacheEntry = {
  expiresAt: number
  data: unknown
}

type ManuscriptsApiDeps = {
  authedFetch: (input: RequestInfo, init?: RequestInit) => Promise<Response>
  authedGetJsonCached: <T = any>(url: string, options?: CachedGetOptions) => Promise<T>
  buildIntakeQueueCacheKey: (page: number, pageSize: number, filters?: { q?: string; overdueOnly?: boolean }) => string
  buildWorkspaceCacheKey: (kind: 'ae' | 'managing', page: number, pageSize: number, q?: string) => string
  buildProcessCacheKey: (filters: ManuscriptsProcessFilters) => string
  buildDetailCacheKey: (manuscriptId: string, options: ManuscriptDetailGetOptions) => string
  intakeQueueCache: Map<string, CacheEntry>
  intakeQueueInflight: Map<string, Promise<unknown>>
  aeWorkspaceCache: Map<string, CacheEntry>
  aeWorkspaceInflight: Map<string, Promise<unknown>>
  managingWorkspaceCache: Map<string, CacheEntry>
  managingWorkspaceInflight: Map<string, Promise<unknown>>
  processRowsCache: Map<string, CacheEntry>
  processRowsInflight: Map<string, Promise<unknown>>
  detailCache: Map<string, CacheEntry>
  detailInflight: Map<string, Promise<unknown>>
  intakeQueueCacheTtlMs: number
  aeWorkspaceCacheTtlMs: number
  managingWorkspaceCacheTtlMs: number
  processCacheTtlMs: number
  detailCacheTtlMs: number
  invalidateProcessRowsCache: () => void
  invalidateManuscriptDetailCache: (manuscriptId: string) => void
}

export function createManuscriptsApi(deps: ManuscriptsApiDeps) {
  const {
    authedFetch,
    authedGetJsonCached,
    buildIntakeQueueCacheKey,
    buildWorkspaceCacheKey,
    buildProcessCacheKey,
    buildDetailCacheKey,
    intakeQueueCache,
    intakeQueueInflight,
    aeWorkspaceCache,
    aeWorkspaceInflight,
    managingWorkspaceCache,
    managingWorkspaceInflight,
    processRowsCache,
    processRowsInflight,
    detailCache,
    detailInflight,
    intakeQueueCacheTtlMs,
    aeWorkspaceCacheTtlMs,
    managingWorkspaceCacheTtlMs,
    processCacheTtlMs,
    detailCacheTtlMs,
    invalidateProcessRowsCache,
    invalidateManuscriptDetailCache,
  } = deps

  return {
    async getIntakeQueue(
      page = 1,
      pageSize = 20,
      filters?: { q?: string; overdueOnly?: boolean },
      options?: IntakeQueueFetchOptions
    ) {
      const force = Boolean(options?.force)
      const ttlMs = options?.ttlMs ?? intakeQueueCacheTtlMs
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
      const ttlMs = options?.ttlMs ?? aeWorkspaceCacheTtlMs
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

    async getManagingWorkspace(page = 1, pageSize = 20, q?: string, options?: WorkspaceFetchOptions) {
      const force = Boolean(options?.force)
      const ttlMs = options?.ttlMs ?? managingWorkspaceCacheTtlMs
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
      const ttlMs = options?.ttlMs ?? processCacheTtlMs
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
      const ttlMs = options.ttlMs ?? detailCacheTtlMs
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
  }
}
