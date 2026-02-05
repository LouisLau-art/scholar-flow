'use client'

import SiteHeader from '@/components/layout/SiteHeader'
import { HomeBanner } from '@/components/portal/HomeBanner'
import { ArticleList } from '@/components/portal/ArticleList'
import { getLatestArticles, PublicArticle } from '@/services/portal'
import { useQuery } from '@tanstack/react-query'
import { FileText, Settings, ShieldCheck, DollarSign, ChevronRight, BookOpen, Users, Globe } from 'lucide-react'
import Link from 'next/link'

export default function HomePage() {
  const { data: articles = [], isLoading } = useQuery({
    queryKey: ['latest-articles'],
    queryFn: () => getLatestArticles(6),
  })

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <SiteHeader />
      
      <main className="flex-1">
        <HomeBanner />
        
        {/* Quick Access Dashboard Tiles */}
        <div className="relative -mt-12 z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Link href="/submit" className="flex items-center justify-between p-6 bg-blue-600 text-white rounded-2xl shadow-xl hover:bg-blue-700 transition-all group">
              <div className="flex items-center gap-4">
                <FileText className="h-6 w-6" />
                <span className="font-bold">Submit Paper</span>
              </div>
              <ChevronRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            
            <Link href="/dashboard" className="flex items-center justify-between p-6 bg-white border border-slate-200 text-slate-900 rounded-2xl shadow-xl hover:border-blue-500 transition-all group">
              <div className="flex items-center gap-4">
                <Users className="h-6 w-6 text-slate-400" />
                <span className="font-bold">My Dashboard</span>
              </div>
              <ChevronRight className="h-5 w-5 text-slate-300 group-hover:translate-x-1 transition-transform" />
            </Link>

            <Link href="/journal/guidelines" className="flex items-center justify-between p-6 bg-white border border-slate-200 text-slate-900 rounded-2xl shadow-xl hover:border-green-500 transition-all group">
              <div className="flex items-center gap-4">
                <BookOpen className="h-6 w-6 text-slate-400" />
                <span className="font-bold">Guidelines</span>
              </div>
              <ChevronRight className="h-5 w-5 text-slate-300 group-hover:translate-x-1 transition-transform" />
            </Link>

            <Link href="/about" className="flex items-center justify-between p-6 bg-white border border-slate-200 text-slate-900 rounded-2xl shadow-xl hover:border-purple-500 transition-all group">
              <div className="flex items-center gap-4">
                <Globe className="h-6 w-6 text-slate-400" />
                <span className="font-bold">About Journal</span>
              </div>
              <ChevronRight className="h-5 w-5 text-slate-300 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>

        {/* Latest Articles Section */}
        <section className="py-24 bg-slate-50">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between mb-12">
              <div>
                <h2 className="text-3xl font-serif font-bold text-slate-900 mb-2">Latest Articles</h2>
                <p className="text-slate-500">Discover the most recent peer-reviewed research published in our journal.</p>
              </div>
              <Link href="/search?status=published" className="text-blue-600 font-bold hover:underline">
                View All Articles →
              </Link>
            </div>

            {isLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-pulse">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-64 bg-slate-200 rounded-xl" />
                ))}
              </div>
            ) : (
              <ArticleList articles={articles} />
            )}
          </div>
        </section>

        {/* Branding Footer Section */}
        <section className="py-20 border-t border-slate-100 bg-white">
          <div className="mx-auto max-w-7xl px-4 text-center">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-[0.3em] mb-12">Indexed by Leading Databases</h3>
            <div className="flex flex-wrap justify-center gap-12 grayscale opacity-40">
              <div className="text-2xl font-serif font-black italic">SCOPUS</div>
              <div className="text-2xl font-serif font-black italic">WEB OF SCIENCE</div>
              <div className="text-2xl font-serif font-black italic">PUBMED</div>
              <div className="text-2xl font-serif font-black italic">DOAJ</div>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}