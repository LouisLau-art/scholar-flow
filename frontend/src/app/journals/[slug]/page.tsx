'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import Link from 'next/link'
import { Star, BookOpen, FileText, ArrowRight, Loader2 } from 'lucide-react'

export default function JournalPage() {
  const params = useParams()
  const slugParam = (params as Record<string, string | string[]> | null)?.slug
  const slug = Array.isArray(slugParam) ? slugParam[0] : (slugParam || '')
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
      <div className="min-h-screen bg-card flex flex-col">
        <SiteHeader />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
        </div>
      </div>
    )
  }

  if (!data?.journal) return <div>Journal not found.</div>

  const { journal, articles } = data

  return (
    <div className="min-h-screen bg-card flex flex-col">
      <SiteHeader />
      
      {/* Journal Hero */}
      <section className="bg-foreground text-white py-24 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10 bg-grid-slate pointer-events-none" />
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 bg-primary/20 text-primary-foreground/80 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest mb-8 border border-primary/30">
              <Star className="h-3 w-3 fill-current" /> High Impact Factor: {journal.impact_factor}
            </div>
            <h1 className="text-5xl font-serif font-bold mb-6 leading-tight">{journal.title}</h1>
            <p className="text-xl text-muted-foreground leading-relaxed italic">{journal.description}</p>
            
            <div className="mt-12 flex gap-6">
              <Link href="/submit" className="bg-card text-foreground px-8 py-4 rounded-xl font-bold hover:bg-muted/40 transition-all shadow-xl">
                Submit to this Journal
              </Link>
              <div className="flex items-center gap-4 text-muted-foreground font-medium">
                <span className="flex items-center gap-2"><BookOpen className="h-5 w-5" /> ISSN: {journal.issn || '2345-6789'}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Published Articles List */}
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-20 lg:px-8">
        <div className="flex items-center justify-between mb-12 border-b border-border/60 pb-8">
          <h2 className="text-3xl font-serif font-bold text-foreground flex items-center gap-3">
            <FileText className="h-8 w-8 text-primary" />
            Latest Published Articles
          </h2>
          <span className="text-sm font-bold text-muted-foreground uppercase tracking-widest">{articles.length} Results</span>
        </div>

        <div className="space-y-8">
          {articles.map((art: any) => (
            <Link 
              key={art.id} 
              href={`/articles/${art.id}`}
              className="group block bg-card p-8 rounded-3xl border border-border/60 hover:border-primary hover:shadow-2xl transition-all duration-300"
            >
              <div className="flex justify-between items-start gap-8">
                <div className="flex-1">
                  <div className="flex items-center gap-3 text-xs font-bold text-muted-foreground uppercase tracking-widest mb-4">
                    <span>{new Date(art.published_at).toLocaleDateString()}</span>
                    <span className="w-1 h-1 bg-muted rounded-full" />
                    <span className="text-primary">DOI: {art.doi}</span>
                  </div>
                  <h3 className="text-2xl font-bold text-foreground group-hover:text-primary transition-colors mb-4 leading-snug">
                    {art.title}
                  </h3>
                  <p className="text-muted-foreground line-clamp-2 leading-relaxed">
                    {art.abstract}
                  </p>
                </div>
                <div className="bg-muted/40 p-4 rounded-2xl group-hover:bg-primary transition-colors hidden sm:block">
                  <ArrowRight className="h-6 w-6 text-muted-foreground group-hover:text-white" />
                </div>
              </div>
            </Link>
          ))}

          {articles.length === 0 && (
            <div className="py-20 text-center text-muted-foreground bg-muted/40 rounded-3xl border-2 border-dashed border-border">
              No articles published in this journal yet.
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
