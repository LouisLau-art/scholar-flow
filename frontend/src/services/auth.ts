import type { Session } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'

const SESSION_CACHE_TTL_MS = 10_000

let sessionCache: { value: Session | null; expiresAt: number } | null = null
let inflightSessionRequest: Promise<Session | null> | null = null

function cacheSession(session: Session | null): void {
  sessionCache = {
    value: session,
    expiresAt: Date.now() + SESSION_CACHE_TTL_MS,
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
        cacheSession(data.session ?? null)
        return data.session ?? null
      }

      const refreshed = await supabase.auth.refreshSession().catch(() => null)
      const refreshedSession = refreshed?.data?.session ?? null
      const finalSession = refreshedSession ?? data.session ?? null
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
    const session = await authService.getSession()
    return session?.access_token ?? null
  },
  async forceRefreshAccessToken(): Promise<string | null> {
    const refreshed = await supabase.auth.refreshSession().catch(() => null)
    const refreshedSession = refreshed?.data?.session ?? null
    const token = refreshedSession?.access_token ?? null
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
    sessionCache = null
    inflightSessionRequest = null
  },
  onAuthStateChange(handler: (session: Session | null) => void) {
    return supabase.auth.onAuthStateChange((_event, session) => {
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
