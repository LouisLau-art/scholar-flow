import type { Session } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'

const STORAGE_KEY = 'scholarflow:access_token'
const SUPABASE_STORAGE_KEY = 'sb-mmvulyrfsorqdpdrzbkd-auth-token'

const cacheToken = (token?: string | null) => {
  if (typeof window === 'undefined') return
  if (token) {
    localStorage.setItem(STORAGE_KEY, token)
  } else {
    localStorage.removeItem(STORAGE_KEY)
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

export const authService = {
  async getSession(): Promise<Session | null> {
    const { data } = await supabase.auth.getSession()
    cacheToken(data.session?.access_token)
    return data.session ?? null
  },
  async getAccessToken(): Promise<string | null> {
    const local = readAccessTokenFromLocalStorage()
    if (local) return local

    const session = await authService.getSession()
    return session?.access_token ?? null
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
  },
  onAuthStateChange(handler: (session: Session | null) => void) {
    return supabase.auth.onAuthStateChange((_event, session) => {
      cacheToken(session?.access_token)
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
