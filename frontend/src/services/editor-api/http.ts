import { authService } from '@/services/auth'
import type { CachedGetOptions } from './types'

type JsonCacheEntry = {
  expiresAt: number
  data: unknown
}

type CreateAuthedGetJsonCachedDeps = {
  authedFetch: (input: RequestInfo, init?: RequestInit) => Promise<Response>
  getJsonCache: Map<string, JsonCacheEntry>
  getJsonInflight: Map<string, Promise<unknown>>
  defaultTtlMs: number
}

export async function authedFetch(input: RequestInfo, init?: RequestInit) {
  const token = await authService.getAccessToken()
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (token) headers.Authorization = `Bearer ${token}`
  return fetch(input, { ...init, headers })
}

export function createAuthedGetJsonCached(deps: CreateAuthedGetJsonCachedDeps) {
  const { authedFetch, getJsonCache, getJsonInflight, defaultTtlMs } = deps

  return async function authedGetJsonCached<T = any>(url: string, options: CachedGetOptions = {}): Promise<T> {
    const ttlMs = options.ttlMs ?? defaultTtlMs
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
}

export function getFilenameFromContentDisposition(contentDisposition: string | null) {
  if (!contentDisposition) return 'finance_invoices.csv'
  const m = /filename="?([^"]+)"?/i.exec(contentDisposition)
  return m?.[1] || 'finance_invoices.csv'
}
