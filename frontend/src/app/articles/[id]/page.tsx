'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import { FileText, Download, Quote, Calendar, Hash, ExternalLink, Loader2 } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import Link from 'next/link'
import { authService } from '@/services/auth'

export default function ArticleDetailPage() {
  const { id } = useParams()
  const [article, setArticle] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [citeCopied, setCiteCopied] = useState(false)
  const [roles, setRoles] = useState<string[] | null>(null)

  useEffect(() => {
    async function fetchArticle() {
      try {
        const res = await fetch(`/api/v1/manuscripts/articles/${id}`)
        const result = await res.json()
        if (result.success) {
          setArticle(result.data)
          if (result.data?.file_path) {
            const { data, error } = await supabase.storage
              .from('manuscripts')
              .createSignedUrl(result.data.file_path, 60 * 5)
            if (!error) {
              setPreviewUrl(data?.signedUrl ?? null)
            }
          }
        }
      } catch (err) {
        console.error('Failed to load article:', err)
      } finally {
        setIsLoading(false)
      }
    }
    async function fetchRoles() {
      try {
        const token = await authService.getAccessToken()
        if (!token) return
        const res = await fetch('/api/v1/user/profile', {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        if (data?.success) {
          setRoles(data?.data?.roles || null)
        }
      } catch (err) {
        console.error('Failed to load roles:', err)
      }
    }
    fetchArticle()
    fetchRoles()
  }, [id])

  async function handleDownload(articleId: string) {
    try {
      if (!article?.file_path) {
        console.error("No file attached to this article")
        return
      }
      // 调用下载统计API
      const res = await fetch(`/api/v1/stats/download/${articleId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });
      
      if (!res.ok) {
        console.error("Failed to record download");
      }

      const { data, error } = await supabase.storage
        .from('manuscripts')
        .createSignedUrl(article.file_path, 60 * 5)
      if (error || !data?.signedUrl) {
        console.error("Failed to create download URL");
        return
      }
      window.open(data.signedUrl, "_blank");
    } catch (error) {
      console.error("Download error:", error);
    }
  }

  async function handleCopyCitation() {
    if (!article) return
    const citation = `${article.title}. ${article.journals?.title || 'Unassigned Journal'}. ${article.published_at ? new Date(article.published_at).getFullYear() : 'Pending'}. DOI: ${article.doi || 'Pending'}.`
    try {
      await navigator.clipboard.writeText(citation)
      setCiteCopied(true)
      setTimeout(() => setCiteCopied(false), 2000)
    } catch (error) {
      console.error("Failed to copy citation", error)
    }
  }

  async function handlePublish() {
    try {
      const token = await authService.getAccessToken()
      if (!token) return
      const res = await fetch('/api/v1/editor/publish', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ manuscript_id: article.id }),
      })
      const data = await res.json()
      if (data?.success) {
        setArticle(data.data)
      } else {
        console.error('Publish failed:', data)
      }
    } catch (err) {
      console.error('Publish error:', err)
    }
  }

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

  const hasFile = Boolean(article?.file_path)
  const datasetUrl = article?.dataset_url
  const sourceCodeUrl = article?.source_code_url
  const datasetReady = Boolean(datasetUrl)
  const sourceCodeReady = Boolean(sourceCodeUrl)
  const canPublish = Boolean(roles?.includes('editor') || roles?.includes('admin'))
  const isPublished = article?.status === 'published' || Boolean(article?.published_at)

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SiteHeader />
      
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-12 lg:grid lg:grid-cols-3 lg:gap-12">
        
        {/* Main Content (Left 2 Columns) */}
        <div className="lg:col-span-2 space-y-12">
          {/* Header Area */}
          <header className="space-y-6">
            <nav className="flex items-center gap-2 text-sm font-bold text-blue-600 uppercase tracking-widest">
              {article.journals?.slug ? (
                <Link href={`/journals/${article.journals.slug}`} className="hover:underline">
                  {article.journals.title}
                </Link>
              ) : (
                <span className="text-slate-400">Unassigned Journal</span>
              )}
              <span className="text-slate-300">/</span>
              <span className="text-slate-400">Article</span>
            </nav>
            <h1 className="text-4xl font-serif font-bold text-slate-900 leading-tight">
              {article.title}
            </h1>
            <div className="flex flex-wrap gap-4 text-slate-600 font-medium">
              <span className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4" />
                Published: {article.published_at ? new Date(article.published_at).toLocaleDateString() : 'Pending'}
              </span>
              <span className="flex items-center gap-1.5"><Hash className="h-4 w-4" /> DOI: {article.doi || 'Pending'}</span>
            </div>
            {canPublish && !isPublished && (
              <div>
                <button
                  onClick={handlePublish}
                  className="inline-flex items-center gap-2 rounded-full bg-blue-600 px-5 py-2 text-sm font-bold text-white hover:bg-blue-700 transition-colors"
                >
                  Publish (dev)
                </button>
              </div>
            )}
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
              <button
                onClick={() => handleDownload(article.id)}
                disabled={!hasFile}
                className="flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-full text-sm font-bold hover:bg-slate-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Download className="h-4 w-4" /> Download PDF
              </button>
            </div>
            <div className="aspect-[3/4] w-full bg-slate-200 rounded-3xl overflow-hidden border-4 border-white shadow-2xl relative">
              {previewUrl ? (
                <iframe
                  src={previewUrl}
                  className="w-full h-full border-0"
                  title="PDF Preview"
                />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center bg-slate-100">
                  <div className="text-center">
                    <FileText className="h-16 w-16 text-slate-300 mx-auto mb-4" />
                    <p className="text-slate-400 font-medium">
                      {hasFile ? "Preview not available. Use Download PDF." : "No PDF uploaded for this article."}
                    </p>
                  </div>
                </div>
              )}
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
            <button
              onClick={handleCopyCitation}
              className="w-full mt-8 py-3 border border-slate-700 rounded-xl text-sm font-bold flex items-center justify-center gap-2 hover:bg-slate-800 transition-all"
            >
              <Quote className="h-4 w-4" /> {citeCopied ? 'Citation Copied' : 'Cite this Article'}
            </button>
          </div>

          {/* Quick Links */}
          <div className="space-y-4">
            <h3 className="font-bold text-slate-900 px-2">Related Resources</h3>
            <div className="space-y-2">
              {datasetReady ? (
                <a
                  href={datasetUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="block w-full p-4 bg-white rounded-2xl border border-slate-200 transition-all group hover:border-blue-200"
                >
                  <div className="text-xs font-bold text-blue-600 mb-1">DATASET</div>
                  <div className="text-sm font-bold text-slate-900 group-hover:text-blue-600 flex items-center justify-between">
                    Open Research Data <ExternalLink className="h-3 w-3" />
                  </div>
                </a>
              ) : (
                <div className="p-4 bg-white rounded-2xl border border-slate-200 opacity-60 cursor-not-allowed transition-all group">
                  <div className="text-xs font-bold text-blue-600 mb-1">DATASET</div>
                  <div className="text-sm font-bold text-slate-900 flex items-center justify-between">
                    Open Research Data <ExternalLink className="h-3 w-3" />
                  </div>
                </div>
              )}
              {sourceCodeReady ? (
                <a
                  href={sourceCodeUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="block w-full p-4 bg-white rounded-2xl border border-slate-200 transition-all group hover:border-emerald-200"
                >
                  <div className="text-xs font-bold text-emerald-600 mb-1">SOURCE CODE</div>
                  <div className="text-sm font-bold text-slate-900 group-hover:text-emerald-600 flex items-center justify-between">
                    Algorithm Implementation <ExternalLink className="h-3 w-3" />
                  </div>
                </a>
              ) : (
                <div className="p-4 bg-white rounded-2xl border border-slate-200 opacity-60 cursor-not-allowed transition-all group">
                  <div className="text-xs font-bold text-emerald-600 mb-1">SOURCE CODE</div>
                  <div className="text-sm font-bold text-slate-900 flex items-center justify-between">
                    Algorithm Implementation <ExternalLink className="h-3 w-3" />
                  </div>
                </div>
              )}
            </div>
          </div>
        </aside>

      </main>
    </div>
  )
}
