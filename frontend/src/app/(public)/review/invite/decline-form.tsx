'use client'

import { useState } from 'react'

const DECLINE_REASONS = [
  { value: 'out_of_scope', label: 'Out of scope' },
  { value: 'conflict_of_interest', label: 'Conflict of interest' },
  { value: 'too_busy', label: 'Too busy' },
  { value: 'insufficient_expertise', label: 'Insufficient expertise' },
  { value: 'other', label: 'Other' },
]

type DeclineFormProps = {
  assignmentId: string
  onDeclined: () => void
}

export function DeclineForm({ assignmentId, onDeclined }: DeclineFormProps) {
  const [reason, setReason] = useState<string>('too_busy')
  const [note, setNote] = useState<string>('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDecline = async () => {
    setError(null)
    setSubmitting(true)
    try {
      const res = await fetch(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/decline`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ reason, note }),
      })
      const json = await res.json().catch(() => null)
      if (!res.ok || !json?.success) {
        throw new Error(json?.detail || json?.message || 'Failed to decline invitation')
      }
      onDeclined()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to decline invitation')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-base font-semibold text-slate-900">Decline Invitation</h2>
      <p className="mt-1 text-sm text-slate-600">Declining is final for this invitation.</p>
      <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="decline_reason">
        Reason
      </label>
      <select
        id="decline_reason"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
      >
        {DECLINE_REASONS.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </select>
      <label className="mt-3 block text-sm font-medium text-slate-700" htmlFor="decline_note">
        Note (optional)
      </label>
      <textarea
        id="decline_note"
        rows={3}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
      />
      {error ? <p className="mt-2 text-sm text-rose-600">{error}</p> : null}
      <button
        type="button"
        disabled={submitting}
        onClick={() => void handleDecline()}
        className="mt-4 w-full rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700 disabled:opacity-60"
      >
        {submitting ? 'Declining...' : 'Decline Invitation'}
      </button>
    </div>
  )
}

