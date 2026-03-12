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
import { ACADEMIC_RECOMMENDATION_OPTIONS, getDecisionOptionLabel } from '@/lib/decision-labels'
import type {
  DecisionAttachment,
  DecisionDraft,
  DecisionReport,
  DecisionSelectionValue,
  DecisionSubmissionMode,
} from '@/types/decision'

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
  submissionMode?: DecisionSubmissionMode
  onDirtyChange: (dirty: boolean) => void
  onSubmitted: (manuscriptStatus: string) => void
}

export function getDecisionOptionsForStage(
  manuscriptStatus?: string | null,
  submissionMode: DecisionSubmissionMode = 'execute'
): DecisionSelectionValue[] {
  const normalizedStatus = String(manuscriptStatus || '').toLowerCase()
  if (submissionMode === 'recommendation') {
    if (normalizedStatus === 'decision' || normalizedStatus === 'decision_done') {
      return [...ACADEMIC_RECOMMENDATION_OPTIONS]
    }
    return []
  }
  if (normalizedStatus === 'decision_done') {
    return ['accept', 'minor_revision', 'major_revision', 'reject']
  }
  if (normalizedStatus === 'decision') {
    return ['minor_revision', 'major_revision', 'reject', 'add_reviewer']
  }
  return []
}

export { getDecisionOptionLabel }

function toAttachmentRef(attachment: DecisionAttachment): string {
  return `${attachment.id}|${attachment.path}`
}

