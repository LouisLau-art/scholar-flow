'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Loader2, Save, Send, WandSparkles } from 'lucide-react'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { assembleLetter } from '@/lib/decision-utils'
import type { DecisionAttachment, DecisionDraft, DecisionReport, FinalDecision } from '@/types/decision'

type LocalAttachment = DecisionAttachment & { ref: string }

type DecisionEditorProps = {
  manuscriptId: string
  reports: DecisionReport[]
  manuscriptStatus?: string | null
  initialDraft?: DecisionDraft | null
  templateContent?: string
  canSubmit: boolean
  canRecordFirst: boolean
  canSubmitFinal: boolean
  hasSubmittedAuthorRevision: boolean
  finalBlockingReasons: string[]
  isReadOnly: boolean
  onDirtyChange: (dirty: boolean) => void
  onSubmitted: (manuscriptStatus: string) => void
}

export function getDecisionOptionsForStage(manuscriptStatus?: string | null): FinalDecision[] {
  const normalizedStatus = String(manuscriptStatus || '').toLowerCase()
  if (normalizedStatus === 'decision_done') {
    return ['accept', 'minor_revision', 'major_revision', 'reject']
  }
  if (normalizedStatus === 'decision') {
    return ['minor_revision', 'major_revision', 'reject', 'add_reviewer']
  }
  return []
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
  manuscriptStatus,
  initialDraft,
  templateContent,
  canSubmit,
  canRecordFirst,
  canSubmitFinal,
  finalBlockingReasons,
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

  const normalizedStatus = String(manuscriptStatus || '').toLowerCase()
  const isDecisionWorkspaceStage = ['decision', 'decision_done'].includes(normalizedStatus)
  const currentDecisionStage: 'first' | 'final' = normalizedStatus === 'decision_done' ? 'final' : 'first'
  const canEditDraft = (canRecordFirst || canSubmitFinal) && normalizedStatus === 'decision'
  const decisionOptions = useMemo(() => getDecisionOptionsForStage(manuscriptStatus), [manuscriptStatus])
  const decisionSelectValue = decisionOptions.includes(decision)
    ? decision
    : decisionOptions.length === 0
      ? '__decision-stage-only__'
      : decisionOptions[0]
  const decisionSpecificBlockingReasons = useMemo(() => {
    const reasons = [...finalBlockingReasons]
    if (currentDecisionStage === 'first') {
      if (decision === 'accept') {
        reasons.push('Accept is not available in first decision stage')
      }
      return reasons
    }
    if (decision === 'major_revision' || decision === 'minor_revision') {
      if (!['decision', 'decision_done'].includes(normalizedStatus)) {
        reasons.push('Revision decision is only allowed in decision/decision_done stage')
      }
      return reasons
    }
    if (decision === 'accept') {
      if (normalizedStatus !== 'decision_done') {
        reasons.push('Accept is only allowed in final decision queue (decision_done)')
      }
      return reasons
    }
    if (!['decision', 'decision_done'].includes(normalizedStatus)) {
      reasons.push('Final reject requires manuscript status in decision/decision_done')
    }
    return reasons
  }, [currentDecisionStage, decision, finalBlockingReasons, normalizedStatus])

  const canSubmitDecisionNow = canSubmitFinal && decisionSpecificBlockingReasons.length === 0

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
    const availableOptions = getDecisionOptionsForStage(manuscriptStatus)
    const fallbackDecision: FinalDecision = normalizedStatus === 'decision_done' ? 'accept' : 'minor_revision'
    const fromDraft = initialDraft
      ? {
          decision: availableOptions.includes(initialDraft.decision)
            ? initialDraft.decision
            : availableOptions[0] || fallbackDecision,
          content: initialDraft.content || '',
          lastUpdatedAt: initialDraft.last_updated_at || null,
          attachments: (initialDraft.attachments || []).map((item) =>
            normalizeAttachment({ ...item, ref: toAttachmentRef(item) })
          ),
        }
      : {
          decision: availableOptions[0] || fallbackDecision,
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
  }, [initialDraft, manuscriptStatus, normalizedStatus, templateContent, onDirtyChange])

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
    if (!isFinal && !canEditDraft) {
      toast.error('First decision draft is only available in decision stage')
      return
    }
    if (isFinal && decision !== 'add_reviewer' && !content.trim()) {
      toast.error(`${currentDecisionStage === 'first' ? 'First' : 'Final'} decision requires letter content`)
      return
    }
    if (isFinal && !canSubmitFinal) {
      toast.error(`Only Editor-in-Chief/Admin can submit ${currentDecisionStage} decision`)
      return
    }
    if (isFinal && !canSubmitDecisionNow) {
      toast.error(decisionSpecificBlockingReasons[0] || `${currentDecisionStage} decision is blocked by workflow requirements`)
      return
    }

    const run = isFinal ? setIsSubmittingFinal : setIsSavingDraft
    run(true)
    try {
      const res = await EditorApi.submitDecision(manuscriptId, {
        content,
        decision,
        is_final: isFinal,
        decision_stage: currentDecisionStage,
        attachment_paths: attachments.map((item) => item.ref),
        last_updated_at: lastUpdatedAt,
      })
      if (!res?.success || !res?.data) {
        throw new Error(res?.detail || res?.message || 'Failed to submit decision')
      }

      const updatedAt = (res.data.updated_at as string | null) ?? lastUpdatedAt
      setSavedBaseline(updatedAt)

      if (isFinal) {
        toast.success(
          decision === 'add_reviewer'
            ? 'Manuscript returned to under review'
            : `${currentDecisionStage === 'first' ? 'First' : 'Final'} decision submitted`
        )
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
    <aside className="rounded-lg border border-border bg-card p-4">
      <h2 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">Decision Letter</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        {currentDecisionStage === 'first'
          ? 'First decision can be saved as a draft in the decision queue. Submitting add reviewer will immediately return the manuscript to under review.'
          : 'Final decision is only available in the final decision queue and will trigger the manuscript state transition.'}
      </p>
      {!isDecisionWorkspaceStage ? (
        <p className="mt-1 rounded-md border border-border bg-muted/40 px-2.5 py-1.5 text-xs text-muted-foreground">
          当前稿件尚未进入 `decision / decision_done`，请先通过 `Exit Review Stage` 推进流程。
        </p>
      ) : null}
      {!canSubmitFinal ? (
        <p className="mt-1 rounded-md border border-primary/30 bg-primary/10 px-2.5 py-1.5 text-xs text-primary">
          当前账号仅可记录 First Decision 草稿；提交决策动作需由 Editor-in-Chief/Admin 执行。
        </p>
      ) : null}
      {canSubmitFinal && !canSubmitDecisionNow ? (
        <div className="mt-1 rounded-md border border-destructive/30 bg-destructive/10 px-2.5 py-1.5 text-xs text-destructive">
          <div className="font-semibold">{currentDecisionStage === 'first' ? 'First decision blocked' : 'Final decision blocked'}</div>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {decisionSpecificBlockingReasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-4 space-y-4">
        <div>
          <label htmlFor="decision-letter-select" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Decision</label>
          <Select
            value={decisionSelectValue}
            onValueChange={(value) => setDecision(value as FinalDecision)}
            disabled={isReadOnly || isSavingDraft || isSubmittingFinal || decisionOptions.length === 0}
          >
            <SelectTrigger id="decision-letter-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {decisionOptions.length > 0 ? (
                decisionOptions.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option === 'accept'
                      ? 'Accept'
                      : option === 'add_reviewer'
                        ? 'Add Reviewer'
                      : option === 'minor_revision'
                        ? 'Minor Revision'
                        : option === 'major_revision'
                          ? 'Major Revision'
                          : 'Reject'}
                  </SelectItem>
                ))
              ) : (
                <SelectItem value="__decision-stage-only__" disabled>
                  Decision workspace only available in decision / decision_done
                </SelectItem>
              )}
            </SelectContent>
          </Select>
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <label htmlFor="decision-letter-content" className="block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Letter Content (Markdown)</label>
            <Button
              type="button"
              onClick={handleGenerateDraft}
              disabled={isReadOnly || isSavingDraft || isSubmittingFinal || !canEditDraft}
              variant="ghost"
              className="inline-flex items-center gap-1 px-0 text-xs font-semibold text-primary hover:underline disabled:opacity-60"
            >
              <WandSparkles className="h-3.5 w-3.5" />
              Generate Letter Draft
            </Button>
          </div>
          <Textarea
            id="decision-letter-content"
            rows={16}
            value={content}
            onChange={(event) => setContent(event.target.value)}
            disabled={isReadOnly}
            className="w-full rounded-md border border-border px-3 py-2 font-mono text-sm leading-6"
            placeholder="Write decision letter..."
          />
        </div>

        <div>
          <label htmlFor="decision-letter-attachment" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Attachments</label>
          <Input
            id="decision-letter-attachment"
            type="file"
            disabled={isReadOnly || isUploading || !canEditDraft}
            onChange={(event) => void handleUpload(event.target.files?.[0] ?? null)}
            className="block w-full text-xs text-muted-foreground"
          />
          {attachments.length > 0 ? (
            <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
              {attachments.map((item) => (
                <li key={item.ref} className="flex items-center justify-between gap-2">
                  <span className="truncate">{item.name}</span>
                  <Button
                    type="button"
                    onClick={() => void openAttachment(item.id)}
                    variant="link"
                    className="shrink-0 px-0 font-semibold text-primary hover:underline"
                  >
                    Open
                  </Button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-xs text-muted-foreground">No attachment uploaded.</p>
          )}
          {isUploading ? <Loader2 className="mt-2 h-4 w-4 animate-spin text-muted-foreground" /> : null}
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <Button
            type="button"
            onClick={() => void submit(false)}
            disabled={isReadOnly || isSavingDraft || isSubmittingFinal || !canEditDraft}
            variant="outline"
            className="inline-flex items-center justify-center gap-2 text-sm font-semibold disabled:opacity-60"
          >
            {isSavingDraft ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save First Decision Draft
          </Button>
          <Button
            type="button"
            onClick={() => void submit(true)}
            disabled={isReadOnly || isSavingDraft || isSubmittingFinal || !canSubmitFinal || !canSubmitDecisionNow}
            className="inline-flex items-center justify-center gap-2 text-sm font-semibold disabled:opacity-60"
          >
            {isSubmittingFinal ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            {decision === 'add_reviewer'
              ? 'Return To Under Review'
              : currentDecisionStage === 'first'
                ? 'Submit First Decision'
                : 'Submit Final Decision'}
          </Button>
        </div>
      </div>
    </aside>
  )
}
