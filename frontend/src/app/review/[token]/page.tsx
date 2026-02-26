'use client'

import { useState, useEffect, useMemo, type FormEvent } from 'react'
import { FileText, Send, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { FileUpload } from '@/components/FileUpload'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { UI_COPY } from '@/lib/ui-copy'
import { sanitizeRichHtml } from '@/lib/sanitizeRichHtml'

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
    <aside className="rounded-lg bg-card p-6 shadow-sm ring-1 ring-border h-fit">
      <h2 className="text-lg font-semibold text-foreground mb-6">Your Evaluation</h2>
      <form className="space-y-6" onSubmit={handleSubmit} data-manuscript-id={manuscriptId}>
        <div>
          <label htmlFor="review-score" className="block text-sm font-semibold text-foreground">Score (1-5)</label>
          <Select value={String(score)} onValueChange={(value) => setScore(Number(value))}>
            <SelectTrigger id="review-score" className="mt-1 w-full">
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
          <label htmlFor="review-comments-to-author" className="block text-sm font-semibold text-foreground">Comments for the Authors</label>
          <Textarea
            id="review-comments-to-author"
            rows={8}
            value={commentsToAuthor}
            onChange={(e) => setCommentsToAuthor(e.target.value)}
            className="mt-1 border-border/80 px-4 py-2"
          />
        </div>

        <div>
          <label htmlFor="review-confidential-comments" className="block text-sm font-semibold text-foreground">
            Confidential Comments to the Editor (optional)
          </label>
          <p className="mt-1 text-xs font-semibold text-red-600">Authors will NOT see this</p>
          <Textarea
            id="review-confidential-comments"
            rows={5}
            value={confidentialComments}
            onChange={(e) => setConfidentialComments(e.target.value)}
            className="mt-2 border-border/80 px-4 py-2"
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

        <Button disabled={isSubmitting} className="w-full gap-2 py-3">
          <Send className="h-4 w-4" /> {isSubmitting ? UI_COPY.submitting : 'Submit Report'}
        </Button>
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
        const [taskRes, pdfRes, attRes] = await Promise.all([
          fetch(`/api/v1/reviews/token/${params.token}`),
          fetch(`/api/v1/reviews/token/${params.token}/pdf-signed`),
          fetch(`/api/v1/reviews/token/${params.token}/attachment-signed`),
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
        setAttachmentLoading(true)
        const attJson = await attRes.json().catch(() => null)
        if (attRes.ok && attJson?.success && attJson?.data?.signed_url) {
          setAttachmentUrl(String(attJson.data.signed_url))
        }
      } catch (e) {
        toast.error('Failed to load review task.')
      } finally {
        setIsLoading(false)
        setPdfLoading(false)
        setAttachmentLoading(false)
      }
    }
    loadData()
  }, [params.token, reloadKey])

  const sanitizedResponseLetter = useMemo(
    () => sanitizeRichHtml(String(latestRevision?.response_letter || '')),
    [latestRevision?.response_letter]
  )

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-muted/40">
        <Loader2 className="h-10 w-10 animate-spin text-foreground" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-muted/40 px-4 py-6 md:p-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 border-b border-border pb-6">
          <h1 className="font-serif text-4xl font-bold text-foreground">
            Review Manuscript
          </h1>
          <p className="mt-2 text-muted-foreground">Secure, no-login access via token.</p>
          {manuscript?.title && (
            <p className="mt-4 text-sm text-muted-foreground">
              <span className="font-semibold text-foreground">Title:</span> {manuscript.title}
            </p>
          )}
        </header>

        {(latestRevision?.editor_comment || latestRevision?.response_letter) && (
          <section className="mb-6 rounded-lg border border-border bg-card p-5 shadow-sm">
            <h2 className="text-base font-semibold text-foreground">Revision Context</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              If you are re-reviewing a revised manuscript, the editor request and author response are shown below.
            </p>

            {latestRevision?.editor_comment ? (
              <div className="mt-4 rounded-lg border border-amber-100 bg-amber-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-amber-800">
                  Editor Request{latestRevision?.decision_type ? ` (${String(latestRevision.decision_type)})` : ''}
                </div>
                <div className="mt-2 whitespace-pre-wrap text-sm text-foreground">{latestRevision.editor_comment}</div>
              </div>
            ) : null}

            {latestRevision?.response_letter ? (
              <div className="mt-4 rounded-lg border border-border bg-muted/40 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-foreground">
                  Author Response
                </div>
                <div
                  className="mt-2 prose prose-sm max-w-none text-foreground prose-img:max-w-full prose-img:h-auto prose-img:rounded-md"
                  dangerouslySetInnerHTML={{ __html: sanitizedResponseLetter }}
                />
              </div>
            ) : null}
          </section>
        )}

        {attachmentUrl ? (
          <section className="mb-6 rounded-lg border border-border bg-card p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-foreground">Your Attachment</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  This is the annotated PDF you uploaded. Only you and Editors can access it.
                </p>
              </div>
              <button
                onClick={() => window.open(attachmentUrl, '_blank')}
                className="rounded-md border border-border/80 bg-card px-3 py-2 text-sm font-semibold text-foreground hover:bg-muted/40"
                disabled={attachmentLoading}
              >
                Download
              </button>
            </div>
          </section>
        ) : null}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-9 rounded-lg bg-card p-3 md:p-4 shadow-sm ring-1 ring-border min-h-[70vh] lg:min-h-[860px] lg:h-[calc(100dvh-200px)] overflow-hidden">
            {pdfLoading ? (
              <div className="h-full flex items-center justify-center text-muted-foreground font-medium">
                Loading preview...
              </div>
            ) : pdfUrl ? (
              <iframe src={pdfUrl} className="w-full h-full border-0" title="PDF Preview" />
            ) : (
              <div className="h-full flex items-center justify-center border-2 border-dashed border-border rounded-md">
                <div className="text-center p-8">
                  <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
                  <p className="mt-4 text-muted-foreground font-medium">No PDF available for preview.</p>
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
