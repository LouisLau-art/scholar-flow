'use client'

import type { ProductionCycle } from '@/types/production'
import { sortCyclesByNewest } from '@/lib/production-utils'

type Props = {
  cycles: ProductionCycle[]
}

function formatTime(raw: string | null | undefined): string {
  if (!raw) return '--'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return '--'
  return d.toLocaleString()
}

export function ProductionTimeline({ cycles }: Props) {
  const ordered = sortCyclesByNewest(cycles)

  if (!ordered.length) {
    return (
      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">Production Timeline</h2>
        <p className="mt-2 text-sm text-muted-foreground">No production history yet.</p>
      </section>
    )
  }

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <h2 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">Production Timeline</h2>
      <p className="mt-1 text-xs text-muted-foreground">轮次历史按时间倒序展示。</p>

      <ol className="mt-4 space-y-3">
        {ordered.map((cycle) => (
          <li key={cycle.id} className="rounded-md border border-border bg-muted/50 p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-semibold text-foreground">Cycle #{cycle.cycle_no}</p>
              <span className="rounded-full bg-card px-2 py-1 text-xs font-semibold text-foreground">{cycle.status}</span>
            </div>

            <div className="mt-2 grid grid-cols-1 gap-1 text-xs text-muted-foreground sm:grid-cols-2">
              <p>Created: {formatTime(cycle.created_at)}</p>
              <p>Updated: {formatTime(cycle.updated_at)}</p>
              <p>Due: {formatTime(cycle.proof_due_at)}</p>
              <p>Approved: {formatTime(cycle.approved_at)}</p>
            </div>

            {cycle.version_note ? (
              <p className="mt-2 text-xs text-foreground">
                <span className="font-semibold text-muted-foreground">Version Note:</span> {cycle.version_note}
              </p>
            ) : null}

            {cycle.latest_response ? (
              <div className="mt-2 rounded border border-border bg-card p-2 text-xs text-foreground">
                <p className="font-semibold text-muted-foreground">Latest Response</p>
                <p>Decision: {cycle.latest_response.decision}</p>
                <p>Submitted: {formatTime(cycle.latest_response.submitted_at || null)}</p>
                {cycle.latest_response.summary ? <p>Summary: {cycle.latest_response.summary}</p> : null}
                {cycle.latest_response.decision === 'submit_corrections' ? (
                  <p>Corrections: {(cycle.latest_response.corrections || []).length}</p>
                ) : null}
              </div>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  )
}
