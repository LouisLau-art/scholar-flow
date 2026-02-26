'use client'

import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { Loader2, Save, Send, ShieldAlert, FileText, Download } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import type { ReviewSubmission, WorkspaceAttachment, WorkspaceData } from '@/types/review'

interface ActionPanelProps {
  assignmentId: string
  workspace: WorkspaceData
  onSubmitted: () => void
  onDirtyChange: (dirty: boolean) => void
}

type FormValues = {
  comments_for_author: string
  confidential_comments_to_editor: string
}

function extractFilename(path: string): string {
  const raw = String(path || '').trim()
  if (!raw) return 'attachment'
  return raw.split('/').pop() || 'attachment'
}

function normalizeAttachmentList(raw: unknown): WorkspaceAttachment[] {
  if (!Array.isArray(raw)) return []
  const out: WorkspaceAttachment[] = []
  for (const item of raw) {
    if (typeof item === 'string') {
      const path = item.trim()
      if (!path) continue
      out.push({ path, filename: extractFilename(path), signed_url: null })
      continue
    }
    if (item && typeof item === 'object') {
      const obj = item as { path?: unknown; filename?: unknown; signed_url?: unknown }
      const path = typeof obj.path === 'string' ? obj.path.trim() : ''
      if (!path) continue
      out.push({
        path,
        filename: typeof obj.filename === 'string' && obj.filename.trim() ? obj.filename.trim() : extractFilename(path),
        signed_url: typeof obj.signed_url === 'string' ? obj.signed_url : null,
      })
    }
  }
  return out
}

