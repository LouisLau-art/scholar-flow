'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import SiteHeader from '@/components/layout/SiteHeader'
import VersionHistory from '@/components/VersionHistory'
import { FileText, Download, Quote, Calendar, Hash, ExternalLink, Loader2, Clock3, Lock } from 'lucide-react'
import Link from 'next/link'
import { authService } from '@/services/auth'

const PRIVATE_PROGRESS_STEPS: Array<{ key: string; label: string }> = [
  { key: 'submitted', label: 'Submitted' },
  { key: 'pre_check', label: 'Pre-check' },
  { key: 'under_review', label: 'Under Review' },
  { key: 'revision_requested', label: 'Revision Requested' },
  { key: 'resubmitted', label: 'Resubmitted' },
  { key: 'decision', label: 'Decision' },
  { key: 'approved', label: 'Accepted' },
  { key: 'layout', label: 'Layout' },
  { key: 'english_editing', label: 'English Editing' },
  { key: 'proofreading', label: 'Proofreading' },
  { key: 'published', label: 'Published' },
]

function normalizeWorkflowStatus(rawStatus: unknown): string {
  const status = String(rawStatus || '').toLowerCase()
  if (['minor_revision', 'major_revision', 'revision_required', 'revision_requested', 'returned_for_revision'].includes(status)) {
    return 'revision_requested'
  }
  if (status === 'decision_done') return 'decision'
  if (status === 'return_for_revision') return 'revision_requested'
  return status || 'submitted'
}

function getStatusLabel(rawStatus: unknown): string {
  const status = normalizeWorkflowStatus(rawStatus)
  const found = PRIVATE_PROGRESS_STEPS.find((s) => s.key === status)
  if (found) return found.label
  if (status === 'rejected') return 'Rejected'
  return status ? status.replace(/_/g, ' ') : 'Unknown'
}

function formatDateTime(raw: unknown): string {
  if (!raw) return 'N/A'
  const date = new Date(String(raw))
  if (Number.isNaN(date.getTime())) return 'N/A'
  return date.toLocaleString()
}

async function fetchPublishedPreviewUrl(articleId: string): Promise<string | null> {
  try {
    const res = await fetch(
      `/api/v1/manuscripts/articles/${encodeURIComponent(articleId)}/pdf-signed`
    )
    const result = await res.json().catch(() => null)
    if (res.ok && result?.success && result?.data?.signed_url) {
      return String(result.data.signed_url)
    }
  } catch (e) {
    console.error('Failed to load signed PDF url:', e)
  }
  return null
}

function ErrorState({ title, message }: { title: string; message: string }) {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SiteHeader />
      <main className="flex-1 mx-auto max-w-4xl w-full px-4 py-16 sm:px-6 lg:px-8">
        <div className="bg-white rounded-3xl shadow-sm border border-slate-100 p-10">
          <h1 className="font-serif text-3xl font-bold text-slate-900">{title}</h1>
          <p className="mt-4 text-slate-600">{message}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/"
              className="rounded-full bg-blue-600 px-6 py-2.5 text-sm font-bold text-white shadow-lg shadow-blue-900/20 hover:bg-blue-500 transition-colors"
            >
              返回首页
            </Link>
            <Link
              href="/dashboard"
              className="rounded-full border border-slate-200 bg-white px-6 py-2.5 text-sm font-bold text-slate-900 hover:bg-slate-50 transition-colors"
            >
              前往 Dashboard
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}

