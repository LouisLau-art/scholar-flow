'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import Link from 'next/link'
import { Loader2, Search as SearchIcon, ArrowRight, ExternalLink } from 'lucide-react'
import { demoJournals } from '@/lib/demo-journals'
import { authService } from '@/services/auth'

export default function SearchPage() {
  const searchParams = useSearchParams()
  const query = searchParams.get('q')
  const mode = searchParams.get('mode')
  const [results, setResults] = useState<any[]>([])
  const [fallback, setFallback] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function doSearch() {
      setIsLoading(true)
      setResults([])
      setFallback([])
      try {
        const currentMode = mode || 'articles'
        const res = await fetch(
          `/api/v1/manuscripts/search?q=${encodeURIComponent(query || '')}&mode=${currentMode}`,
        )
        const data = await res.json()
        if (data.success) setResults(data.results || [])

        // 搜索为空时，给出对用户“有用”的可见内容，避免页面看起来像坏掉。
        if ((data.results || []).length === 0) {
          if (currentMode === 'journals') {
            const q = (query || '').trim().toLowerCase()
            const demo = demoJournals.filter((j) => {
              if (!q) return true
              return (
                j.title.toLowerCase().includes(q) ||
                j.slug.toLowerCase().includes(q) ||
                (j.issn || '').toLowerCase().includes(q)
              )
            })
            setFallback(demo)
          } else {
            const token = await authService.getAccessToken()
            if (token) {
              const mine = await fetch('/api/v1/manuscripts/mine', {
                headers: { Authorization: `Bearer ${token}` },
              }).then((r) => r.json())

              if (mine?.success && Array.isArray(mine.data)) {
                const q = (query || '').trim().toLowerCase()
                const filtered = mine.data.filter((m: any) => {
                  if (!q) return true
                  return (
                    String(m.title || '').toLowerCase().includes(q) ||
                    String(m.abstract || '').toLowerCase().includes(q)
                  )
                })
                setFallback(filtered)
              }
            }
          }
        }
      } catch (err) {
        console.error('Search failed:', err)
      } finally {
        setIsLoading(false)
      }
    }
    if (query) doSearch()
  }, [query, mode])

  const currentMode = mode || 'articles'

  const renderResult = (res: any, kind: 'primary' | 'fallback') => {
    const href = currentMode === 'journals' ? `/journals/${res.slug}` : `/articles/${res.id}`
    const meta = currentMode === 'journals' ? (res.issn || 'Journal') : (res.journals?.title || 'Scientific Report')
    const subtitle = currentMode === 'journals' ? res.description : res.abstract

    return (
      <Link
        href={href}
        key={`${kind}:${res.id}`}
        className="group block bg-white p-8 rounded-3xl border border-slate-100 hover:border-blue-500 hover:shadow-2xl transition-all"
      >
        <div className="flex justify-between items-center gap-6">
          <div className="min-w-0">
            <div className="text-xs font-bold text-blue-600 uppercase tracking-widest mb-2">
              {meta}
            </div>
            <h3 className="text-2xl font-bold text-slate-900 group-hover:text-blue-600 transition-colors mb-2 leading-snug">
              {res.title}
            </h3>
            <p className="text-slate-500 line-clamp-2">{subtitle}</p>
          </div>
          <ArrowRight className="h-6 w-6 text-slate-300 group-hover:text-blue-600 group-hover:translate-x-2 transition-all shrink-0" />
        </div>
      </Link>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SiteHeader />
      
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-12">
        <header className="mb-12 border-b border-slate-200 pb-8">
          <h1 className="text-3xl font-serif font-bold text-slate-900 flex items-center gap-4">
            <SearchIcon className="h-8 w-8 text-blue-600" />
            Search Results for "{query}"
          </h1>
          <p className="mt-2 text-slate-500 font-medium">Showing top results in {currentMode}</p>
        </header>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-40">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
            <p className="text-slate-400 font-medium tracking-widest uppercase text-xs">Aggregating Global Research...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {results.map((r: any) => renderResult(r, 'primary'))}

            {results.length === 0 && (
              <div className="bg-white rounded-3xl border border-slate-100 p-10 space-y-6">
                <div className="text-center">
                  <p className="text-slate-700 font-semibold text-lg">No results found</p>
                  <p className="text-slate-500 text-sm mt-2">
                    {currentMode === 'articles'
                      ? 'Tip: public search only shows published articles.'
                      : 'Tip: journal data may not be initialized in this environment.'}
                  </p>
                </div>

                {fallback.length > 0 && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-bold text-slate-900">
                        {currentMode === 'articles' ? 'Your submissions (unpublished)' : 'Sample journals'}
                      </p>
                      <Link href="/dashboard" className="text-sm font-bold text-blue-600 hover:underline inline-flex items-center gap-1">
                        Dashboard <ExternalLink className="h-4 w-4" />
                      </Link>
                    </div>
                    {fallback.slice(0, 10).map((r: any) => renderResult(r, 'fallback'))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
