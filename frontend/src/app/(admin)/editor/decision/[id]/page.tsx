'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import { DecisionWorkspaceLayout } from '@/components/editor/decision/DecisionWorkspaceLayout'
import { ReviewReportComparison } from '@/components/editor/decision/ReviewReportComparison'
import { DecisionEditor } from '@/components/editor/decision/DecisionEditor'
import type { DecisionContext } from '@/types/decision'

function getReviewStageExitRequestedOutcomeLabel(
  outcome: 'major_revision' | 'minor_revision' | 'reject' | 'add_reviewer'
): string {
  switch (outcome) {
    case 'major_revision':
      return 'Major Revision'
    case 'minor_revision':
      return 'Minor Revision'
    case 'reject':
      return 'Reject'
    case 'add_reviewer':
      return 'Add Reviewer'
    default:
      return String(outcome)
  }
}

export default function DecisionWorkspacePage() {
  const params = useParams()
  const router = useRouter()
  const manuscriptId = String((params as Record<string, string>)?.id || '')
  const [context, setContext] = useState<DecisionContext | null>(null)
  const [loading, setLoading] = useState(true)
  const [dirty, setDirty] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res = await EditorApi.getDecisionContext(manuscriptId)
      if (!res?.success || !res?.data) {
        const detail = String(res?.detail || res?.message || 'Failed to load decision workspace')
        const normalizedDetail = detail.toLowerCase()
        if (
          normalizedDetail.includes('decision workspace unavailable') ||
          normalizedDetail.includes('unavailable in status') ||
          normalizedDetail.includes('decision submission is only allowed') ||
          normalizedDetail.includes('forbidden by journal scope') ||
          normalizedDetail.includes('insufficient permission for action')
        ) {
          toast.info('稿件已离开决策阶段，已返回详情页。')
          router.replace(`/editor/manuscript/${encodeURIComponent(manuscriptId)}`)
          return
        }
        throw new Error(detail)
      }
      setContext(res.data as DecisionContext)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to load decision workspace')
      setContext(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!manuscriptId) return
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manuscriptId])

  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => {
      if (!dirty) return
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [dirty])

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-muted/40">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </main>
    )
  }

  if (!context) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-muted/40 px-6 text-sm text-muted-foreground">
        Decision workspace is unavailable for this manuscript.
      </main>
    )
  }

  return (
    <DecisionWorkspaceLayout
      manuscriptId={manuscriptId}
      manuscriptTitle={context.manuscript.title || 'Untitled Manuscript'}
      manuscriptStatus={context.manuscript.status}
      left={
        <div className="overflow-hidden rounded-lg border border-border bg-card">
          {context.manuscript.pdf_url ? (
            <iframe
              title="Decision Workspace PDF Preview"
              src={context.manuscript.pdf_url}
              className="h-[calc(100vh-140px)] min-h-[520px] w-full"
            />
          ) : (
            <div className="flex h-[calc(100vh-140px)] min-h-[520px] items-center justify-center text-sm text-muted-foreground">
              PDF preview is unavailable.
            </div>
          )}
        </div>
      }
      middle={<ReviewReportComparison reports={context.reports || []} />}
      right={
        <div className="space-y-3">
          {context.review_stage_exit_request?.target_stage === 'first' ? (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
              <div className="font-semibold">AE recommendation</div>
              <div className="mt-1">
                {context.review_stage_exit_request.requested_outcome
                  ? getReviewStageExitRequestedOutcomeLabel(context.review_stage_exit_request.requested_outcome)
                  : 'No recommendation recorded'}
              </div>
              {context.review_stage_exit_request.note ? (
                <div className="mt-1 text-[11px] text-amber-100/80">{context.review_stage_exit_request.note}</div>
              ) : null}
            </div>
          ) : null}
          <div className="rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-xs text-primary">
            {String(context.manuscript.status || '').toLowerCase() === 'decision'
              ? (
                  <>
                    <strong>First Decision</strong> 会执行实际处理结果；
                    <strong>Add Reviewer</strong> 会把稿件退回 <code>under_review</code>。
                  </>
                )
              : (
                  <>
                    <strong>Final Decision</strong> 会触发最终状态流转与作者通知。
                  </>
                )}
          </div>
          <DecisionEditor
            manuscriptId={manuscriptId}
            reports={context.reports || []}
            manuscriptStatus={context.manuscript.status || ''}
            initialDraft={context.draft || null}
            templateContent={context.templates?.[0]?.content || ''}
            canSubmit={Boolean(context.permissions?.can_submit)}
            canRecordFirst={Boolean((context.permissions?.can_record_first ?? true) || context.permissions?.can_submit_final)}
            canSubmitFinal={Boolean(context.permissions?.can_submit_final)}
            hasSubmittedAuthorRevision={Boolean(context.permissions?.has_submitted_author_revision)}
            finalBlockingReasons={context.permissions?.final_blocking_reasons || []}
            isReadOnly={Boolean(context.permissions?.is_read_only)}
            onDirtyChange={setDirty}
            onSubmitted={(_status) => {
              setDirty(false)
              const nextStatus = String(_status || '').toLowerCase()
              // 提交后若稿件离开 decision/decision_done，直接回详情页，避免停留在错误的工作台。
              if (nextStatus && !['decision', 'decision_done'].includes(nextStatus)) {
                router.replace(`/editor/manuscript/${encodeURIComponent(manuscriptId)}`)
                return
              }
              void load()
            }}
          />
        </div>
      }
    />
  )
}
