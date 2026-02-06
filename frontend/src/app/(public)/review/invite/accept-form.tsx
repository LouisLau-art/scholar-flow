'use client'

import { useState } from 'react'

type AcceptFormProps = {
  assignmentId: string
  defaultDueDate: string
  minDueDate: string
  maxDueDate: string
  onAccepted: () => void
}

export function AcceptForm({
  assignmentId,
  defaultDueDate,
  minDueDate,
  maxDueDate,
  onAccepted,
}: AcceptFormProps) {
  const [dueDate, setDueDate] = useState(defaultDueDate)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleAccept = async () => {
    setError(null)
    setSubmitting(true)
    try {
      const res = await fetch(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/accept`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ due_date: dueDate }),
      })
      const json = await res.json().catch(() => null)
      if (!res.ok || !json?.success) {
        throw new Error(json?.detail || json?.message || 'Failed to accept invitation')
      }
      onAccepted()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to accept invitation')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-base font-semibold text-slate-900">Accept Invitation</h2>
      <p className="mt-1 text-sm text-slate-600">Pick a due date before entering the review workspace.</p>
      <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="due_date">
        Due date
      </label>
      <input
        id="due_date"
        type="date"
        value={dueDate}
        min={minDueDate}
        max={maxDueDate}
        onChange={(e) => setDueDate(e.target.value)}
        className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
      />
      <p className="mt-1 text-xs text-slate-500">
        Allowed window: {minDueDate} to {maxDueDate}
      </p>
      {error ? <p className="mt-2 text-sm text-rose-600">{error}</p> : null}
      <button
        type="button"
        disabled={submitting}
        onClick={() => void handleAccept()}
        className="mt-4 w-full rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
      >
        {submitting ? 'Accepting...' : 'Accept & Continue'}
      </button>
    </div>
  )
}

