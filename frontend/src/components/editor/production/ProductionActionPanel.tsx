'use client'

import { useMemo, useState } from 'react'
import { CheckCircle2, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import type { ProductionCycle } from '@/types/production'
import { canApproveProductionCycle } from '@/lib/production-utils'

type Props = {
  manuscriptId: string
  activeCycle: ProductionCycle | null
  canApprove: boolean
  onApproved: () => Promise<void>
}

function statusHint(status: string | undefined): string {
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

export function ProductionActionPanel({ manuscriptId, activeCycle, canApprove, onApproved }: Props) {
  const [loading, setLoading] = useState(false)

  const latest = useMemo(() => activeCycle?.latest_response || null, [activeCycle])
  const correctionItems = useMemo(() => latest?.corrections || [], [latest?.corrections])

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

  return (
    <section className="space-y-3">
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-bold uppercase tracking-wide text-slate-700">Action Panel</h2>
        <p className="mt-1 text-xs text-slate-500">发布前核准与最新作者反馈摘要。</p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
        <div className="text-sm text-slate-900 font-semibold">Current Action State</div>
        <p className="text-xs text-slate-600">{statusHint(activeCycle?.status)}</p>

        {latest ? (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 space-y-1">
            <p className="font-semibold uppercase tracking-wide text-slate-600">Latest Proofreading</p>
            <p>Decision: {latest.decision}</p>
            <p>Submitted: {latest.submitted_at ? new Date(latest.submitted_at).toLocaleString() : '--'}</p>
            {latest.summary ? <p>Summary: {latest.summary}</p> : null}
            {latest.decision === 'submit_corrections' ? (
              <>
                <p>Corrections: {correctionItems.length}</p>
                {correctionItems.length > 0 ? (
                  <div className="mt-2 space-y-2">
                    {correctionItems.map((item, idx) => (
                      <div key={`${item.id || idx}`} className="rounded border border-slate-200 bg-white p-2 text-[11px] text-slate-700">
                        <p className="font-semibold text-slate-600">Item #{idx + 1}</p>
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
          <p className="text-xs text-slate-500">暂无作者反馈。</p>
        )}

        <button
          type="button"
          onClick={() => void handleApprove()}
          disabled={loading || !activeCycle || !canApprove || !canApproveProductionCycle(activeCycle.status)}
          className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-emerald-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
          Approve for Publication
        </button>
      </div>
    </section>
  )
}
