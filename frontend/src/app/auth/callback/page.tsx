'use client'

import { Suspense, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { toast } from 'sonner'

function parseHashParams(hash: string): Record<string, string> {
  const raw = hash.startsWith('#') ? hash.slice(1) : hash
  const params = new URLSearchParams(raw)
  const out: Record<string, string> = {}
  params.forEach((v, k) => {
    out[k] = v
  })
  return out
}

function AuthCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    let cancelled = false

    async function run() {
      const next = searchParams?.get('next') || '/dashboard'
      const code = searchParams?.get('code')
      const accessToken = searchParams?.get('access_token')
      const refreshToken = searchParams?.get('refresh_token')

      try {
        // 1) PKCE flow: ?code=...
        if (code) {
          const { error } = await supabase.auth.exchangeCodeForSession(code)
          if (error) throw error
        } else if (accessToken && refreshToken) {
          // 1.5) Dev login / direct session: ?access_token=...&refresh_token=...
          const { error } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          })
          if (error) throw error
        } else if (typeof window !== 'undefined' && window.location.hash) {
          // 2) Implicit flow fallback: fragment access_token=...&refresh_token=...
          const h = parseHashParams(window.location.hash)
          if (h.access_token && h.refresh_token) {
            const { error } = await supabase.auth.setSession({
              access_token: h.access_token,
              refresh_token: h.refresh_token,
            })
            if (error) throw error
          }
        }

        // 3) 验证是否已建立 session（避免“打开了但 session 仍为 null”）
        const { data } = await supabase.auth.getSession()
        if (!data.session) {
          throw new Error('Session is still null after callback')
        }

        if (cancelled) return
        router.replace(next)
        router.refresh()
      } catch (e: any) {
        console.error('[AuthCallback] failed:', e)
        toast.error('登录回调失败，请重试或重新发送登录邮件。')
        if (cancelled) return
        router.replace('/login')
      }
    }

    run()
    return () => {
      cancelled = true
    }
  }, [router, searchParams])

  return (
    <div className="min-h-screen bg-muted/40 flex items-center justify-center p-6">
      <div className="rounded-2xl bg-card border border-border shadow-sm p-8 text-center max-w-md w-full">
        <div className="font-serif text-2xl font-bold text-foreground">Signing you in…</div>
        <p className="mt-2 text-sm text-muted-foreground">正在完成登录回调与会话建立，请稍候。</p>
      </div>
    </div>
  )
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-muted/40 flex items-center justify-center p-6">
          <div className="rounded-2xl bg-card border border-border shadow-sm p-8 text-center max-w-md w-full">
            <div className="font-serif text-2xl font-bold text-foreground">Signing you in…</div>
            <p className="mt-2 text-sm text-muted-foreground">正在加载登录回调页面…</p>
          </div>
        </div>
      }
    >
      <AuthCallbackContent />
    </Suspense>
  )
}
