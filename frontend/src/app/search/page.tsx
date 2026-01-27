'use client'

import { useSearchParams } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import { Loader2, Search as SearchIcon, FileText } from 'lucide-react'

export default function SearchPage() {
  const searchParams = useSearchParams()
  const query = searchParams.get('q')
  const mode = searchParams.get('mode')

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

        {/* 模拟结果列表 */}
        <div className="space-y-8">
          <div className="bg-white p-8 rounded-2xl shadow-sm ring-1 ring-slate-200 animate-pulse">
            <div className="h-6 w-3/4 bg-slate-100 rounded mb-4" />
            <div className="h-4 w-full bg-slate-50 rounded mb-2" />
            <div className="h-4 w-5/6 bg-slate-50 rounded" />
          </div>
          
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <Loader2 className="h-12 w-12 animate-spin mb-4 text-blue-200" />
            <p className="text-lg font-medium">Aggregating research from 200+ journals...</p>
          </div>
        </div>
      </main>
    </div>
  )
}
