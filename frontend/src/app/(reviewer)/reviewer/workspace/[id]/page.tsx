'use client'

import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { ActionPanel } from './action-panel'
import { PDFViewer } from './pdf-viewer'
import type { WorkspaceData } from '@/types/review'

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

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <header className="mb-4">
        <h1 className="text-2xl font-semibold text-slate-900">{workspace.manuscript.title}</h1>
        {workspace.manuscript.abstract ? (
          <p className="mt-1 line-clamp-2 text-sm text-slate-600">{workspace.manuscript.abstract}</p>
        ) : null}
      </header>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <PDFViewer pdfUrl={workspace.manuscript.pdf_url} isLoading={false} />
        <ActionPanel
          assignmentId={assignmentId}
          workspace={workspace}
          onDirtyChange={setIsDirty}
          onSubmitted={() => {
            setWorkspace((prev) =>
              prev
                ? {
                    ...prev,
                    permissions: { ...prev.permissions, is_read_only: true, can_submit: false },
                    review_report: { ...prev.review_report, status: 'completed' },
                  }
                : prev
            )
          }}
        />
      </div>
    </main>
  )
}
