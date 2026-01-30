'use client'

import { useState } from 'react'
import { Search, ArrowRight, FileText, BookOpen } from 'lucide-react'
import { useRouter } from 'next/navigation'

export default function HeroSection() {
  const [searchMode, setSearchMode] = useState<'articles' | 'journals'>('articles')
  const [query, setQuery] = useState('')
  const router = useRouter()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    router.push(`/search?mode=${searchMode}&q=${encodeURIComponent(query)}`)
  }

  return (
    <section className="relative overflow-hidden bg-slate-900 py-24 sm:py-32 lg:pb-40">
      {/* 背景纹理 (Dot Pattern) */}
      <div className="absolute inset-0 opacity-10 bg-grid-slate pointer-events-none" />
      
      {/* 装饰性渐变 */}
      <div className="absolute top-0 right-0 -translate-y-12 translate-x-12 blur-3xl opacity-30">
        <div className="aspect-[1000/600] w-[60rem] bg-gradient-to-r from-blue-500 to-purple-600 rounded-full" />
      </div>

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
        <h1 className="font-serif text-5xl font-bold tracking-tight text-white sm:text-7xl mb-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
          Publish Your Research <br />
          <span className="text-blue-500">Open to the World</span>
        </h1>
        <p className="mx-auto max-w-2xl text-lg leading-8 text-slate-300 mb-12 animate-in fade-in slide-in-from-bottom-6 duration-700 delay-150">
          Accelerating scientific discovery through AI-powered peer review and global open access. 
          The next generation platform for scholars and publishers.
        </p>

        {/* Search Box ( discovery Core) */}
        <div className="mx-auto max-w-3xl animate-in fade-in slide-in-from-bottom-8 duration-700 delay-300">
          <div className="bg-white rounded-2xl shadow-2xl p-2 sm:p-3 overflow-hidden">
            {/* Mode Switcher */}
            <div className="flex gap-4 px-4 py-2 border-b border-slate-100 mb-2">
              <button 
                onClick={() => setSearchMode('articles')}
                className={`flex items-center gap-2 text-sm font-bold pb-2 transition-colors border-b-2 ${
                  searchMode === 'articles' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-600'
                }`}
              >
                <FileText className="h-4 w-4" /> Articles
              </button>
              <button 
                onClick={() => setSearchMode('journals')}
                className={`flex items-center gap-2 text-sm font-bold pb-2 transition-colors border-b-2 ${
                  searchMode === 'journals' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-600'
                }`}
              >
                <BookOpen className="h-4 w-4" /> Journals
              </button>
            </div>

            {/* Input Area */}
            <form onSubmit={handleSearch} className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input 
                  type="text"
                  placeholder={searchMode === 'articles' ? "Search by title, DOI, or author..." : "Search journals by field or title..."}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 text-slate-900 bg-white border-0 focus:ring-0 focus:outline-none text-lg placeholder:text-slate-400"
                />
              </div>
              <button 
                type="submit"
                className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-4 rounded-xl font-bold transition-all flex items-center gap-2 shrink-0"
              >
                Search <ArrowRight className="h-5 w-5" />
              </button>
            </form>
          </div>
          
          {/* Quick Stats / Trending */}
          <div className="mt-6 flex flex-wrap justify-center gap-6 text-sm text-slate-400">
            <span className="flex items-center gap-2">Trending: <span className="text-blue-400 hover:underline cursor-pointer">AI Ethics</span></span>
            <span className="flex items-center gap-2">Impact Factor: <span className="text-white font-mono">8.42</span></span>
            <span className="flex items-center gap-2 text-white font-semibold">2.4M+ Citations</span>
          </div>
        </div>
      </div>
    </section>
  )
}