export function ActionPanel({ assignmentId, workspace, onSubmitted, onDirtyChange }: ActionPanelProps) {
  const reviewReport = workspace.review_report || {
    comments_for_author: '',
    confidential_comments_to_editor: '',
    attachments: [],
    status: 'pending',
  }
  const [isUploading, setIsUploading] = useState(false)
  const [attachments, setAttachments] = useState<WorkspaceAttachment[]>(
    normalizeAttachmentList(reviewReport.attachments)
  )
  const isReadOnly = workspace.permissions.is_read_only
  const draftStorageKey = useMemo(() => `sf:reviewer:draft:${assignmentId}`, [assignmentId])
  const form = useForm<FormValues>({
    mode: 'onChange',
    defaultValues: {
      comments_for_author: reviewReport.comments_for_author || '',
      confidential_comments_to_editor: reviewReport.confidential_comments_to_editor || '',
    },
  })

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty, isSubmitting },
    getValues,
    reset,
    setValue,
  } = form

  useEffect(() => {
    reset({
      comments_for_author: reviewReport.comments_for_author || '',
      confidential_comments_to_editor: reviewReport.confidential_comments_to_editor || '',
    })
    setAttachments(normalizeAttachmentList(reviewReport.attachments))
  }, [
    reset,
    reviewReport.attachments,
    reviewReport.comments_for_author,
    reviewReport.confidential_comments_to_editor,
  ])

  useEffect(() => {
    if (isReadOnly) {
      onDirtyChange(false)
      return
    }
    onDirtyChange(isDirty)
  }, [isDirty, isReadOnly, onDirtyChange])

  useEffect(() => {
    if (isReadOnly) return
    const authorComment = String(reviewReport.comments_for_author || '').trim()
    const privateComment = String(reviewReport.confidential_comments_to_editor || '').trim()
    if (authorComment || privateComment) return
    try {
      const raw = window.localStorage.getItem(draftStorageKey)
      if (!raw) return
      const parsed = JSON.parse(raw) as {
        comments_for_author?: string
        confidential_comments_to_editor?: string
      } | null
      if (!parsed) return
      if (typeof parsed.comments_for_author === 'string') {
        setValue('comments_for_author', parsed.comments_for_author, { shouldDirty: false })
      }
      if (typeof parsed.confidential_comments_to_editor === 'string') {
        setValue('confidential_comments_to_editor', parsed.confidential_comments_to_editor, { shouldDirty: false })
      }
    } catch {
      // ignore corrupted local draft
    }
  }, [
    draftStorageKey,
    isReadOnly,
    setValue,
    reviewReport.comments_for_author,
    reviewReport.confidential_comments_to_editor,
  ])

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
      const path = String(json.data.path)
      setAttachments((prev) => [
        ...prev,
        {
          path,
          filename: extractFilename(path),
          signed_url: json?.data?.url ? String(json.data.url) : null,
        },
      ])
      toast.success('Attachment uploaded')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Attachment upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const saveDraft = () => {
    if (isReadOnly) return
    const values = getValues()
    try {
      window.localStorage.setItem(
        draftStorageKey,
        JSON.stringify({
          comments_for_author: values.comments_for_author || '',
          confidential_comments_to_editor: values.confidential_comments_to_editor || '',
        })
      )
      toast.success('Draft saved locally')
    } catch {
      toast.error('Failed to save local draft')
    }
  }

  const onSubmit = handleSubmit(async (values) => {
    const payload: ReviewSubmission = {
      comments_for_author: values.comments_for_author,
      confidential_comments_to_editor: values.confidential_comments_to_editor,
      recommendation: 'minor_revision',
      attachments: attachments.map((item) => item.path),
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
    try {
      window.localStorage.removeItem(draftStorageKey)
    } catch {
      // ignore
    }
    toast.success('Review submitted')
    onSubmitted()
  })

  return (
    <Card className="border-border shadow-sm">
      <CardHeader>
        <CardTitle className="text-lg">Review Comment</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {isReadOnly ? (
          <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            This review is submitted. The form is now read-only.
          </div>
        ) : null}

        <form className="space-y-5" onSubmit={(event) => void onSubmit(event)}>
          <div className="space-y-2">
            <label className="text-sm font-semibold text-foreground" htmlFor="comments_for_author">
              Comment to Authors
            </label>
            <Textarea
              id="comments_for_author"
              rows={10}
              disabled={isReadOnly}
              placeholder="Write your review comment..."
              {...register('comments_for_author', { required: 'Comment is required' })}
            />
            {errors.comments_for_author ? (
              <p className="text-xs font-semibold text-rose-600">{errors.comments_for_author.message}</p>
            ) : (
              <p className="text-xs text-muted-foreground">
                This section is visible to authors and editors.
              </p>
            )}
          </div>

          <div className="space-y-2">
            <label className="inline-flex items-center gap-1.5 text-sm font-semibold text-foreground" htmlFor="confidential_comments_to_editor">
              <ShieldAlert className="h-4 w-4 text-amber-600" />
              Private note to Editor (optional)
            </label>
            <Textarea
              id="confidential_comments_to_editor"
              rows={6}
              disabled={isReadOnly}
              placeholder="Only editors can see this note."
              {...register('confidential_comments_to_editor')}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-foreground">Attachment (optional)</label>
            <div className="flex items-center gap-2">
              <Input
                type="file"
                accept="application/pdf,.doc,.docx,.txt"
                disabled={isReadOnly || isUploading}
                onChange={(event) => void handleUpload(event.target.files?.[0] ?? null)}
              />
              {isUploading ? <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" /> : null}
            </div>
            {attachments.length > 0 ? (
              <div className="space-y-2 rounded-md border border-border bg-muted/50 p-2.5">
                {attachments.map((item) => (
                  <div key={item.path} className="flex items-center justify-between gap-2 text-xs">
                    <div className="inline-flex items-center gap-1.5 text-foreground">
                      <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                      <span>{item.filename || extractFilename(item.path)}</span>
                    </div>
                    {item.signed_url ? (
                      <a
                        href={item.signed_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-primary hover:text-primary/80"
                      >
                        <Download className="h-3.5 w-3.5" />
                        Download
                      </a>
                    ) : (
                      <Badge variant="secondary">Stored</Badge>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No attachment uploaded.</p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={saveDraft}
              disabled={isReadOnly || isSubmitting || isUploading}
              className="gap-1.5"
            >
              <Save className="h-4 w-4" />
              Save Draft
            </Button>
            <Button type="submit" disabled={isReadOnly || isSubmitting || isUploading} className="gap-1.5">
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              {isReadOnly ? 'Read-only' : isSubmitting ? 'Submitting…' : 'Submit Review'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
