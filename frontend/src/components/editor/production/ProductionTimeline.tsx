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
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-bold uppercase tracking-wide text-slate-700">Production Timeline</h2>
        <p className="mt-2 text-sm text-slate-500">No production history yet.</p>
      </section>
    )
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-bold uppercase tracking-wide text-slate-700">Production Timeline</h2>
      <p className="mt-1 text-xs text-slate-500">轮次历史按时间倒序展示。</p>

      <ol className="mt-4 space-y-3">
        {ordered.map((cycle) => (
          <li key={cycle.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-semibold text-slate-900">Cycle #{cycle.cycle_no}</p>
              <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold text-slate-700">{cycle.status}</span>
            </div>

            <div className="mt-2 grid grid-cols-1 gap-1 text-xs text-slate-600 sm:grid-cols-2">
              <p>Created: {formatTime(cycle.created_at)}</p>
              <p>Updated: {formatTime(cycle.updated_at)}</p>
              <p>Due: {formatTime(cycle.proof_due_at)}</p>
              <p>Approved: {formatTime(cycle.approved_at)}</p>
            </div>

            {cycle.version_note ? (
              <p className="mt-2 text-xs text-slate-700">
                <span className="font-semibold text-slate-600">Version Note:</span> {cycle.version_note}
              </p>
            ) : null}

            {cycle.latest_response ? (
              <div className="mt-2 rounded border border-slate-200 bg-white p-2 text-xs text-slate-700">
                <p className="font-semibold text-slate-600">Latest Response</p>
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
