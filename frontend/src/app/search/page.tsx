import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import Link from 'next/link'
import { Loader2, Search as SearchIcon, FileText, ArrowRight } from 'lucide-react'

export default function SearchPage() {
  const searchParams = useSearchParams()
  const query = searchParams.get('q')
  const mode = searchParams.get('mode')
  const [results, setResults] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function doSearch() {
      setIsLoading(true)
      try {
        const res = await fetch(`/api/v1/manuscripts/search?q=${encodeURIComponent(query || '')}&mode=${mode || 'articles'}`)
        const data = await res.json()
        if (data.success) setResults(data.results)
      } catch (err) {
        console.error('Search failed:', err)
      } finally {
        setIsLoading(false)
      }
    }
    if (query) doSearch()
  }, [query, mode])

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SiteHeader />
      
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-12">
        <header className="mb-12 border-b border-slate-200 pb-8">
          <h1 className="text-3xl font-serif font-bold text-slate-900 flex items-center gap-4">
            <SearchIcon className="h-8 w-8 text-blue-600" />
            Search Results for "{query}"
          </h1>
          <p className="mt-2 text-slate-500 font-medium">Showing top results in {mode || 'articles'}</p>
        </header>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-40">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
            <p className="text-slate-400 font-medium tracking-widest uppercase text-xs">Aggregating Global Research...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {results.map((res: any) => (
              <Link 
                href={mode === 'journals' ? `/journals/${res.slug}` : `/articles/${res.id}`}
                key={res.id} 
                className="group block bg-white p-8 rounded-3xl border border-slate-100 hover:border-blue-500 hover:shadow-2xl transition-all"
              >
                <div className="flex justify-between items-center">
                  <div>
                    <div className="text-xs font-bold text-blue-600 uppercase tracking-widest mb-2">
                      {res.journals?.title || res.issn || 'Scientific Report'}
                    </div>
                    <h3 className="text-2xl font-bold text-slate-900 group-hover:text-blue-600 transition-colors mb-2 leading-snug">
                      {res.title}
                    </h3>
                    <p className="text-slate-500 line-clamp-2">{res.abstract || res.description}</p>
                  </div>
                  <ArrowRight className="h-6 w-6 text-slate-300 group-hover:text-blue-600 group-hover:translate-x-2 transition-all" />
                </div>
              </Link>
            ))}

            {results.length === 0 && (
              <div className="text-center py-40 bg-white rounded-3xl border border-slate-100">
                <p className="text-slate-400 text-lg">No results found for your query. Try different keywords.</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
