'use client'

import { useState, useEffect, type FormEvent } from 'react'
import { FileText, Send, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

export default function ReviewerPage({ params }: { params: { token: string } }) {
  /**
   * 审稿人免登录落地页
   * 遵循章程：衬线体标题，slate-900 风格，优雅降级
   */
  const [isLoading, setIsLoading] = useState(true)
  const [manuscript, setManuscript] = useState<any>(null)
  const [reviewReport, setReviewReport] = useState<any>(null)
  const [score, setScore] = useState(5)
  const [commentsToAuthor, setCommentsToAuthor] = useState('')
  const [confidentialComments, setConfidentialComments] = useState('')
  const [attachment, setAttachment] = useState<File | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    const loadData = async () => {
      try {
        const res = await fetch(`/api/v1/reviews/token/${params.token}`)
        const json = await res.json()
        if (!res.ok || !json?.success) {
          toast.error(json?.detail || json?.message || 'Failed to load review task.')
          return
        }
        setReviewReport(json.data.review_report)
        setManuscript(json.data.manuscript)
      } catch (e) {
        toast.error('Failed to load review task.')
      } finally {
        setIsLoading(false)
      }
    }
    loadData()
  }, [params.token])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!commentsToAuthor.trim()) {
      toast.error('Comments to author is required.')
      return
    }
    if (score < 1 || score > 5) {
      toast.error('Score must be 1-5.')
      return
    }

    setIsSubmitting(true)
    const toastId = toast.loading('Submitting review...')
    try {
      const fd = new FormData()
      fd.set('content', commentsToAuthor)
      fd.set('score', String(score))
      if (confidentialComments.trim()) fd.set('confidential_comments_to_editor', confidentialComments)
      if (attachment) fd.set('attachment', attachment)

      const res = await fetch(`/api/v1/reviews/token/${params.token}/submit`, {
        method: 'POST',
        body: fd,
      })
      const json = await res.json().catch(() => null)
      if (!res.ok || !json?.success) {
        toast.error(json?.detail || json?.message || 'Submission failed.', { id: toastId })
        return
      }
      toast.success('Review submitted. Thank you!', { id: toastId })
      setCommentsToAuthor('')
      setConfidentialComments('')
      setAttachment(null)
    } catch (err) {
      toast.error('Submission failed.', { id: toastId })
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <Loader2 className="h-10 w-10 animate-spin text-slate-900" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-12 border-b border-slate-200 pb-6">
          <h1 className="font-serif text-4xl font-bold text-slate-900">
            Review Manuscript
          </h1>
          <p className="mt-2 text-slate-600">Secure, no-login access via token.</p>
          {manuscript?.title && (
            <p className="mt-4 text-sm text-slate-500">
              <span className="font-semibold text-slate-700">Title:</span> {manuscript.title}
            </p>
          )}
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* PDF 预览占位区域 (T023) */}
          <div className="lg:col-span-2 rounded-lg bg-white p-4 shadow-sm ring-1 ring-slate-200 h-[800px] flex items-center justify-center border-2 border-dashed border-slate-200">
            <div className="text-center">
              <FileText className="mx-auto h-12 w-12 text-slate-300" />
              <p className="mt-4 text-slate-500 font-medium">PDF Preview Component Loading...</p>
            </div>
          </div>

          {/* 评审表单 */}
          <aside className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-slate-200 h-fit">
            <h2 className="text-lg font-semibold text-slate-900 mb-6">Your Evaluation</h2>
            <form className="space-y-6" onSubmit={handleSubmit}>
              <div>
                <label className="block text-sm font-semibold text-slate-900">Score (1-5)</label>
                <select
                  value={String(score)}
                  onChange={(e) => setScore(Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-500"
                >
                  <option value="5">5 - Excellent</option>
                  <option value="4">4 - Good</option>
                  <option value="3">3 - Average</option>
                  <option value="2">2 - Poor</option>
                  <option value="1">1 - Terrible</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-900">Comments to Author (required)</label>
                <textarea
                  rows={8}
                  value={commentsToAuthor}
                  onChange={(e) => setCommentsToAuthor(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-900">
                  Confidential Comments to Editor (optional)
                </label>
                <p className="mt-1 text-xs text-slate-500">
                  This section is confidential and will not be shown to the author.
                </p>
                <textarea
                  rows={5}
                  value={confidentialComments}
                  onChange={(e) => setConfidentialComments(e.target.value)}
                  className="mt-2 w-full rounded-md border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-900">Confidential Attachment (optional)</label>
                <p className="mt-1 text-xs text-slate-500">
                  Upload an annotated PDF or supporting file. Editors only.
                </p>
                <input
                  type="file"
                  onChange={(e) => setAttachment(e.target.files?.[0] ?? null)}
                  className="mt-2 block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-slate-800 hover:file:bg-slate-200"
                />
              </div>

              <button
                disabled={isSubmitting}
                className="w-full flex items-center justify-center gap-2 rounded-md bg-slate-900 py-3 text-white hover:bg-slate-800 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <Send className="h-4 w-4" /> {isSubmitting ? 'Submitting...' : 'Submit Report'}
              </button>
            </form>
          </aside>
        </div>
      </div>
    </div>
  )
}
