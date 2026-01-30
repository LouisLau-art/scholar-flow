'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import Link from 'next/link'
import { Star, BookOpen, FileText, ArrowRight, Loader2 } from 'lucide-react'

export default function JournalPage() {
  const { slug } = useParams()
  const [data, setData] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function fetchJournal() {
      try {
        const res = await fetch(`/api/v1/manuscripts/journals/${slug}`)
        const result = await res.json()
        if (result.success) setData(result)
      } catch (err) {
        console.error('Failed to load journal:', err)
      } finally {
        setIsLoading(false)
      }
    }
    fetchJournal()
  }, [slug])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-white flex flex-col">
        <SiteHeader />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
        </div>
      </div>
    )
  }

  if (!data?.journal) return <div>Journal not found.</div>

  const { journal, articles } = data

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <SiteHeader />
      
      {/* Journal Hero */}
      <section className="bg-slate-900 text-white py-24 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10 bg-grid-slate pointer-events-none" />
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 bg-blue-600/20 text-blue-400 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest mb-8 border border-blue-500/30">
              <Star className="h-3 w-3 fill-current" /> High Impact Factor: {journal.impact_factor}
            </div>
            <h1 className="text-5xl font-serif font-bold mb-6 leading-tight">{journal.title}</h1>
            <p className="text-xl text-slate-400 leading-relaxed italic">{journal.description}</p>
            
            <div className="mt-12 flex gap-6">
              <Link href="/submit" className="bg-white text-slate-900 px-8 py-4 rounded-xl font-bold hover:bg-slate-100 transition-all shadow-xl">
                Submit to this Journal
              </Link>
              <div className="flex items-center gap-4 text-slate-400 font-medium">
                <span className="flex items-center gap-2"><BookOpen className="h-5 w-5" /> ISSN: {journal.issn || '2345-6789'}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Published Articles List */}
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-20 lg:px-8">
        <div className="flex items-center justify-between mb-12 border-b border-slate-100 pb-8">
          <h2 className="text-3xl font-serif font-bold text-slate-900 flex items-center gap-3">
            <FileText className="h-8 w-8 text-blue-600" />
            Latest Published Articles
          </h2>
          <span className="text-sm font-bold text-slate-400 uppercase tracking-widest">{articles.length} Results</span>
        </div>

        <div className="space-y-8">
          {articles.map((art: any) => (
            <Link 
              key={art.id} 
              href={`/articles/${art.id}`}
              className="group block bg-white p-8 rounded-3xl border border-slate-100 hover:border-blue-500 hover:shadow-2xl transition-all duration-300"
            >
              <div className="flex justify-between items-start gap-8">
                <div className="flex-1">
                  <div className="flex items-center gap-3 text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">
                    <span>{new Date(art.published_at).toLocaleDateString()}</span>
                    <span className="w-1 h-1 bg-slate-300 rounded-full" />
                    <span className="text-blue-600">DOI: {art.doi}</span>
                  </div>
                  <h3 className="text-2xl font-bold text-slate-900 group-hover:text-blue-600 transition-colors mb-4 leading-snug">
                    {art.title}
                  </h3>
                  <p className="text-slate-500 line-clamp-2 leading-relaxed">
                    {art.abstract}
                  </p>
                </div>
                <div className="bg-slate-50 p-4 rounded-2xl group-hover:bg-blue-600 transition-colors hidden sm:block">
                  <ArrowRight className="h-6 w-6 text-slate-300 group-hover:text-white" />
                </div>
              </div>
            </Link>
          ))}

          {articles.length === 0 && (
            <div className="py-20 text-center text-slate-400 bg-slate-50 rounded-3xl border-2 border-dashed border-slate-200">
              No articles published in this journal yet.
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
