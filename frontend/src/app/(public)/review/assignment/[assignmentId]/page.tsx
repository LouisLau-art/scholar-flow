'use client'

import { useEffect, useState, type FormEvent } from 'react'
import { Loader2, Send } from 'lucide-react'
import { toast } from 'sonner'
import { FileUpload } from '@/components/FileUpload'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

function ReviewForm({
  assignmentId,
  manuscriptId,
  onSubmitted,
}: {
  assignmentId: string
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

      const res = await fetch(`/api/v1/reviews/magic/assignments/${encodeURIComponent(assignmentId)}/submit`, {
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
    } catch {
      toast.error('Submission failed.', { id: toastId })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <aside className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-slate-200 h-fit">
      <h2 className="text-lg font-semibold text-slate-900 mb-6">Your Evaluation</h2>
      <form
        className="space-y-6"
        onSubmit={handleSubmit}
        data-manuscript-id={manuscriptId}
      >
        <div>
          <label htmlFor="review_score" className="block text-sm font-semibold text-slate-900">
            Score (1-5)
          </label>
          <Select value={String(score)} onValueChange={(value) => setScore(Number(value))}>
            <SelectTrigger id="review_score" className="mt-1 w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="5">5 - Excellent</SelectItem>
              <SelectItem value="4">4 - Good</SelectItem>
              <SelectItem value="3">3 - Average</SelectItem>
              <SelectItem value="2">2 - Poor</SelectItem>
              <SelectItem value="1">1 - Terrible</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <label htmlFor="comments_for_author" className="block text-sm font-semibold text-slate-900">
            Comments for the Authors
          </label>
          <textarea
            id="comments_for_author"
            rows={8}
            value={commentsToAuthor}
            onChange={(e) => setCommentsToAuthor(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label htmlFor="confidential_comments_to_editor" className="block text-sm font-semibold text-slate-900">
            Confidential Comments to the Editor (optional)
          </label>
          <p className="mt-1 text-xs font-semibold text-red-600">Authors will NOT see this</p>
          <textarea
            id="confidential_comments_to_editor"
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

export default function ReviewAssignmentPage({ params }: { params: { assignmentId: string } }) {
  const assignmentId = params.assignmentId

  const [isLoading, setIsLoading] = useState(true)
  const [manuscript, setManuscript] = useState<any>(null)
  const [reviewReport, setReviewReport] = useState<any>(null)
  const [latestRevision, setLatestRevision] = useState<any>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [attachmentUrl, setAttachmentUrl] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const loadData = async () => {
      setPdfUrl(null)
      setAttachmentUrl(null)
      try {
        const [taskRes, pdfRes, attRes] = await Promise.all([
          fetch(`/api/v1/reviews/magic/assignments/${encodeURIComponent(assignmentId)}`),
          fetch(`/api/v1/reviews/magic/assignments/${encodeURIComponent(assignmentId)}/pdf-signed`),
          fetch(`/api/v1/reviews/magic/assignments/${encodeURIComponent(assignmentId)}/attachment-signed`),
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
          setPdfUrl(String(pdfJson.data.signed_url))
        }

        const attJson = await attRes.json().catch(() => null)
        if (attRes.ok && attJson?.success && attJson?.data?.signed_url) {
          setAttachmentUrl(String(attJson.data.signed_url))
        }
      } catch {
        toast.error('Failed to load review task.')
      } finally {
        setIsLoading(false)
      }
    }
    loadData()
  }, [assignmentId, reloadKey])

  const manuscriptId = String(manuscript?.id || '')

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
        <header className="mb-6 border-b border-slate-200 pb-5">
          <h1 className="font-serif text-4xl font-bold text-slate-900">Review Manuscript</h1>
          <p className="mt-2 text-slate-600">Secure, no-login access via magic link.</p>
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
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-700">Author Response</div>
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
                <p className="mt-1 text-sm text-slate-500">Only you and Editors can access this file.</p>
              </div>
              <button
                onClick={() => window.open(attachmentUrl, '_blank')}
                className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-900 hover:bg-slate-50"
              >
                Download
              </button>
            </div>
          </section>
        ) : null}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <section className="lg:col-span-2 rounded-lg bg-white shadow-sm ring-1 ring-slate-200">
            <div className="border-b border-slate-200 px-6 py-4">
              <h2 className="text-lg font-semibold text-slate-900">Manuscript PDF</h2>
            </div>
            <div className="p-2">
              {pdfUrl ? (
                <div className="w-full rounded-md border border-slate-200 bg-slate-50 h-[calc(100vh-260px)] min-h-[800px]">
                  <iframe title="PDF Preview" src={pdfUrl} className="h-full w-full rounded-md" />
                </div>
              ) : (
                <div className="flex h-[400px] items-center justify-center text-sm text-slate-500">
                  PDF preview is not available.
                </div>
              )}
            </div>
          </section>

          <ReviewForm
            key={manuscriptId || assignmentId}
            assignmentId={assignmentId}
            manuscriptId={manuscriptId}
            onSubmitted={() => setReloadKey((v) => v + 1)}
          />
        </div>

        {reviewReport?.status === 'completed' ? (
          <div className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
            Your review has been submitted. You can revisit this page anytime using the same link.
          </div>
        ) : null}
      </div>
    </div>
  )
}
