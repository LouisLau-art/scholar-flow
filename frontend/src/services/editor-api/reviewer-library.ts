import type { ReviewerLibrarySearchOptions } from './types'

type ReviewerLibraryApiDeps = {
  authedFetch: (input: RequestInfo, init?: RequestInit) => Promise<Response>
  buildReviewerSearchCacheKey: (params: {
    manuscriptId?: string
    query?: string
    limit: number
    page: number
    roleScopeKey?: string
  }) => string
  normalizeRoleScopeKey: (scopeKey?: string) => string
  invalidateReviewerSearchCacheByPredicate: (predicate: (key: string) => boolean) => void
  reviewerSearchCache: Map<string, { expiresAt: number; data: unknown }>
  reviewerSearchInflight: Map<string, Promise<unknown>>
  reviewerLibraryCacheTtlMs: number
}

export function createReviewerLibraryApi(deps: ReviewerLibraryApiDeps) {
  const {
    authedFetch,
    buildReviewerSearchCacheKey,
    normalizeRoleScopeKey,
    invalidateReviewerSearchCacheByPredicate,
    reviewerSearchCache,
    reviewerSearchInflight,
    reviewerLibraryCacheTtlMs,
  } = deps

  return {
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
      const ttlMs = options.ttlMs ?? reviewerLibraryCacheTtlMs
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
  }
}
