'use client'

import { useEffect, useState } from 'react'
import SiteHeader from '@/components/layout/SiteHeader'
import { authService } from '@/services/auth'
import { Loader2, MessageSquare } from 'lucide-react'

type ReviewFeedback = {
  id: string
  content?: string | null
  score?: number | null
  // 中文注释: 机密字段在 Author 视角下应不存在；即便存在也必须忽略渲染
  confidential_comments_to_editor?: string | null
  attachment_path?: string | null
}

export default function AuthorManuscriptReviewsPage({ params }: { params: { id: string } }) {
  const [isLoading, setIsLoading] = useState(true)
  const [items, setItems] = useState<ReviewFeedback[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const token = await authService.getAccessToken()
        if (!token) {
          setError('Please sign in again.')
          return
        }
        const res = await fetch(`/api/v1/reviews/feedback/${params.id}`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const json = await res.json().catch(() => null)
        if (!res.ok || !json?.success) {
          setError(json?.detail || json?.message || 'Failed to load review feedback.')
          return
        }
        setItems((json.data || []) as ReviewFeedback[])
      } catch (e) {
        setError('Failed to load review feedback.')
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [params.id])

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SiteHeader />
      <main className="flex-1 mx-auto max-w-5xl w-full px-4 py-10">
        <h1 className="text-2xl font-serif font-bold text-slate-900">Review Feedback</h1>
        <p className="mt-2 text-sm text-slate-500">
          Confidential reviewer comments and attachments are not shown to authors.
        </p>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-10 w-10 animate-spin text-slate-900" />
          </div>
        ) : error ? (
          <div className="mt-8 rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700 text-sm">
            {error}
          </div>
        ) : items.length === 0 ? (
          <div className="mt-8 rounded-xl border border-slate-200 bg-white p-8 text-slate-600 text-sm">
            No review feedback available yet.
          </div>
        ) : (
          <div className="mt-8 space-y-4">
            {items.map((r) => (
              <div key={r.id} className="rounded-xl border border-slate-200 bg-white p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-slate-900 font-semibold">
                    <MessageSquare className="h-4 w-4" />
                    Review
                  </div>
                  <div className="text-xs font-mono text-slate-400">score: {r.score ?? '—'}</div>
                </div>
                <div className="mt-4 text-slate-700 whitespace-pre-wrap">
                  {r.content || '—'}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

