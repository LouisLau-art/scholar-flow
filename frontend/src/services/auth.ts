import type { Session } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'

const STORAGE_KEY = 'scholarflow:access_token'

const cacheToken = (token?: string | null) => {
  if (typeof window === 'undefined') return
  if (token) {
    localStorage.setItem(STORAGE_KEY, token)
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}

export const authService = {
  async getSession(): Promise<Session | null> {
    const { data } = await supabase.auth.getSession()
    cacheToken(data.session?.access_token)
    return data.session ?? null
  },
  async getAccessToken(): Promise<string | null> {
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
}
