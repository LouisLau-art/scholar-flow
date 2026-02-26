import { createDecisionProductionApi } from './editor-api/decision-production'
import { createFinanceApi } from './editor-api/finance'
import { authedFetch, createAuthedGetJsonCached, getFilenameFromContentDisposition } from './editor-api/http'
import { createInternalCollaborationApi } from './editor-api/internal-collaboration'
import { createManuscriptsApi } from './editor-api/manuscripts'
import { createRbacApi } from './editor-api/rbac'
import { createReviewerLibraryApi } from './editor-api/reviewer-library'
import type {
  CachedGetOptions,
  ManuscriptDetailGetOptions,
  ManuscriptsProcessFilters,
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

const authedGetJsonCached = createAuthedGetJsonCached({
  authedFetch,
  getJsonCache,
  getJsonInflight,
  defaultTtlMs: GET_CACHE_TTL_MS,
})

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

const rbacApi = createRbacApi({
  authedFetch,
  authedGetJsonCached,
})

const manuscriptsApi = createManuscriptsApi({
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
  intakeQueueCacheTtlMs: INTAKE_QUEUE_CACHE_TTL_MS,
  aeWorkspaceCacheTtlMs: AE_WORKSPACE_CACHE_TTL_MS,
  managingWorkspaceCacheTtlMs: MANAGING_WORKSPACE_CACHE_TTL_MS,
  processCacheTtlMs: PROCESS_CACHE_TTL_MS,
  detailCacheTtlMs: DETAIL_CACHE_TTL_MS,
  invalidateProcessRowsCache,
  invalidateManuscriptDetailCache,
})

export const EditorApi = {
  ...financeApi,
  ...rbacApi,
  ...manuscriptsApi,
  ...decisionProductionApi,

  ...reviewerLibraryApi,

  ...internalCollaborationApi,
}