export default function ArticleClient({ initialArticle }: { initialArticle?: any }) {
  const params = useParams()
  const routeIdRaw = initialArticle?.id || params?.id
  const articleId = String(Array.isArray(routeIdRaw) ? routeIdRaw[0] : routeIdRaw || '').trim()

  const [article, setArticle] = useState<any>(initialArticle || null)
  const [isLoading, setIsLoading] = useState(!initialArticle)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [citeCopied, setCiteCopied] = useState(false)
  const [roles, setRoles] = useState<string[] | null>(null)
  const [currentUserId, setCurrentUserId] = useState<string | null>(null)
  const [identityResolved, setIdentityResolved] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchUserAndRoles() {
      try {
        const session = await authService.getSession()
        const user = session?.user
        if (user) setCurrentUserId(user.id)

        const token = await authService.getAccessToken()
        if (!token) return
        const res = await fetch('/api/v1/user/profile', {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json().catch(() => null)
        if (data?.success) {
          setRoles(data?.data?.roles || null)
        }
      } catch (err) {
        console.error('Failed to load user info:', err)
      } finally {
        setIdentityResolved(true)
      }
    }
    fetchUserAndRoles()
  }, [])

  useEffect(() => {
    let cancelled = false

    async function fetchArticle() {
      setLoadError(null)
      if (!articleId) {
        setArticle(null)
        setIsLoading(false)
        setLoadError('Article not found.')
        return
      }

      if (initialArticle) {
        const isInitialPublished = initialArticle?.status === 'published' || Boolean(initialArticle?.published_at)
        const initialPath = initialArticle?.final_pdf_path || initialArticle?.file_path
        if (isInitialPublished && initialPath) {
          const signedUrl = await fetchPublishedPreviewUrl(String(initialArticle.id))
          if (!cancelled && signedUrl) setPreviewUrl(signedUrl)
        } else if (!cancelled) {
          setPreviewUrl(null)
        }
        setIsLoading(false)
        return
      }

      setIsLoading(true)
      setPreviewUrl(null)

      try {
        // 1) 先走公开已发表文章接口
        const publicRes = await fetch(`/api/v1/manuscripts/articles/${encodeURIComponent(articleId)}`)
        const publicJson = await publicRes.json().catch(() => null)
        if (publicRes.ok && publicJson?.success && publicJson?.data) {
          if (cancelled) return
          setArticle(publicJson.data)
          const signedUrl = await fetchPublishedPreviewUrl(String(publicJson.data?.id || articleId))
          if (!cancelled && signedUrl) setPreviewUrl(signedUrl)
          return
        }

        // 2) 非公开稿件：允许登录作者查看进度（受保护 by-id）
        const token = await authService.getAccessToken()
        if (!token) {
          if (cancelled) return
          setArticle(null)
          setLoadError('Article not found.')
          return
        }

        const ownRes = await fetch(`/api/v1/manuscripts/by-id/${encodeURIComponent(articleId)}`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const ownJson = await ownRes.json().catch(() => null)

        if (ownRes.ok && ownJson?.success && ownJson?.data) {
          if (cancelled) return
          setArticle(ownJson.data)
          return
        }

        if (cancelled) return
        setArticle(null)
        if (ownRes.status === 401) {
          setLoadError('请先登录后查看该稿件。')
        } else if (ownRes.status === 403) {
          setLoadError('未发表稿件仅作者本人可查看。')
        } else {
          setLoadError('Article not found.')
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Failed to load article:', err)
          setArticle(null)
          setLoadError('Failed to load article.')
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    fetchArticle()

    return () => {
      cancelled = true
    }
  }, [articleId, initialArticle]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleDownload(idForDownload: string) {
    try {
      const res = await fetch(`/api/v1/stats/download/${idForDownload}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!res.ok) {
        console.error('Failed to record download')
      }

      const pdfRes = await fetch(`/api/v1/manuscripts/articles/${encodeURIComponent(String(idForDownload))}/pdf-signed`)
      const pdfJson = await pdfRes.json().catch(() => null)
      const signedUrl = pdfJson?.data?.signed_url
      if (!pdfRes.ok || !signedUrl) {
        console.error('Failed to create download URL')
        return
      }
      window.open(String(signedUrl), '_blank')
    } catch (error) {
      console.error('Download error:', error)
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
      console.error('Failed to copy citation', error)
    }
  }

  function handleDownloadCitation(format: 'bib' | 'ris') {
    if (!article?.id) return
    const href = `/api/v1/manuscripts/articles/${encodeURIComponent(String(article.id))}/citation.${format}`
    window.open(href, '_blank')
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
      const data = await res.json().catch(() => null)
      if (data?.success) {
        setArticle(data.data)
      } else {
        console.error('Publish failed:', data)
      }
    } catch (err) {
      console.error('Publish error:', err)
    }
  }

  const isPublished = article?.status === 'published' || Boolean(article?.published_at)
  const waitingIdentityForPrivateArticle = Boolean(article && !isPublished && !identityResolved)

  if (isLoading || waitingIdentityForPrivateArticle) {
    return (
      <div className="min-h-screen bg-white flex flex-col">
        <SiteHeader />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
        </div>
      </div>
    )
  }

  if (!article) {
    return <ErrorState title="Article not found" message={loadError || '页面不存在，或该内容尚未发布。'} />
  }

  const hasFile = Boolean(article?.final_pdf_path || article?.file_path)
  const datasetUrl = article?.dataset_url
  const sourceCodeUrl = article?.source_code_url
  const datasetReady = Boolean(datasetUrl)
  const sourceCodeReady = Boolean(sourceCodeUrl)
  const canPublish = Boolean(roles?.includes('editor') || roles?.includes('admin'))
  const isAuthor = currentUserId === article.author_id
  const canViewHistory = isAuthor || canPublish || roles?.includes('reviewer')
  const normalizedStatus = normalizeWorkflowStatus(article?.status)
  const currentStepIndex = PRIVATE_PROGRESS_STEPS.findIndex((step) => step.key === normalizedStatus)
  const isRejected = normalizedStatus === 'rejected'
  const latestActivity = formatDateTime(article?.updated_at || article?.created_at)

  if (!isPublished) {
    if (!isAuthor) {
      return <ErrorState title="Access restricted" message="未发表稿件仅作者本人可查看进度信息。" />
    }

    return (
      <div className="min-h-screen bg-slate-50 flex flex-col">
        <SiteHeader />
        <main className="flex-1 mx-auto max-w-5xl w-full px-4 py-12 sm:px-6 lg:px-8">
          <section className="bg-white border border-slate-200 shadow-sm rounded-3xl p-8 sm:p-10">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-amber-700">
              <Lock className="h-3.5 w-3.5" />
              Private Manuscript View
            </div>
            <h1 className="mt-5 text-3xl font-serif font-bold text-slate-900 leading-tight">
              {article.title || 'Untitled Manuscript'}
            </h1>
            <p className="mt-3 text-slate-600">
              该稿件尚未发表。作者侧仅展示流程进度与最近动态，不展示全文、下载与引用信息。
            </p>

            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Current Stage</div>
                <div className="mt-2 text-base font-semibold text-slate-900">{getStatusLabel(article?.status)}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Latest Activity</div>
                <div className="mt-2 flex items-center gap-2 text-sm text-slate-900">
                  <Clock3 className="h-4 w-4 text-slate-500" />
                  <span>{latestActivity}</span>
                </div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Submission ID</div>
                <div className="mt-2 truncate font-mono text-sm text-slate-800">{String(article?.id || '')}</div>
              </div>
            </div>

            <div className="mt-8">
              <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">Workflow Progress</h2>
              <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {PRIVATE_PROGRESS_STEPS.map((step, index) => {
                  const done = !isRejected && currentStepIndex >= 0 && index < currentStepIndex
                  const active = !isRejected && index === currentStepIndex
                  return (
                    <div
                      key={step.key}
                      className={[
                        'rounded-xl border px-3 py-2 text-sm font-medium',
                        done ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : '',
                        active ? 'border-blue-200 bg-blue-50 text-blue-800' : '',
                        !done && !active ? 'border-slate-200 bg-white text-slate-500' : '',
                      ].join(' ').trim()}
                    >
                      {step.label}
                    </div>
                  )
                })}
              </div>
              {isRejected ? (
                <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700">
                  Current stage: Rejected
                </div>
              ) : null}
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/dashboard"
                className="rounded-full bg-blue-600 px-6 py-2.5 text-sm font-bold text-white shadow-lg shadow-blue-900/20 hover:bg-blue-500 transition-colors"
              >
                返回 Dashboard
              </Link>
              {normalizedStatus === 'revision_requested' ? (
                <Link
                  href={`/submit-revision/${encodeURIComponent(String(article.id))}`}
                  className="rounded-full border border-slate-200 bg-white px-6 py-2.5 text-sm font-bold text-slate-900 hover:bg-slate-50 transition-colors"
                >
                  提交修订稿
                </Link>
              ) : null}
            </div>
          </section>
        </main>
      </div>
    )
  }

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
                      {hasFile ? 'Preview not available. Use Download PDF.' : 'No PDF uploaded for this article.'}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* Version History (Authorized Only) */}
          {canViewHistory && (
            <section className="space-y-4">
              <h2 className="text-xl font-bold text-slate-900">Version History</h2>
              <VersionHistory manuscriptId={article.id} />
            </section>
          )}
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
            <div className="mt-3 grid grid-cols-2 gap-2">
              <button
                onClick={() => handleDownloadCitation('bib')}
                className="py-2 border border-slate-700 rounded-xl text-xs font-bold hover:bg-slate-800 transition-all"
              >
                BibTeX
              </button>
              <button
                onClick={() => handleDownloadCitation('ris')}
                className="py-2 border border-slate-700 rounded-xl text-xs font-bold hover:bg-slate-800 transition-all"
              >
                RIS
              </button>
            </div>
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
