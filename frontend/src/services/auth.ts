import type { Session } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'

const STORAGE_KEY = 'scholarflow:access_token'
const SESSION_CACHE_TTL_MS = 10_000
const SUPABASE_STORAGE_KEY = (() => {
  const raw = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
  try {
    const ref = new URL(raw).hostname.split('.')[0]
    if (ref) return `sb-${ref}-auth-token`
  } catch {
    // ignore
  }
  return 'sb-mmvulyrfsorqdpdrzbkd-auth-token'
})()

let sessionCache: { value: Session | null; expiresAt: number } | null = null
let inflightSessionRequest: Promise<Session | null> | null = null

const cacheToken = (token?: string | null) => {
  if (typeof window === 'undefined') return
  if (token) {
    localStorage.setItem(STORAGE_KEY, token)
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}

function cacheSession(session: Session | null): void {
  sessionCache = {
    value: session,
    expiresAt: Date.now() + SESSION_CACHE_TTL_MS,
  }
}

function readAccessTokenFromLocalStorage(): string | null {
  if (typeof window === 'undefined') return null

  const cached = window.localStorage.getItem(STORAGE_KEY)
  if (cached) return cached

  // 中文注释：E2E / 部分环境下 supabase-js 的 getSession 可能触发网络刷新并导致卡住。
  // 这里优先从 Supabase 自己的 localStorage session 里取 access_token，避免阻塞页面加载。
  const raw = window.localStorage.getItem(SUPABASE_STORAGE_KEY)
  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) as { access_token?: string | null } | null
    const token = parsed?.access_token ?? null
    if (token) cacheToken(token)
    return token
  } catch {
    return null
  }
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  if (typeof window === 'undefined') return null
  const parts = token.split('.')
  if (parts.length < 2) return null
  try {
    const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = b64 + '='.repeat((4 - (b64.length % 4)) % 4)
    const json = window.atob(padded)
    return JSON.parse(json) as Record<string, unknown>
  } catch {
    return null
  }
}

function isLikelyExpired(token: string, skewSeconds = 60): boolean {
  const payload = decodeJwtPayload(token)
  const exp = Number(payload?.exp || 0)
  if (!exp) return false
  const now = Math.floor(Date.now() / 1000)
  return exp <= now + skewSeconds
}

export const authService = {
  async getSession(): Promise<Session | null> {
    const cached = sessionCache
    if (cached && cached.expiresAt > Date.now()) return cached.value
    if (inflightSessionRequest) return inflightSessionRequest

    inflightSessionRequest = (async () => {
      const { data } = await supabase.auth.getSession()
      const token = data.session?.access_token
      if (token && !isLikelyExpired(token)) {
        cacheToken(token)
        cacheSession(data.session ?? null)
        return data.session ?? null
      }

      const refreshed = await supabase.auth.refreshSession().catch(() => null)
      const refreshedSession = refreshed?.data?.session ?? null
      const finalSession = refreshedSession ?? data.session ?? null
      cacheToken(finalSession?.access_token ?? null)
      cacheSession(finalSession)
      return finalSession
    })()

    try {
      return await inflightSessionRequest
    } finally {
      inflightSessionRequest = null
    }
  },
  async getAccessToken(): Promise<string | null> {
    const local = readAccessTokenFromLocalStorage()
    if (local && !isLikelyExpired(local)) return local

    if (local && isLikelyExpired(local)) {
      const refreshed = await authService.forceRefreshAccessToken()
      if (refreshed) return refreshed
    }

    const session = await authService.getSession()
    return session?.access_token ?? null
  },
  async forceRefreshAccessToken(): Promise<string | null> {
    const refreshed = await supabase.auth.refreshSession().catch(() => null)
    const refreshedSession = refreshed?.data?.session ?? null
    const token = refreshedSession?.access_token ?? null
    cacheToken(token)
    cacheSession(refreshedSession)
    return token
  },
  async getUserProfile(): Promise<any> {
    const token = await authService.getAccessToken()
    if (!token) return null
    const res = await fetch('/api/v1/user/profile', {
      headers: { Authorization: `Bearer ${token}` },
    })
    const result = await res.json()
    return result.success ? result.data : null
  },
  async signOut(): Promise<void> {
    await supabase.auth.signOut()
    cacheToken(null)
    sessionCache = null
    inflightSessionRequest = null
  },
  onAuthStateChange(handler: (session: Session | null) => void) {
    return supabase.auth.onAuthStateChange((_event, session) => {
      cacheToken(session?.access_token)
      cacheSession(session ?? null)
      handler(session)
    })
  },
  async verifyMagicLink(token: string): Promise<{
    reviewer_id: string
    manuscript_id: string
    assignment_id: string
    expires_at: string
  } | null> {
    const res = await fetch('/api/v1/auth/magic-link/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
    const json = await res.json().catch(() => null)
    if (!res.ok || !json?.success || !json?.data?.assignment_id) return null
    return json.data
  },
}
