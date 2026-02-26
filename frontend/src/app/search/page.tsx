import Link from 'next/link'
import { ArrowRight, ExternalLink, Search as SearchIcon } from 'lucide-react'

import SiteHeader from '@/components/layout/SiteHeader'
import { getBackendOrigin } from '@/lib/backend-origin'
import { demoJournals } from '@/lib/demo-journals'

type SearchMode = 'articles' | 'journals'
const SEARCH_REVALIDATE_SECONDS = 60

type SearchResultItem = {
  id: string
  title?: string | null
  slug?: string | null
  issn?: string | null
  description?: string | null
  abstract?: string | null
  journals?: {
    title?: string | null
  } | null
}

interface SearchPageProps {
  searchParams?: {
    q?: string | string[]
    mode?: string | string[]
  }
}

function pickFirst(value?: string | string[]): string {
  if (Array.isArray(value)) return value[0] || ''
  return value || ''
}

function normalizeMode(raw: string): SearchMode {
  return raw === 'journals' ? 'journals' : 'articles'
}

async function searchOnServer(query: string, mode: SearchMode): Promise<SearchResultItem[]> {
  if (!query) return []
  try {
    const origin = getBackendOrigin()
    const params = new URLSearchParams({ q: query, mode })
    const res = await fetch(`${origin}/api/v1/manuscripts/search?${params.toString()}`, {
      next: {
        revalidate: SEARCH_REVALIDATE_SECONDS,
        tags: ['search-results', `search:${mode}:${query.toLowerCase()}`],
      },
    })
    if (!res.ok) return []
    const payload = await res.json().catch(() => null)
    if (!payload?.success || !Array.isArray(payload?.results)) return []
    return payload.results as SearchResultItem[]
  } catch (error) {
    if (process.env.NODE_ENV !== 'production') {
      console.warn('Search failed on server:', error)
    }
    return []
  }
}

function renderResult(res: SearchResultItem, mode: SearchMode, kind: 'primary' | 'fallback') {
  const fallbackKey = `fallback:${kind}:${res.id}`
  const href = mode === 'journals' ? `/journals/${res.slug || ''}` : `/articles/${res.id}`
  const meta = mode === 'journals' ? (res.issn || 'Journal') : (res.journals?.title || 'Scientific Report')
  const subtitle = mode === 'journals' ? res.description : res.abstract

  return (
    <Link
      href={href}
      key={fallbackKey}
      className="group block bg-card p-8 rounded-3xl border border-border/60 hover:border-primary hover:shadow-2xl transition-all"
    >
      <div className="flex justify-between items-center gap-6">
        <div className="min-w-0">
          <div className="text-xs font-bold text-primary uppercase tracking-widest mb-2">
            {meta}
          </div>
          <h3 className="text-2xl font-bold text-foreground group-hover:text-primary transition-colors mb-2 leading-snug">
            {res.title || 'Untitled'}
          </h3>
          <p className="text-muted-foreground line-clamp-2">{subtitle || 'No summary available.'}</p>
        </div>
        <ArrowRight className="h-6 w-6 text-muted-foreground group-hover:text-primary group-hover:translate-x-2 transition-all shrink-0" />
      </div>
    </Link>
  )
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const query = pickFirst(searchParams?.q).trim()
  const currentMode = normalizeMode(pickFirst(searchParams?.mode))
  const results = await searchOnServer(query, currentMode)
  const fallback =
    query && results.length === 0 && currentMode === 'journals'
      ? demoJournals.filter((journal) => {
          const keyword = query.toLowerCase()
          return (
            journal.title.toLowerCase().includes(keyword) ||
            journal.slug.toLowerCase().includes(keyword) ||
            (journal.issn || '').toLowerCase().includes(keyword)
          )
        })
      : []

  return (
    <div className="min-h-screen bg-muted/40 flex flex-col">
      <SiteHeader />

      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-12">
        <header className="mb-12 border-b border-border pb-8">
          <h1 className="text-3xl font-serif font-bold text-foreground flex items-center gap-4">
            <SearchIcon className="h-8 w-8 text-primary" />
            {query ? <>Search Results for &quot;{query}&quot;</> : <>Search</>}
          </h1>
          <p className="mt-2 text-muted-foreground font-medium">
            {query ? `Showing top results in ${currentMode}` : '请输入关键词后回车搜索（例如：title / DOI）'}
          </p>
        </header>

        {!query ? (
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
            {results.map((item) => renderResult(item, currentMode, 'primary'))}

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
                      <p className="text-sm font-bold text-foreground">Sample journals</p>
                      <Link href="/dashboard" className="text-sm font-bold text-primary hover:underline inline-flex items-center gap-1">
                        Dashboard <ExternalLink className="h-4 w-4" />
                      </Link>
                    </div>
                    {fallback.slice(0, 10).map((item) => renderResult(item, currentMode, 'fallback'))}
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
