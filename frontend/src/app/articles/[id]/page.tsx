'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import { FileText, Download, Quote, Calendar, Hash, ExternalLink, Loader2 } from 'lucide-react'

export default function ArticleDetailPage() {
  const { id } = useParams()
  const [article, setArticle] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function fetchArticle() {
      try {
        const res = await fetch(`/api/v1/manuscripts/articles/${id}`)
        const result = await res.json()
        if (result.success) setArticle(result.data)
      } catch (err) {
        console.error('Failed to load article:', err)
      } finally {
        setIsLoading(false)
      }
    }
    fetchArticle()
  }, [id])

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

  if (!article) return <div>Article not found.</div>

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SiteHeader />
      
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-12 lg:grid lg:grid-cols-3 lg:gap-12">
        
        {/* Main Content (Left 2 Columns) */}
        <div className="lg:col-span-2 space-y-12">
          {/* Header Area */}
          <header className="space-y-6">
            <nav className="flex items-center gap-2 text-sm font-bold text-blue-600 uppercase tracking-widest">
              <Link href={`/journals/${article.journals?.slug}`} className="hover:underline">
                {article.journals?.title}
              </Link>
              <span className="text-slate-300">/</span>
              <span className="text-slate-400">Article</span>
            </nav>
            <h1 className="text-4xl font-serif font-bold text-slate-900 leading-tight">
              {article.title}
            </h1>
            <div className="flex flex-wrap gap-4 text-slate-600 font-medium">
              <span className="flex items-center gap-1.5"><Calendar className="h-4 w-4" /> Published: {new Date(article.published_at).toLocaleDateString()}</span>
              <span className="flex items-center gap-1.5"><Hash className="h-4 w-4" /> DOI: {article.doi || 'Pending'}</span>
            </div>
          </header>

          {/* Abstract Section */}
          <section className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm">
            <h2 className="text-xl font-bold text-slate-900 mb-4 border-b border-slate-100 pb-2">Abstract</h2>
            <p className="text-slate-600 leading-relaxed text-lg italic">
              {article.abstract}
            </p>
          </section>

          {/* PDF Preview Area */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-slate-900">Full Text Preview</h2>
              <button className="flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-full text-sm font-bold hover:bg-slate-800 transition-all">
                <Download className="h-4 w-4" /> Download PDF
              </button>
            </div>
            <div className="aspect-[3/4] w-full bg-slate-200 rounded-3xl overflow-hidden border-4 border-white shadow-2xl relative group">
              {/* 这里使用 Iframe 模拟 PDF 预览，实际接入 Supabase 签名链接 */}
              <div className="absolute inset-0 flex items-center justify-center bg-slate-100">
                <div className="text-center">
                  <FileText className="h-16 w-16 text-slate-300 mx-auto mb-4" />
                  <p className="text-slate-400 font-medium">Secure PDF Viewer Loading...</p>
                </div>
              </div>
              <iframe 
                src="https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf" 
                className="w-full h-full border-0 relative z-10 opacity-90 group-hover:opacity-100 transition-opacity"
              />
            </div>
          </section>
        </div>

        {/* Sidebar (Right 1 Column) */}
        <aside className="mt-12 lg:mt-0 space-y-8">
          {/* Article Metrics */}
          <div className="bg-slate-900 text-white p-8 rounded-3xl shadow-xl">
            <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-6">Metrics</h3>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <div className="text-2xl font-mono font-bold">1.2K</div>
                <div className="text-xs text-slate-400 font-bold uppercase">Views</div>
              </div>
              <div>
                <div className="text-2xl font-mono font-bold">450</div>
                <div className="text-xs text-slate-400 font-bold uppercase">Downloads</div>
              </div>
            </div>
            <button className="w-full mt-8 py-3 border border-slate-700 rounded-xl text-sm font-bold flex items-center justify-center gap-2 hover:bg-slate-800 transition-all">
              <Quote className="h-4 w-4" /> Cite this Article
            </button>
          </div>

          {/* Quick Links */}
          <div className="space-y-4">
            <h3 className="font-bold text-slate-900 px-2">Related Resources</h3>
            <div className="space-y-2">
              <div className="p-4 bg-white rounded-2xl border border-slate-200 hover:border-blue-500 cursor-pointer transition-all group">
                <div className="text-xs font-bold text-blue-600 mb-1">DATASET</div>
                <div className="text-sm font-bold text-slate-900 group-hover:text-blue-600 flex items-center justify-between">
                  Open Research Data <ExternalLink className="h-3 w-3" />
                </div>
              </div>
              <div className="p-4 bg-white rounded-2xl border border-slate-200 hover:border-blue-500 cursor-pointer transition-all group">
                <div className="text-xs font-bold text-emerald-600 mb-1">SOURCE CODE</div>
                <div className="text-sm font-bold text-slate-900 group-hover:text-blue-600 flex items-center justify-between">
                  Algorithm Implementation <ExternalLink className="h-3 w-3" />
                </div>
              </div>
            </div>
          </div>
        </aside>

      </main>
    </div>
  )
}

import Link from 'next/link'
