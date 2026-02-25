'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import Link from 'next/link'
import { Loader2, Search as SearchIcon, ArrowRight, ExternalLink } from 'lucide-react'
import { demoJournals } from '@/lib/demo-journals'
import { authService } from '@/services/auth'

function SearchContent() {
  const searchParams = useSearchParams()
  const query = searchParams?.get('q')
  const mode = searchParams?.get('mode')
  const [results, setResults] = useState<any[]>([])
  const [fallback, setFallback] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    async function doSearch() {
      setIsLoading(true)
      setResults([])
      setFallback([])
      try {
        const q = (query || '').trim()
        if (!q) return
        const currentMode = mode || 'articles'
        const res = await fetch(
          `/api/v1/manuscripts/search?q=${encodeURIComponent(q)}&mode=${currentMode}`,
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
    const q = (query || '').trim()
    if (!q) {
      setIsLoading(false)
      setResults([])
      setFallback([])
      return
    }
    doSearch()
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
        className="group block bg-card p-8 rounded-3xl border border-border/60 hover:border-primary hover:shadow-2xl transition-all"
      >
        <div className="flex justify-between items-center gap-6">
          <div className="min-w-0">
            <div className="text-xs font-bold text-primary uppercase tracking-widest mb-2">
              {meta}
            </div>
            <h3 className="text-2xl font-bold text-foreground group-hover:text-primary transition-colors mb-2 leading-snug">
              {res.title}
            </h3>
            <p className="text-muted-foreground line-clamp-2">{subtitle}</p>
          </div>
          <ArrowRight className="h-6 w-6 text-muted-foreground group-hover:text-primary group-hover:translate-x-2 transition-all shrink-0" />
        </div>
      </Link>
    )
  }

  return (
    <div className="min-h-screen bg-muted/40 flex flex-col">
      <SiteHeader />
      
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-12">
        <header className="mb-12 border-b border-border pb-8">
          <h1 className="text-3xl font-serif font-bold text-foreground flex items-center gap-4">
            <SearchIcon className="h-8 w-8 text-primary" />
            {((query || '').trim() ? (
              <>Search Results for &quot;{query}&quot;</>
            ) : (
              <>Search</>
            ))}
          </h1>
          <p className="mt-2 text-muted-foreground font-medium">
            {((query || '').trim()
              ? `Showing top results in ${currentMode}`
              : '请输入关键词后回车搜索（例如：title / DOI）')}
          </p>
        </header>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-40">
            <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
            <p className="text-muted-foreground font-medium tracking-widest uppercase text-xs">Aggregating Global Research...</p>
          </div>
        ) : !((query || '').trim()) ? (
          <div className="bg-card rounded-3xl border border-border/60 p-10">
            <div className="max-w-xl space-y-4">
              <p className="text-foreground font-semibold">快速开始</p>
              <p className="text-sm text-muted-foreground">
                点击右上角搜索按钮，或在地址栏使用 <span className="font-mono">/search?q=关键词</span>。
              </p>
              <div className="flex flex-wrap gap-2 text-sm">
                <Link href="/search?q=doi" className="px-3 py-1 rounded-full bg-muted hover:bg-muted/70">doi</Link>
                <Link href="/search?q=energy" className="px-3 py-1 rounded-full bg-muted hover:bg-muted/70">energy</Link>
                <Link href="/search?q=review" className="px-3 py-1 rounded-full bg-muted hover:bg-muted/70">review</Link>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {results.map((r: any) => renderResult(r, 'primary'))}

            {results.length === 0 && (
              <div className="bg-card rounded-3xl border border-border/60 p-10 space-y-6">
                <div className="text-center">
                  <p className="text-foreground font-semibold text-lg">No results found</p>
                  <p className="text-muted-foreground text-sm mt-2">
                    {currentMode === 'articles'
                      ? 'Tip: public search only shows published articles.'
                      : 'Tip: journal data may not be initialized in this environment.'}
                  </p>
                </div>

                {fallback.length > 0 && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-bold text-foreground">
                        {currentMode === 'articles' ? 'Your submissions (unpublished)' : 'Sample journals'}
                      </p>
                      <Link href="/dashboard" className="text-sm font-bold text-primary hover:underline inline-flex items-center gap-1">
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

export default function SearchPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-muted/40 flex items-center justify-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    }>
      <SearchContent />
    </Suspense>
  )
}
