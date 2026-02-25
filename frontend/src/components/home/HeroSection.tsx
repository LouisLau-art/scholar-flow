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
    <section className="relative overflow-hidden bg-foreground py-24 sm:py-32 lg:pb-40">
      {/* 背景纹理 (Dot Pattern) */}
      <div className="absolute inset-0 opacity-10 bg-grid-neutral pointer-events-none" />
      
      {/* 装饰性渐变 */}
      <div className="absolute top-0 right-0 -translate-y-12 translate-x-12 blur-3xl opacity-30">
        <div className="aspect-[1000/600] sf-w-60rem bg-gradient-to-r from-primary/80 to-primary rounded-full" />
      </div>

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
        <h1 className="font-serif text-5xl font-bold tracking-tight text-primary-foreground sm:text-7xl mb-8 sf-motion-enter-up">
          Publish Your Research <br />
          <span className="text-primary">Open to the World</span>
        </h1>
        <p className="mx-auto max-w-2xl text-lg leading-8 text-primary-foreground/70 mb-12 sf-motion-enter-up-soft delay-150">
          Accelerating scientific discovery through AI-powered peer review and global open access. 
          The next generation platform for scholars and publishers.
        </p>

        {/* Search Box ( discovery Core) */}
        <div className="mx-auto max-w-3xl sf-motion-enter-up-strong delay-300">
          <div className="bg-card rounded-2xl shadow-2xl p-2 sm:p-3 overflow-hidden">
            {/* Mode Switcher */}
            <div className="flex gap-4 px-4 py-2 border-b border-border/60 mb-2">
              <button 
                onClick={() => setSearchMode('articles')}
                className={`flex items-center gap-2 text-sm font-bold pb-2 transition-colors border-b-2 ${
                  searchMode === 'articles' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                <FileText className="h-4 w-4" /> Articles
              </button>
              <button 
                onClick={() => setSearchMode('journals')}
                className={`flex items-center gap-2 text-sm font-bold pb-2 transition-colors border-b-2 ${
                  searchMode === 'journals' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                <BookOpen className="h-4 w-4" /> Journals
              </button>
            </div>

            {/* Input Area */}
            <form onSubmit={handleSearch} className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <input 
                  type="text"
                  placeholder={searchMode === 'articles' ? "Search by title, DOI, or author..." : "Search journals by field or title..."}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 text-foreground bg-background border-0 focus:ring-0 focus:outline-none text-lg placeholder:text-muted-foreground"
                />
              </div>
              <button 
                type="submit"
                className="bg-primary hover:bg-primary/90 text-primary-foreground px-8 py-4 rounded-xl font-bold transition-all flex items-center gap-2 shrink-0"
              >
                Search <ArrowRight className="h-5 w-5" />
              </button>
            </form>
          </div>
          
          {/* Quick Stats / Trending */}
          <div className="mt-6 flex flex-wrap justify-center gap-6 text-sm text-primary-foreground/70">
            <span className="flex items-center gap-2">Trending: <span className="text-primary hover:underline cursor-pointer">AI Ethics</span></span>
            <span className="flex items-center gap-2">Impact Factor: <span className="text-primary-foreground font-mono">8.42</span></span>
            <span className="flex items-center gap-2 text-primary-foreground font-semibold">2.4M+ Citations</span>
          </div>
        </div>
      </div>
    </section>
  )
}
