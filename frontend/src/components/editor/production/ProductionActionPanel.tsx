'use client'

import { useMemo, useState } from 'react'
import { CheckCircle2, Loader2, Mail, ArrowRight } from 'lucide-react'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import type { ProductionCycle } from '@/types/production'
import { canApproveProductionCycle } from '@/lib/production-utils'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'

type Props = {
  manuscriptId: string
  manuscriptStatus?: string | null
  activeCycle: ProductionCycle | null
  canApprove: boolean
  onApproved: () => Promise<void>
  onOpenProofreadingEmail?: () => void
}

function statusHint(status: string | undefined, stage: string | undefined): string {
  if (stage) return `SOP Stage: ${stage}`
  switch (status) {
    case 'draft':
      return '请先上传清样后进入作者校对。'
    case 'awaiting_author':
      return '等待作者提交校对结果。'
    case 'author_corrections_submitted':
      return '作者已提交修正清单，建议处理后重新上传清样。'
    case 'in_layout_revision':
      return '排版修订中，完成后上传新清样。'
    case 'author_confirmed':
      return '可执行发布前核准。'
    case 'approved_for_publish':
      return '已核准，可进入发布门禁流程。'
    default:
      return '无可执行动作。'
  }
}

export function ProductionActionPanel({
  manuscriptId,
  manuscriptStatus,
  activeCycle,
  canApprove,
  onApproved,
  onOpenProofreadingEmail,
}: Props) {
  const [loading, setLoading] = useState(false)
  const [targetStage, setTargetStage] = useState<string>('')

  const latest = useMemo(() => activeCycle?.latest_response || null, [activeCycle])
  const correctionItems = useMemo(() => latest?.corrections || [], [latest?.corrections])
  const normalizedManuscriptStatus = String(manuscriptStatus || '').trim().toLowerCase()
  const canShowPublish = normalizedManuscriptStatus === 'approved_for_publish'
  const canShowApprove = Boolean(activeCycle && canApproveProductionCycle(activeCycle.status))

  const handleApprove = async () => {
    if (!activeCycle) return
    setLoading(true)
    try {
      const res = await EditorApi.approveProductionCycle(manuscriptId, activeCycle.id)
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || '核准失败')
      }
      toast.success('已核准为可发布生产版本')
      await onApproved()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '核准失败')
    } finally {
      setLoading(false)
    }
  }

  const handleTransition = async () => {
    if (!activeCycle || !targetStage) return
    setLoading(true)
    try {
      const res = await EditorApi.transitionProductionCycle(manuscriptId, activeCycle.id, { target_stage: targetStage })
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || '阶段流转失败')
      }
      toast.success('已流转到新阶段')
      setTargetStage('')
      await onApproved()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '流转失败')
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async () => {
    setLoading(true)
    try {
      const res = await EditorApi.advanceProduction(manuscriptId)
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || 'Publish failed')
      }
      toast.success('Moved to Published')
      await onApproved()
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Publish failed'
      const normalizedDetail = String(detail).toLowerCase()
      if (normalizedDetail.includes('payment required')) {
        toast.error('Waiting for Payment.')
      } else if (normalizedDetail.includes('production pdf') || normalizedDetail.includes('approval required')) {
        toast.error('Production Gate not met.')
      } else {
        toast.error(detail)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="space-y-3">
      <div className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-bold uppercase tracking-wide text-foreground">Action Panel</h2>
        <p className="mt-1 text-xs text-muted-foreground">阶段流转与核准动作。</p>
      </div>

      <div className="rounded-lg border border-border bg-card p-4 space-y-3">
        <div className="text-sm text-foreground font-semibold">Current Action State</div>
        <p className="text-xs text-muted-foreground">{statusHint(activeCycle?.status, activeCycle?.stage || undefined)}</p>

        {latest ? (
          <div className="rounded-md border border-border bg-muted/50 p-3 text-xs text-foreground space-y-1">
            <p className="font-semibold uppercase tracking-wide text-muted-foreground">Latest Proofreading</p>
            <p>Decision: {latest.decision}</p>
            <p>Submitted: {latest.submitted_at ? new Date(latest.submitted_at).toLocaleString() : '--'}</p>
            {latest.summary ? <p>Summary: {latest.summary}</p> : null}
            {latest.decision === 'submit_corrections' ? (
              <>
                <p>Corrections: {correctionItems.length}</p>
                {correctionItems.length > 0 ? (
                  <div className="mt-2 space-y-2">
                    {correctionItems.map((item, idx) => (
                      <div key={`${item.id || idx}`} className="rounded border border-border bg-card p-2 text-[11px] text-foreground">
                        <p className="font-semibold text-muted-foreground">Item #{idx + 1}</p>
                        {item.line_ref ? <p>Line Ref: {item.line_ref}</p> : null}
                        {item.original_text ? <p>Original: {item.original_text}</p> : null}
                        <p>Suggested: {item.suggested_text}</p>
                        {item.reason ? <p>Reason: {item.reason}</p> : null}
                      </div>
                    ))}
                  </div>
                ) : null}
              </>
            ) : null}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">暂无作者反馈。</p>
        )}

        {activeCycle && (
          <div className="space-y-2 pt-2 border-t border-border">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Transition Stage</p>
            <div className="flex items-center gap-2">
              <Select value={targetStage} onValueChange={setTargetStage}>
                <SelectTrigger className="h-9"><SelectValue placeholder="Select target stage" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="typesetting">Typesetting</SelectItem>
                  <SelectItem value="language_editing">Language Editing</SelectItem>
                  <SelectItem value="ae_internal_proof">AE Internal Proof</SelectItem>
                  <SelectItem value="author_proofreading">Author Proofreading</SelectItem>
                  <SelectItem value="ae_final_review">AE Final Review</SelectItem>
                  <SelectItem value="pdf_preparation">PDF Preparation</SelectItem>
                </SelectContent>
              </Select>
              <Button type="button" onClick={() => void handleTransition()} disabled={loading || !targetStage} className="h-9 px-3 gap-1">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                Move
              </Button>
            </div>
          </div>
        )}

        <div className="space-y-2 pt-2 border-t border-border">
          {activeCycle && onOpenProofreadingEmail && (
            <button
              type="button"
              onClick={onOpenProofreadingEmail}
              disabled={loading || !activeCycle}
              className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground hover:bg-muted disabled:opacity-60"
            >
              <Mail className="h-4 w-4" />
              Send Proofreading Reminder
            </button>
          )}

          {canShowApprove ? (
            <button
              type="button"
              onClick={() => void handleApprove()}
              disabled={loading || !activeCycle || !canApprove}
              className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
              Approve for Publication
            </button>
          ) : null}

          {canShowPublish ? (
            <button
              type="button"
              onClick={() => void handlePublish()}
              disabled={loading}
              className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
              Publish Manuscript
            </button>
          ) : null}
        </div>
      </div>
    </section>
  )
}
