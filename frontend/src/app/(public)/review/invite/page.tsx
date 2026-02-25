'use client'

import { useCallback, useEffect, useState } from 'react'
import { Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { AcceptForm } from './accept-form'
import { DeclineForm } from './decline-form'

type InviteData = {
  assignment: {
    assignment_id: string
    status: 'invited' | 'accepted' | 'declined' | 'submitted' | string
    due_at: string | null
    decline_reason: string | null
    decline_note: string | null
    timeline: {
      invited_at: string | null
      opened_at: string | null
      accepted_at: string | null
      declined_at: string | null
      submitted_at: string | null
    }
  }
  manuscript: {
    id: string
    title: string
    abstract: string | null
  }
  window: {
    min_due_date: string
    max_due_date: string
    default_due_date: string
  }
  can_open_workspace: boolean
}

function formatDateTime(raw: string | null | undefined) {
  if (!raw) return '-'
  try {
    return new Date(raw).toLocaleString()
  } catch {
    return raw
  }
}

function InviteLoadingFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
      <div className="text-center">
        <div className="text-sm font-semibold text-foreground">Loading…</div>
        <div className="mt-2 text-sm text-muted-foreground">Checking your invitation status.</div>
      </div>
    </div>
  )
}

function ReviewInvitePageInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const assignmentId = searchParams?.get('assignment_id') || ''

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<InviteData | null>(null)

  const loadInvite = useCallback(async () => {
    if (!assignmentId) {
      setError('Missing assignment id in invite link.')
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/invite`)
      const json = await res.json().catch(() => null)
      if (!res.ok || !json?.success || !json?.data) {
        throw new Error(json?.detail || json?.message || 'Failed to load invitation')
      }
      setData(json.data as InviteData)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load invitation')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [assignmentId])

  useEffect(() => {
    void loadInvite()
  }, [loadInvite])

  const openWorkspace = () => {
    if (!assignmentId) return
    router.push(`/reviewer/workspace/${encodeURIComponent(assignmentId)}`)
  }

  if (loading) {
    return <InviteLoadingFallback />
  }

  if (error || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
        <div className="max-w-md rounded-lg border border-destructive/30 bg-card p-6 text-center">
          <h1 className="text-lg font-semibold text-foreground">Invitation unavailable</h1>
          <p className="mt-2 text-sm text-destructive">{error || 'This invitation cannot be opened.'}</p>
        </div>
      </div>
    )
  }

  const state = String(data.assignment.status || 'invited').toLowerCase()
  const canOpenWorkspace = data.can_open_workspace || state === 'submitted'

  return (
    <main className="min-h-screen bg-muted/30 px-4 py-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <section className="rounded-lg border border-border bg-card p-6">
          <h1 className="text-xl font-semibold text-foreground">{data.manuscript.title}</h1>
          {data.manuscript.abstract ? <p className="mt-2 text-sm text-muted-foreground">{data.manuscript.abstract}</p> : null}
          <div className="mt-4 inline-flex rounded-full bg-muted px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Status: {state}
          </div>
          {state === 'declined' ? (
            <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              You declined this invitation{data.assignment.decline_reason ? ` (${data.assignment.decline_reason})` : ''}.
            </div>
          ) : null}
        </section>

        <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-border bg-card p-4">
            <h2 className="text-base font-semibold text-foreground">Timeline</h2>
            <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
              <li>Invited: {formatDateTime(data.assignment.timeline.invited_at)}</li>
              <li>Opened: {formatDateTime(data.assignment.timeline.opened_at)}</li>
              <li>Accepted: {formatDateTime(data.assignment.timeline.accepted_at)}</li>
              <li>Declined: {formatDateTime(data.assignment.timeline.declined_at)}</li>
              <li>Submitted: {formatDateTime(data.assignment.timeline.submitted_at)}</li>
              <li>Due at: {formatDateTime(data.assignment.due_at)}</li>
            </ul>
          </div>

          {state === 'invited' ? (
            <div className="space-y-4">
              <AcceptForm
                assignmentId={assignmentId}
                minDueDate={data.window.min_due_date}
                maxDueDate={data.window.max_due_date}
                defaultDueDate={data.window.default_due_date}
                onAccepted={openWorkspace}
              />
              <DeclineForm assignmentId={assignmentId} onDeclined={() => void loadInvite()} />
            </div>
          ) : (
            <div className="rounded-lg border border-border bg-card p-4">
              <h2 className="text-base font-semibold text-foreground">Next Step</h2>
              {canOpenWorkspace ? (
                <>
                  <p className="mt-2 text-sm text-muted-foreground">Your invitation is active. Continue to the review workspace.</p>
                  <button
                    type="button"
                    onClick={openWorkspace}
                    className="mt-4 w-full rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
                  >
                    Open Review Workspace
                  </button>
                </>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">No further action available for this invitation.</p>
              )}
            </div>
          )}
        </section>
      </div>
    </main>
  )
}

export default function ReviewInvitePage() {
  return (
    <Suspense fallback={<InviteLoadingFallback />}>
      <ReviewInvitePageInner />
    </Suspense>
  )
}
