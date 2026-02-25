'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { DatePicker } from '@/components/ui/date-picker'
import { Label } from '@/components/ui/label'

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
    <div className="rounded-lg border border-border bg-card p-4">
      <h2 className="text-base font-semibold text-foreground">Accept Invitation</h2>
      <p className="mt-1 text-sm text-muted-foreground">Pick a due date before entering the review workspace.</p>
      <Label className="mt-4 block text-sm font-medium text-foreground">Due date</Label>
      <DatePicker value={dueDate} minDate={minDueDate} maxDate={maxDueDate} onChange={setDueDate} className="mt-1" />
      <p className="mt-1 text-xs text-muted-foreground">
        Allowed window: {minDueDate} to {maxDueDate}
      </p>
      {error ? <p className="mt-2 text-sm text-rose-600">{error}</p> : null}
      <Button
        type="button"
        disabled={submitting}
        onClick={() => void handleAccept()}
        className="mt-4 w-full"
      >
        {submitting ? 'Accepting...' : 'Accept & Continue'}
      </Button>
    </div>
  )
}
