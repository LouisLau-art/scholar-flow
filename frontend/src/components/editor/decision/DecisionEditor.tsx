'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Loader2, Save, Send, WandSparkles } from 'lucide-react'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { assembleLetter } from '@/lib/decision-utils'
import type { DecisionAttachment, DecisionDraft, DecisionReport, FinalDecision } from '@/types/decision'

type LocalAttachment = DecisionAttachment & { ref: string }

type DecisionEditorProps = {
  manuscriptId: string
  reports: DecisionReport[]
  initialDraft?: DecisionDraft | null
  templateContent?: string
  canSubmit: boolean
  isReadOnly: boolean
  onDirtyChange: (dirty: boolean) => void
  onSubmitted: (manuscriptStatus: string) => void
}

function toAttachmentRef(attachment: DecisionAttachment): string {
  return `${attachment.id}|${attachment.path}`
}

function normalizeAttachment(raw: LocalAttachment): LocalAttachment {
  return {
    id: raw.id,
    path: raw.path,
    name: raw.name,
    ref: raw.ref || `${raw.id}|${raw.path}`,
  }
}

export function DecisionEditor({
  manuscriptId,
  reports,
  initialDraft,
  templateContent,
  canSubmit,
  isReadOnly,
  onDirtyChange,
  onSubmitted,
}: DecisionEditorProps) {
  const [decision, setDecision] = useState<FinalDecision>('minor_revision')
  const [content, setContent] = useState('')
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null)
  const [attachments, setAttachments] = useState<LocalAttachment[]>([])
  const [isSavingDraft, setIsSavingDraft] = useState(false)
  const [isSubmittingFinal, setIsSubmittingFinal] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const baselineRef = useRef('')

  const snapshot = useMemo(
    () =>
      JSON.stringify({
        decision,
        content,
        lastUpdatedAt,
        attachments: attachments.map((item) => ({ id: item.id, path: item.path, ref: item.ref })),
      }),
    [decision, content, lastUpdatedAt, attachments]
  )

  useEffect(() => {
    const fromDraft = initialDraft
      ? {
          decision: initialDraft.decision,
          content: initialDraft.content || '',
          lastUpdatedAt: initialDraft.last_updated_at || null,
          attachments: (initialDraft.attachments || []).map((item) =>
            normalizeAttachment({ ...item, ref: toAttachmentRef(item) })
          ),
        }
      : {
          decision: 'minor_revision' as FinalDecision,
          content: templateContent || '',
          lastUpdatedAt: null,
          attachments: [] as LocalAttachment[],
        }

    setDecision(fromDraft.decision)
    setContent(fromDraft.content)
    setLastUpdatedAt(fromDraft.lastUpdatedAt)
    setAttachments(fromDraft.attachments)

    baselineRef.current = JSON.stringify({
      decision: fromDraft.decision,
      content: fromDraft.content,
      lastUpdatedAt: fromDraft.lastUpdatedAt,
      attachments: fromDraft.attachments.map((item) => ({ id: item.id, path: item.path, ref: item.ref })),
    })
    onDirtyChange(false)
  }, [initialDraft, templateContent, onDirtyChange])

  useEffect(() => {
    onDirtyChange(snapshot !== baselineRef.current && !isReadOnly)
  }, [snapshot, onDirtyChange, isReadOnly])

  const setSavedBaseline = (updatedAt: string | null) => {
    const normalized = JSON.stringify({
      decision,
      content,
      lastUpdatedAt: updatedAt,
      attachments: attachments.map((item) => ({ id: item.id, path: item.path, ref: item.ref })),
    })
    baselineRef.current = normalized
    setLastUpdatedAt(updatedAt)
    onDirtyChange(false)
  }

  const handleGenerateDraft = () => {
    const generated = assembleLetter(reports)
    setContent(generated)
    toast.success('Draft generated from reviewer comments')
  }

  const handleUpload = async (file: File | null) => {
    if (!file || isReadOnly) return
    setIsUploading(true)
    try {
      const res = await EditorApi.uploadDecisionAttachment(manuscriptId, file)
      if (!res?.success || !res?.data?.attachment_id || !res?.data?.path) {
        throw new Error(res?.detail || res?.message || 'Attachment upload failed')
      }
      const next: LocalAttachment = {
        id: String(res.data.attachment_id),
        path: String(res.data.path),
        name: file.name,
        ref: String(res.data.ref || `${res.data.attachment_id}|${res.data.path}`),
      }
      setAttachments((prev) => [...prev, next])
      toast.success('Attachment uploaded')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Attachment upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const openAttachment = async (attachmentId: string) => {
    try {
      const res = await EditorApi.getDecisionAttachmentSignedUrl(manuscriptId, attachmentId)
      if (!res?.success || !res?.data?.signed_url) {
        throw new Error(res?.detail || res?.message || 'Failed to open attachment')
      }
      window.open(String(res.data.signed_url), '_blank', 'noopener,noreferrer')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to open attachment')
    }
  }

  const submit = async (isFinal: boolean) => {
    if (isReadOnly) return
    if (isFinal && !content.trim()) {
      toast.error('Final submission requires decision letter content')
      return
    }
    if (isFinal && !canSubmit) {
      toast.error('At least one submitted review report is required')
      return
    }

    const run = isFinal ? setIsSubmittingFinal : setIsSavingDraft
    run(true)
    try {
      const res = await EditorApi.submitDecision(manuscriptId, {
        content,
        decision,
        is_final: isFinal,
        decision_stage: isFinal ? 'final' : 'first',
        attachment_paths: attachments.map((item) => item.ref),
        last_updated_at: lastUpdatedAt,
      })
      if (!res?.success || !res?.data) {
        throw new Error(res?.detail || res?.message || 'Failed to submit decision')
      }

      const updatedAt = (res.data.updated_at as string | null) ?? lastUpdatedAt
      setSavedBaseline(updatedAt)

      if (isFinal) {
        toast.success('Final decision submitted')
        onSubmitted(String(res.data.manuscript_status || ''))
      } else {
        toast.success('Draft saved')
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to submit decision')
    } finally {
      run(false)
    }
  }

  return (
    <aside className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-bold uppercase tracking-wide text-slate-700">Decision Letter</h2>
      <p className="mt-1 text-xs text-slate-500">
        Draft content and attachments remain private until <strong>Submit Final Decision</strong>.
      </p>

      <div className="mt-4 space-y-4">
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Decision</label>
          <Select
            value={decision}
            onValueChange={(value) => setDecision(value as FinalDecision)}
            disabled={isReadOnly || isSavingDraft || isSubmittingFinal}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="accept">Accept</SelectItem>
              <SelectItem value="minor_revision">Minor Revision</SelectItem>
              <SelectItem value="major_revision">Major Revision</SelectItem>
              <SelectItem value="reject">Reject</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <label className="block text-xs font-semibold uppercase tracking-wide text-slate-600">Letter Content (Markdown)</label>
            <button
              type="button"
              onClick={handleGenerateDraft}
              disabled={isReadOnly || isSavingDraft || isSubmittingFinal}
              className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:underline disabled:opacity-60"
            >
              <WandSparkles className="h-3.5 w-3.5" />
              Generate Letter Draft
            </button>
          </div>
          <textarea
            rows={16}
            value={content}
            onChange={(event) => setContent(event.target.value)}
            disabled={isReadOnly}
            className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm leading-6"
            placeholder="Write decision letter..."
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Attachments</label>
          <input
            type="file"
            disabled={isReadOnly || isUploading}
            onChange={(event) => void handleUpload(event.target.files?.[0] ?? null)}
            className="block w-full text-xs text-slate-600"
          />
          {attachments.length > 0 ? (
            <ul className="mt-2 space-y-1 text-xs text-slate-600">
              {attachments.map((item) => (
                <li key={item.ref} className="flex items-center justify-between gap-2">
                  <span className="truncate">{item.name}</span>
                  <button
                    type="button"
                    onClick={() => void openAttachment(item.id)}
                    className="shrink-0 font-semibold text-blue-600 hover:underline"
                  >
                    Open
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-xs text-slate-500">No attachment uploaded.</p>
          )}
          {isUploading ? <Loader2 className="mt-2 h-4 w-4 animate-spin text-slate-500" /> : null}
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => void submit(false)}
            disabled={isReadOnly || isSavingDraft || isSubmittingFinal}
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 disabled:opacity-60"
          >
            {isSavingDraft ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save Draft
          </button>
          <button
            type="button"
            onClick={() => void submit(true)}
            disabled={isReadOnly || isSavingDraft || isSubmittingFinal}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {isSubmittingFinal ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            Submit Final Decision
          </button>
        </div>
      </div>
    </aside>
  )
}
