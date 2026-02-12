'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import { DecisionWorkspaceLayout } from '@/components/editor/decision/DecisionWorkspaceLayout'
import { ReviewReportComparison } from '@/components/editor/decision/ReviewReportComparison'
import { DecisionEditor } from '@/components/editor/decision/DecisionEditor'
import type { DecisionContext } from '@/types/decision'

export default function DecisionWorkspacePage() {
  const params = useParams()
  const manuscriptId = String((params as Record<string, string>)?.id || '')
  const [context, setContext] = useState<DecisionContext | null>(null)
  const [loading, setLoading] = useState(true)
  const [dirty, setDirty] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res = await EditorApi.getDecisionContext(manuscriptId)
      if (!res?.success || !res?.data) {
        throw new Error(res?.detail || res?.message || 'Failed to load decision workspace')
      }
      setContext(res.data as DecisionContext)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to load decision workspace')
      setContext(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!manuscriptId) return
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manuscriptId])

  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => {
      if (!dirty) return
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [dirty])

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100">
        <Loader2 className="h-6 w-6 animate-spin text-slate-600" />
      </main>
    )
  }

  if (!context) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6 text-sm text-slate-600">
        Decision workspace is unavailable for this manuscript.
      </main>
    )
  }

  return (
    <DecisionWorkspaceLayout
      manuscriptId={manuscriptId}
      manuscriptTitle={context.manuscript.title || 'Untitled Manuscript'}
      manuscriptStatus={context.manuscript.status}
      left={
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          {context.manuscript.pdf_url ? (
            <iframe
              title="Decision Workspace PDF Preview"
              src={context.manuscript.pdf_url}
              className="h-[calc(100vh-140px)] min-h-[520px] w-full"
            />
          ) : (
            <div className="flex h-[calc(100vh-140px)] min-h-[520px] items-center justify-center text-sm text-slate-500">
              PDF preview is unavailable.
            </div>
          )}
        </div>
      }
      middle={<ReviewReportComparison reports={context.reports || []} />}
      right={
        <div className="space-y-3">
          <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-900">
            <strong>First Decision</strong> 仅保存建议草稿；<strong>Final Decision</strong> 才会触发状态流转与作者通知。
          </div>
          <DecisionEditor
            manuscriptId={manuscriptId}
            reports={context.reports || []}
            manuscriptStatus={context.manuscript.status || ''}
            initialDraft={context.draft || null}
            templateContent={context.templates?.[0]?.content || ''}
            canSubmit={Boolean(context.permissions?.can_submit)}
            canRecordFirst={Boolean(context.permissions?.can_record_first ?? true)}
            canSubmitFinal={Boolean(context.permissions?.can_submit_final)}
            hasSubmittedAuthorRevision={Boolean(context.permissions?.has_submitted_author_revision)}
            finalBlockingReasons={context.permissions?.final_blocking_reasons || []}
            isReadOnly={Boolean(context.permissions?.is_read_only)}
            onDirtyChange={setDirty}
            onSubmitted={(_status) => {
              setDirty(false)
              void load()
            }}
          />
        </div>
      }
    />
  )
}
