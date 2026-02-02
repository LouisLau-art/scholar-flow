'use client'

import { useEffect } from 'react'
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

export default function AuthCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    let cancelled = false

    async function run() {
      const next = searchParams.get('next') || '/dashboard'
      const code = searchParams.get('code')

      try {
        // 1) PKCE flow: ?code=...
        if (code) {
          const { error } = await supabase.auth.exchangeCodeForSession(code)
          if (error) throw error
        } else if (typeof window !== 'undefined' && window.location.hash) {
          // 2) Implicit flow fallback: #access_token=...&refresh_token=...
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
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="rounded-2xl bg-white border border-slate-200 shadow-sm p-8 text-center max-w-md w-full">
        <div className="font-serif text-2xl font-bold text-slate-900">Signing you in…</div>
        <p className="mt-2 text-sm text-slate-500">正在完成登录回调与会话建立，请稍候。</p>
      </div>
    </div>
  )
}

