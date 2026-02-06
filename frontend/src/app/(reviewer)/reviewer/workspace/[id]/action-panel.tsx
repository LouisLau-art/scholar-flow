'use client'

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { Loader2, Send } from 'lucide-react'
import type { ReviewSubmission, WorkspaceData } from '@/types/review'

interface ActionPanelProps {
  assignmentId: string
  workspace: WorkspaceData
  onSubmitted: () => void
  onDirtyChange: (dirty: boolean) => void
}

type FormValues = {
  comments_for_author: string
  confidential_comments_to_editor: string
  recommendation: ReviewSubmission['recommendation']
}

export function ActionPanel({ assignmentId, workspace, onSubmitted, onDirtyChange }: ActionPanelProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [attachmentPaths, setAttachmentPaths] = useState<string[]>(workspace.review_report.attachments || [])
  const isReadOnly = workspace.permissions.is_read_only
  const form = useForm<FormValues>({
    mode: 'onChange',
    defaultValues: {
      comments_for_author: workspace.review_report.comments_for_author || '',
      confidential_comments_to_editor: workspace.review_report.confidential_comments_to_editor || '',
      recommendation: workspace.review_report.recommendation || 'minor_revision',
    },
  })

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty, isSubmitting },
  } = form

  useEffect(() => {
    onDirtyChange(isDirty && !isReadOnly)
  }, [isDirty, isReadOnly, onDirtyChange])

  const handleUpload = async (file: File | null) => {
    if (!file) return
    setIsUploading(true)
    try {
      const body = new FormData()
      body.append('file', file)
      const res = await fetch(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/attachments`, {
        method: 'POST',
        body,
      })
      const json = await res.json().catch(() => null)
      if (!res.ok || !json?.success || !json?.data?.path) {
        throw new Error(json?.detail || json?.message || 'Attachment upload failed')
      }
      setAttachmentPaths((prev) => [...prev, String(json.data.path)])
      toast.success('Attachment uploaded')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Attachment upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const onSubmit = handleSubmit(async (values) => {
    const payload: ReviewSubmission = {
      ...values,
      attachments: attachmentPaths,
    }
    const res = await fetch(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/submit`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const json = await res.json().catch(() => null)
    if (!res.ok || !json?.success) {
      throw new Error(json?.detail || json?.message || 'Submit failed')
    }
    toast.success('Review submitted')
    onSubmitted()
  })

  return (
    <aside className="rounded-lg border border-slate-200 bg-white p-4 sm:p-6">
      <h2 className="text-lg font-semibold text-slate-900">Action Panel</h2>
      <p className="mt-1 text-sm text-slate-500">Submit your recommendation and comments.</p>

      <form className="mt-5 space-y-5" onSubmit={(e) => void onSubmit(e)}>
        <div>
          <label className="text-sm font-semibold text-slate-900" htmlFor="recommendation">
            Recommendation
          </label>
          <select
            id="recommendation"
            disabled={isReadOnly}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100"
            {...register('recommendation', { required: true })}
          >
            <option value="accept">Accept</option>
            <option value="minor_revision">Minor Revision</option>
            <option value="major_revision">Major Revision</option>
            <option value="reject">Reject</option>
          </select>
        </div>

        <div>
          <label className="text-sm font-semibold text-slate-900" htmlFor="comments_for_author">
            Comments for the Authors
          </label>
          <textarea
            id="comments_for_author"
            rows={8}
            disabled={isReadOnly}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100"
            {...register('comments_for_author', { required: 'Required' })}
          />
          {errors.comments_for_author ? (
            <p className="mt-1 text-xs font-semibold text-rose-600">{errors.comments_for_author.message}</p>
          ) : null}
        </div>

        <div>
          <label className="text-sm font-semibold text-slate-900" htmlFor="confidential_comments_to_editor">
            Confidential Comments to the Editor
          </label>
          <p className="mt-1 text-xs font-semibold text-red-600">Authors will NOT see this.</p>
          <textarea
            id="confidential_comments_to_editor"
            rows={5}
            disabled={isReadOnly}
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100"
            {...register('confidential_comments_to_editor')}
          />
        </div>

        <div>
          <label className="text-sm font-semibold text-slate-900">Attachments</label>
          <div className="mt-2 flex items-center gap-3">
            <input
              type="file"
              accept="application/pdf"
              disabled={isReadOnly || isUploading}
              onChange={(event) => void handleUpload(event.target.files?.[0] ?? null)}
              className="block w-full text-xs text-slate-600"
            />
            {isUploading ? <Loader2 className="h-4 w-4 animate-spin text-slate-500" /> : null}
          </div>
          {attachmentPaths.length > 0 ? (
            <ul className="mt-2 space-y-1 text-xs text-slate-600">
              {attachmentPaths.map((item) => (
                <li key={item}>{item.split('/').pop()}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-xs text-slate-500">No attachment uploaded.</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isReadOnly || isSubmitting || isUploading}
          className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Send className="h-4 w-4" />
          {isReadOnly ? 'Read-only' : isSubmitting ? 'Submitting...' : 'Submit Review'}
        </button>
      </form>
    </aside>
  )
}
