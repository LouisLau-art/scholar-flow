'use client'

import { useState, useEffect, type FormEvent } from 'react'
import { FileText, Send, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { FileUpload } from '@/components/FileUpload'

function ReviewForm({
  token,
  manuscriptId,
  onSubmitted,
}: {
  token: string
  manuscriptId: string
  onSubmitted?: () => void
}) {
  const [score, setScore] = useState(5)
  const [commentsToAuthor, setCommentsToAuthor] = useState('')
  const [confidentialComments, setConfidentialComments] = useState('')
  const [attachment, setAttachment] = useState<File | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!commentsToAuthor.trim()) {
      toast.error('Comments for the Authors is required.')
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
      fd.set('comments_for_author', commentsToAuthor)
      fd.set('score', String(score))
      if (confidentialComments.trim()) fd.set('confidential_comments_to_editor', confidentialComments)
      if (attachment) fd.set('attachment', attachment)

      const res = await fetch(`/api/v1/reviews/token/${token}/submit`, {
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
      onSubmitted?.()
    } catch (err) {
      toast.error('Submission failed.', { id: toastId })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <aside className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-slate-200 h-fit">
      <h2 className="text-lg font-semibold text-slate-900 mb-6">Your Evaluation</h2>
      <form className="space-y-6" onSubmit={handleSubmit} data-manuscript-id={manuscriptId}>
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
          <label className="block text-sm font-semibold text-slate-900">Comments for the Authors</label>
          <textarea
            rows={8}
            value={commentsToAuthor}
            onChange={(e) => setCommentsToAuthor(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-slate-900">
            Confidential Comments to the Editor (optional)
          </label>
          <p className="mt-1 text-xs font-semibold text-red-600">Authors will NOT see this</p>
          <textarea
            rows={5}
            value={confidentialComments}
            onChange={(e) => setConfidentialComments(e.target.value)}
            className="mt-2 w-full rounded-md border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <FileUpload
          label="Upload Annotated PDF (Optional)"
          helperText="Only Editors and you (the Reviewer) can download this file."
          accept="application/pdf"
          disabled={isSubmitting}
          file={attachment}
          onFileSelected={setAttachment}
        />

        <button
          disabled={isSubmitting}
          className="w-full flex items-center justify-center gap-2 rounded-md bg-slate-900 py-3 text-white hover:bg-slate-800 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          <Send className="h-4 w-4" /> {isSubmitting ? 'Submitting...' : 'Submit Report'}
        </button>
      </form>
    </aside>
  )
}

export default function ReviewerPage({ params }: { params: { token: string } }) {
  /**
   * 审稿人免登录落地页
   * 遵循章程：衬线体标题，slate-900 风格，优雅降级
   */
  const [isLoading, setIsLoading] = useState(true)
  const [manuscript, setManuscript] = useState<any>(null)
  const [reviewReport, setReviewReport] = useState<any>(null)
  const [latestRevision, setLatestRevision] = useState<any>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [attachmentUrl, setAttachmentUrl] = useState<string | null>(null)
  const [attachmentLoading, setAttachmentLoading] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const loadData = async () => {
      setPdfUrl(null)
      setPdfLoading(true)
      setAttachmentUrl(null)
      try {
        const [taskRes, pdfRes] = await Promise.all([
          fetch(`/api/v1/reviews/token/${params.token}`),
          fetch(`/api/v1/reviews/token/${params.token}/pdf-signed`),
        ])

        const json = await taskRes.json().catch(() => null)
        if (!taskRes.ok || !json?.success) {
          toast.error(json?.detail || json?.message || 'Failed to load review task.')
          return
        }
        setReviewReport(json.data.review_report)
        setManuscript(json.data.manuscript)
        setLatestRevision(json.data.latest_revision || null)

        const pdfJson = await pdfRes.json().catch(() => null)
        if (pdfRes.ok && pdfJson?.success && pdfJson?.data?.signed_url) {
          setPdfUrl(pdfJson.data.signed_url)
        } else {
          setPdfUrl(null)
        }

        // 已提交且有附件时：允许 reviewer 通过 token 下载自己上传的机密附件（可选）
        try {
          setAttachmentLoading(true)
          const attRes = await fetch(`/api/v1/reviews/token/${params.token}/attachment-signed`)
          const attJson = await attRes.json().catch(() => null)
          if (attRes.ok && attJson?.success && attJson?.data?.signed_url) {
            setAttachmentUrl(String(attJson.data.signed_url))
          }
        } catch {
          // ignore
        } finally {
          setAttachmentLoading(false)
        }
      } catch (e) {
        toast.error('Failed to load review task.')
      } finally {
        setIsLoading(false)
        setPdfLoading(false)
      }
    }
    loadData()
  }, [params.token, reloadKey])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <Loader2 className="h-10 w-10 animate-spin text-slate-900" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 md:p-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 border-b border-slate-200 pb-6">
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

        {(latestRevision?.editor_comment || latestRevision?.response_letter) && (
          <section className="mb-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-slate-900">Revision Context</h2>
            <p className="mt-1 text-sm text-slate-500">
              If you are re-reviewing a revised manuscript, the editor request and author response are shown below.
            </p>

            {latestRevision?.editor_comment ? (
              <div className="mt-4 rounded-lg border border-amber-100 bg-amber-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-amber-800">
                  Editor Request{latestRevision?.decision_type ? ` (${String(latestRevision.decision_type)})` : ''}
                </div>
                <div className="mt-2 whitespace-pre-wrap text-sm text-slate-800">{latestRevision.editor_comment}</div>
              </div>
            ) : null}

            {latestRevision?.response_letter ? (
              <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-700">
                  Author Response
                </div>
                <div
                  className="mt-2 prose prose-sm max-w-none text-slate-700 prose-img:max-w-full prose-img:h-auto prose-img:rounded-md"
                  dangerouslySetInnerHTML={{ __html: String(latestRevision.response_letter) }}
                />
              </div>
            ) : null}
          </section>
        )}

        {attachmentUrl ? (
          <section className="mb-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Your Attachment</h2>
                <p className="mt-1 text-sm text-slate-500">
                  This is the annotated PDF you uploaded. Only you and Editors can access it.
                </p>
              </div>
              <button
                onClick={() => window.open(attachmentUrl, '_blank')}
                className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-900 hover:bg-slate-50"
                disabled={attachmentLoading}
              >
                Download
              </button>
            </div>
          </section>
        ) : null}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-9 rounded-lg bg-white p-3 md:p-4 shadow-sm ring-1 ring-slate-200 min-h-[70vh] lg:min-h-[860px] lg:h-[calc(100dvh-200px)] overflow-hidden">
            {pdfLoading ? (
              <div className="h-full flex items-center justify-center text-slate-500 font-medium">
                Loading preview...
              </div>
            ) : pdfUrl ? (
              <iframe src={pdfUrl} className="w-full h-full border-0" title="PDF Preview" />
            ) : (
              <div className="h-full flex items-center justify-center border-2 border-dashed border-slate-200 rounded-md">
                <div className="text-center p-8">
                  <FileText className="mx-auto h-12 w-12 text-slate-300" />
                  <p className="mt-4 text-slate-500 font-medium">No PDF available for preview.</p>
                </div>
              </div>
            )}
          </div>

          {/* ReviewForm 强制 key：切换稿件时彻底清空状态 */}
          {manuscript?.id ? (
            <div className="lg:col-span-3">
              <ReviewForm
                key={manuscript.id}
                token={params.token}
                manuscriptId={manuscript.id}
                onSubmitted={() => {
                  // 重新拉取，以刷新附件下载链接/状态
                  setReloadKey((k) => k + 1)
                }}
              />
            </div>
          ) : (
            <div className="lg:col-span-3">
              <ReviewForm
                key={params.token}
                token={params.token}
                manuscriptId={params.token}
                onSubmitted={() => {
                  setReloadKey((k) => k + 1)
                }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