function normalizeAttachment(raw: LocalAttachment): LocalAttachment {
  return {
    id: raw.id,
    path: raw.path,
    name: raw.name,
    ref: raw.ref || `${raw.id}|${raw.path}`,
    signed_url: raw.signed_url || null,
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
  submissionMode = 'execute',
  onDirtyChange,
  onSubmitted,
}: DecisionEditorProps) {
  const [decision, setDecision] = useState<DecisionSelectionValue>('accept')
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
  const canEditDraft = submissionMode === 'execute' && (canRecordFirst || canSubmitFinal) && normalizedStatus === 'decision'
  const decisionOptions = useMemo(
    () => getDecisionOptionsForStage(manuscriptStatus, submissionMode),
    [manuscriptStatus, submissionMode]
  )
  const decisionSelectValue = decisionOptions.includes(decision)
    ? decision
    : decisionOptions.length === 0
      ? '__decision-stage-only__'
      : decisionOptions[0]
  const decisionSpecificBlockingReasons = useMemo(() => {
    if (submissionMode === 'recommendation') {
      return []
    }
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
  }, [currentDecisionStage, decision, finalBlockingReasons, normalizedStatus, submissionMode])

  const canSubmitDecisionNow =
    submissionMode === 'recommendation'
      ? isDecisionWorkspaceStage && (currentDecisionStage === 'first' ? canRecordFirst : canSubmitFinal)
      : canSubmitFinal && decisionSpecificBlockingReasons.length === 0

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
    const availableOptions = getDecisionOptionsForStage(manuscriptStatus, submissionMode)
    const fallbackDecision: DecisionSelectionValue =
      availableOptions[0] || (submissionMode === 'recommendation' ? 'accept' : normalizedStatus === 'decision_done' ? 'accept' : 'minor_revision')
    const effectiveDraft = submissionMode === 'execute' ? initialDraft : null
    const fromDraft = effectiveDraft
      ? {
          decision: availableOptions.includes(effectiveDraft.decision)
            ? effectiveDraft.decision
            : availableOptions[0] || fallbackDecision,
          content: effectiveDraft.content || '',
          lastUpdatedAt: effectiveDraft.last_updated_at || null,
          attachments: (effectiveDraft.attachments || []).map((item) =>
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
  }, [initialDraft, manuscriptStatus, normalizedStatus, submissionMode, templateContent, onDirtyChange])

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
        signed_url: typeof res.data.signed_url === 'string' ? res.data.signed_url : null,
      }
      setAttachments((prev) => [...prev, next])
      toast.success('Attachment uploaded')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Attachment upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const openAttachment = async (attachment: LocalAttachment) => {
    try {
      const signedUrl = attachment.signed_url
      if (signedUrl) {
        window.open(String(signedUrl), '_blank', 'noopener,noreferrer')
        return
      }
      const res = await EditorApi.getDecisionAttachmentSignedUrl(manuscriptId, attachment.id)
      if (!res?.success || !res?.data?.signed_url) {
        throw new Error(res?.detail || res?.message || 'Failed to open attachment')
      }
      window.open(String(res.data.signed_url), '_blank', 'noopener,noreferrer')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to open attachment')
    }
  }

  const removeAttachment = (attachmentId: string) => {
    setAttachments((prev) => prev.filter((item) => item.id !== attachmentId))
    toast.success('Attachment removed from current draft')
  }

  const submit = async (isFinal: boolean) => {
    if (isReadOnly) return
    if (submissionMode === 'recommendation' && !isFinal) {
      toast.error('Recommendation mode does not support draft save')
      return
    }
    if (!isFinal && !canEditDraft) {
      toast.error('First decision draft is only available in decision stage')
      return
    }
    if (submissionMode !== 'recommendation' && isFinal && decision !== 'add_reviewer' && !content.trim()) {
      toast.error(`${currentDecisionStage === 'first' ? 'First' : 'Final'} decision requires letter content`)
      return
    }
    const canSubmitCurrentStage =
      currentDecisionStage === 'first' ? canRecordFirst || canSubmitFinal : canSubmitFinal
    if (isFinal && !canSubmitCurrentStage) {
      toast.error(
        submissionMode === 'recommendation'
          ? `Current role cannot submit ${currentDecisionStage} recommendation`
          : `Current role cannot submit ${currentDecisionStage} decision`
      )
      return
    }
    if (isFinal && !canSubmitDecisionNow) {
      toast.error(
        decisionSpecificBlockingReasons[0] ||
          `${currentDecisionStage} ${submissionMode === 'recommendation' ? 'recommendation' : 'decision'} is blocked by workflow requirements`
      )
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
          submissionMode === 'recommendation'
            ? `${currentDecisionStage === 'first' ? 'First' : 'Final'} recommendation recorded`
            : decision === 'add_reviewer'
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
      <h2 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">
        {submissionMode === 'recommendation' ? 'Academic Recommendation' : 'Decision Letter'}
      </h2>
      <p className="mt-1 text-xs text-muted-foreground">
        {submissionMode === 'recommendation'
          ? currentDecisionStage === 'first'
            ? 'First recommendation records the academic conclusion only. Editorial staff will decide the actual manuscript transition and author communication.'
            : 'Final recommendation records the academic conclusion only. It does not directly change manuscript status or notify the author.'
          : currentDecisionStage === 'first'
            ? 'First decision can be saved as a draft in the decision queue. Submitting Add Additional Reviewer will immediately return the manuscript to under review.'
            : 'Final decision is only available in the final decision queue and will trigger the manuscript state transition.'}
      </p>
      {!isDecisionWorkspaceStage ? (
        <p className="mt-1 rounded-md border border-border bg-muted/40 px-2.5 py-1.5 text-xs text-muted-foreground">
          当前稿件尚未进入 `decision / decision_done`，请先通过 `Exit Review Stage` 推进流程。
        </p>
      ) : null}
      {!canSubmitFinal && submissionMode !== 'recommendation' ? (
        <p className="mt-1 rounded-md border border-primary/30 bg-primary/10 px-2.5 py-1.5 text-xs text-primary">
          当前账号仅可记录 First Decision 草稿；提交当前决策动作需具备对应阶段的提交权限。
        </p>
      ) : null}
      {submissionMode !== 'recommendation' && canSubmitFinal && !canSubmitDecisionNow ? (
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
          <label htmlFor="decision-letter-select" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {submissionMode === 'recommendation' ? 'Recommendation' : 'Decision'}
          </label>
          <Select
            value={decisionSelectValue}
            onValueChange={(value) => setDecision(value as DecisionSelectionValue)}
            disabled={isReadOnly || isSavingDraft || isSubmittingFinal || decisionOptions.length === 0}
          >
            <SelectTrigger id="decision-letter-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {decisionOptions.length > 0 ? (
                decisionOptions.map((option) => (
                  <SelectItem key={option} value={option}>
                    {getDecisionOptionLabel(option)}
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
            <label htmlFor="decision-letter-content" className="block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {submissionMode === 'recommendation' ? 'Recommendation Note (Optional)' : 'Letter Content (Markdown)'}
            </label>
            {submissionMode === 'execute' ? (
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
            ) : null}
          </div>
          <Textarea
            id="decision-letter-content"
            rows={16}
            value={content}
            onChange={(event) => setContent(event.target.value)}
            disabled={isReadOnly}
            className="w-full rounded-md border border-border px-3 py-2 font-mono text-sm leading-6"
            placeholder={submissionMode === 'recommendation' ? 'Write recommendation note...' : 'Write decision letter...'}
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
                    onClick={() => void openAttachment(item)}
                    variant="link"
                    className="shrink-0 px-0 font-semibold text-primary hover:underline"
                  >
                    Open
                  </Button>
                  {!isReadOnly && canEditDraft ? (
                    <Button
                      type="button"
                      onClick={() => removeAttachment(item.id)}
                      variant="link"
                      className="shrink-0 px-0 font-semibold text-destructive hover:underline"
                    >
                      Remove
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-xs text-muted-foreground">No attachment uploaded.</p>
          )}
          {isUploading ? <Loader2 className="mt-2 h-4 w-4 animate-spin text-muted-foreground" /> : null}
        </div>

        <div className={`grid grid-cols-1 gap-2 ${submissionMode === 'execute' ? 'sm:grid-cols-2' : ''}`}>
          {submissionMode === 'execute' ? (
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
          ) : null}
          <Button
            type="button"
            onClick={() => void submit(true)}
            disabled={isReadOnly || isSavingDraft || isSubmittingFinal || !canSubmitDecisionNow}
            className="inline-flex items-center justify-center gap-2 text-sm font-semibold disabled:opacity-60"
          >
            {isSubmittingFinal ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            {submissionMode === 'recommendation'
              ? currentDecisionStage === 'first'
                ? 'Submit First Recommendation'
                : 'Submit Final Recommendation'
              : decision === 'add_reviewer'
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
