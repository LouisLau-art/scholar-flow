'use client'

import { useCallback, useEffect, useState } from 'react'
import { Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Badge } from '@/components/ui/badge'
import { ManuscriptPdfPreview } from '@/components/reviewer/ManuscriptPdfPreview'
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
    journal_title: string | null
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
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)

  const loadInvite = useCallback(async () => {
    if (!assignmentId) {
      setError('Missing assignment id in invite link.')
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    setPdfLoading(true)
    try {
      const [res, pdfRes] = await Promise.all([
        fetch(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/invite`),
        fetch(`/api/v1/reviews/magic/assignments/${encodeURIComponent(assignmentId)}/pdf-signed`),
      ])
      const json = await res.json().catch(() => null)
      if (!res.ok || !json?.success || !json?.data) {
        throw new Error(json?.detail || json?.message || 'Failed to load invitation')
      }
      setData(json.data as InviteData)

      const pdfJson = await pdfRes.json().catch(() => null)
      if (pdfRes.ok && pdfJson?.success && pdfJson?.data?.signed_url) {
        setPdfUrl(String(pdfJson.data.signed_url))
      } else {
        setPdfUrl(null)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load invitation')
      setData(null)
      setPdfUrl(null)
    } finally {
      setLoading(false)
      setPdfLoading(false)
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
  const showDecisionSurface = state === 'invited' || state === 'opened'

  return (
    <main className="min-h-screen bg-muted/30 px-4 py-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <section className="rounded-lg border border-border bg-card p-6">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold text-foreground">{data.manuscript.title}</h1>
            <Badge variant="secondary">{state}</Badge>
            {data.manuscript.journal_title ? (
              <Badge variant="outline">{data.manuscript.journal_title}</Badge>
            ) : null}
          </div>
          {data.manuscript.abstract ? <p className="mt-2 text-sm text-muted-foreground">{data.manuscript.abstract}</p> : null}
          <div className="mt-4 grid gap-3 text-sm text-muted-foreground md:grid-cols-3">
            <div className="rounded-md border border-border bg-muted/40 px-3 py-2">
              <div className="text-xs uppercase tracking-wide">Journal</div>
              <div className="mt-1 font-medium text-foreground">{data.manuscript.journal_title || 'Unassigned journal'}</div>
            </div>
            <div className="rounded-md border border-border bg-muted/40 px-3 py-2">
              <div className="text-xs uppercase tracking-wide">Invitation Status</div>
              <div className="mt-1 font-medium capitalize text-foreground">{state}</div>
            </div>
            <div className="rounded-md border border-border bg-muted/40 px-3 py-2">
              <div className="text-xs uppercase tracking-wide">Current Due Date</div>
              <div className="mt-1 font-medium text-foreground">{formatDateTime(data.assignment.due_at)}</div>
            </div>
          </div>
          {state === 'declined' ? (
            <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              You declined this invitation{data.assignment.decline_reason ? ` (${data.assignment.decline_reason})` : ''}.
            </div>
          ) : null}
        </section>

        <section className="grid grid-cols-1 gap-4 lg:grid-cols-[1.1fr_0.9fr]">
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
            {showDecisionSurface ? (
              <div className="mt-4 rounded-md border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
                Review the manuscript preview below before deciding. If you accept, you will choose a due date and continue directly to the reviewer workspace.
              </div>
            ) : null}
          </div>

          {showDecisionSurface ? (
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

        <section>
          <ManuscriptPdfPreview pdfUrl={pdfUrl} isLoading={pdfLoading} />
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
