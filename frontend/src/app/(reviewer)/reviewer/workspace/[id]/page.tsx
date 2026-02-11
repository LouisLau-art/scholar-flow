'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { format } from 'date-fns'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { buttonVariants } from '@/components/ui/button'
import { ActionPanel } from './action-panel'
import { PDFViewer } from './pdf-viewer'
import type { WorkspaceData } from '@/types/review'

function formatDateTime(value?: string | null) {
  if (!value) return '—'
  try {
    return format(new Date(value), 'yyyy-MM-dd HH:mm')
  } catch {
    return '—'
  }
}

function actorLabel(actor: string) {
  if (actor === 'reviewer') return 'You'
  if (actor === 'author') return 'Author'
  if (actor === 'editor') return 'Editor'
  return 'System'
}

function channelBadgeVariant(channel: string): 'secondary' | 'outline' | 'default' {
  if (channel === 'private') return 'default'
  if (channel === 'public') return 'secondary'
  return 'outline'
}

export default function ReviewerWorkspacePage({ params }: { params: { id: string } }) {
  const assignmentId = params.id
  const [workspace, setWorkspace] = useState<WorkspaceData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDirty, setIsDirty] = useState(false)

  const isReadOnly = useMemo(() => workspace?.permissions.is_read_only ?? false, [workspace])

  useEffect(() => {
    let mounted = true
    const load = async () => {
      setIsLoading(true)
      try {
        const res = await fetch(`/api/v1/reviewer/assignments/${encodeURIComponent(assignmentId)}/workspace`)
        const json = await res.json().catch(() => null)
        if (!res.ok || !json?.success || !json?.data) {
          throw new Error(json?.detail || json?.message || 'Failed to load workspace')
        }
        if (mounted) setWorkspace(json.data as WorkspaceData)
      } catch (error) {
        toast.error(error instanceof Error ? error.message : 'Failed to load workspace')
        if (mounted) setWorkspace(null)
      } finally {
        if (mounted) setIsLoading(false)
      }
    }
    void load()
    return () => {
      mounted = false
    }
  }, [assignmentId])

  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => {
      if (!isDirty || isReadOnly) return
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [isDirty, isReadOnly])

  if (isLoading) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <PDFViewer pdfUrl={null} isLoading />
      </main>
    )
  }

  if (!workspace) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10 text-center text-sm text-slate-600">
        Workspace is unavailable for this assignment.
      </main>
    )
  }

  const manuscript = workspace.manuscript
  const assignment = workspace.assignment || {
    id: assignmentId,
    status: workspace.review_report?.status || 'pending',
    due_at: null,
    invited_at: null,
    opened_at: null,
    accepted_at: null,
    submitted_at: null,
    decline_reason: null,
  }
  const report = workspace.review_report || {
    status: 'pending',
    comments_for_author: '',
    confidential_comments_to_editor: '',
    attachments: [],
    submitted_at: null,
  }
  const timeline = Array.isArray(workspace.timeline) ? workspace.timeline : []

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <header className="mb-5 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">{manuscript.title}</h1>
          <Badge variant="outline">Blind Review</Badge>
          <Badge variant="secondary">{String(assignment.status || 'pending')}</Badge>
          {isReadOnly ? <Badge>Submitted</Badge> : null}
        </div>
        {manuscript.abstract ? (
          <p className="mt-3 text-sm leading-6 text-slate-600">{manuscript.abstract}</p>
        ) : (
          <p className="mt-3 text-sm text-slate-500">No abstract available.</p>
        )}
        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span>Due: {formatDateTime(assignment.due_at)}</span>
          <span>Invited: {formatDateTime(assignment.invited_at)}</span>
          <span>Accepted: {formatDateTime(assignment.accepted_at)}</span>
          <span>Last submitted: {formatDateTime(report.submitted_at || assignment.submitted_at)}</span>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {manuscript.dataset_url ? (
            <a
              href={manuscript.dataset_url}
              target="_blank"
              rel="noreferrer"
              className={buttonVariants({ size: 'sm', variant: 'outline' })}
            >
              Dataset URL
            </a>
          ) : null}
          {manuscript.source_code_url ? (
            <a
              href={manuscript.source_code_url}
              target="_blank"
              rel="noreferrer"
              className={buttonVariants({ size: 'sm', variant: 'outline' })}
            >
              Source Code URL
            </a>
          ) : null}
          {manuscript.cover_letter_url ? (
            <a
              href={manuscript.cover_letter_url}
              target="_blank"
              rel="noreferrer"
              className={buttonVariants({ size: 'sm', variant: 'outline' })}
            >
              Cover Letter
            </a>
          ) : null}
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <section className="space-y-6 lg:col-span-8">
          <PDFViewer pdfUrl={manuscript.pdf_url} isLoading={false} />

          <Card className="border-slate-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">Communication Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              {timeline.length === 0 ? (
                <p className="text-sm text-slate-500">No communication records yet.</p>
              ) : (
                <div className="max-h-[460px] space-y-3 overflow-auto pr-1">
                  {timeline.map((event) => (
                    <div key={event.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <Badge variant={channelBadgeVariant(event.channel)}>{event.channel}</Badge>
                          <span className="text-xs font-medium text-slate-700">{actorLabel(event.actor)}</span>
                        </div>
                        <span className="text-xs text-slate-500">{formatDateTime(event.timestamp)}</span>
                      </div>
                      <div className="mt-2 text-sm font-semibold text-slate-900">{event.title}</div>
                      {event.message ? (
                        <div className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                          {event.message}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </section>

        <section className="space-y-6 lg:col-span-4">
          <ActionPanel
            assignmentId={assignmentId}
            workspace={workspace}
            onDirtyChange={setIsDirty}
            onSubmitted={() => {
              setWorkspace((prev) =>
                prev
                  ? {
                      ...prev,
                      assignment: {
                        ...prev.assignment,
                        status: 'completed',
                        submitted_at: new Date().toISOString(),
                      },
                      permissions: { ...prev.permissions, is_read_only: true, can_submit: false },
                      review_report: {
                        ...prev.review_report,
                        status: 'completed',
                        submitted_at: new Date().toISOString(),
                      },
                    }
                  : prev
              )
            }}
          />

          <Card className="border-slate-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">Review Scope</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-slate-600">
              <p>You can view only this assignment and its communication records.</p>
              <p>Author identity and other reviewers’ data are hidden by policy.</p>
              <div className="pt-2">
                <Link href="/review/invite" className="text-blue-600 hover:text-blue-500">
                  Back to invite page
                </Link>
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  )
}
