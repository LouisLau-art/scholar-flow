import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, GraduationCap } from 'lucide-react'
import SiteHeader from '@/components/layout/SiteHeader'
import QueryProvider from '@/components/providers/QueryProvider'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { editorService } from '@/services/editorService'
import { EditorApi } from '@/services/editorApi'
import { AcademicCheckModal } from '@/components/AcademicCheckModal'
import { buildProcessScopeEmptyHint } from '@/lib/rbac'
import type { EditorRbacContext } from '@/types/rbac'

interface Manuscript {
  id: string
  title: string
  status?: string
  pre_check_status?: string
  journal?: { title?: string | null } | null
  updated_at?: string | null
  latest_first_decision_draft?: {
    id?: string
    decision?: string
    updated_at?: string
  } | null
}

export default function EICAcademicQueuePage() {
  const [academicManuscripts, setAcademicManuscripts] = useState<Manuscript[]>([])
  const [finalDecisionManuscripts, setFinalDecisionManuscripts] = useState<Manuscript[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [rbacContext, setRbacContext] = useState<EditorRbacContext | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedManuscriptId, setSelectedManuscriptId] = useState<string | null>(null)

  const scopeHint = useMemo(() => buildProcessScopeEmptyHint(rbacContext), [rbacContext])

  const fetchQueue = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [academicRows, finalRows] = await Promise.all([
        editorService.getAcademicQueue(),
        editorService.getFinalDecisionQueue(),
      ])
      setAcademicManuscripts(academicRows as unknown as Manuscript[])
      setFinalDecisionManuscripts(finalRows as unknown as Manuscript[])
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err.message : 'Failed to fetch academic queue')
      setAcademicManuscripts([])
      setFinalDecisionManuscripts([])
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchRbacContext = useCallback(async () => {
    try {
      const res = await EditorApi.getRbacContext()
      if (res?.success && res?.data) {
        setRbacContext(res.data)
        return
      }
      setRbacContext(null)
    } catch {
      setRbacContext(null)
    }
  }, [])

  useEffect(() => {
    fetchQueue()
    fetchRbacContext()
  }, [fetchQueue, fetchRbacContext])

  const openDecisionModal = (id: string) => {
    setSelectedManuscriptId(id)
    setModalOpen(true)
  }

  return (
    <QueryProvider>
      <div className="min-h-screen bg-slate-50">
        <SiteHeader />
        <main className="mx-auto w-[96vw] max-w-screen-2xl px-4 py-10 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="mt-1 rounded-xl bg-white p-2 shadow-sm ring-1 ring-slate-200">
              <GraduationCap className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-bold text-slate-900 tracking-tight">Editor-in-Chief Workspace</h1>
              <p className="mt-1 text-slate-500 font-medium">Editor-in-Chief workspace for optional academic pre-check and final decision handoff.</p>
            </div>
          </div>

          <Link href="/dashboard?tab=editor_in_chief" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
            <ArrowLeft className="h-4 w-4" />
            返回编辑台
          </Link>
        </div>

        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          {scopeHint ? (
            <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800">{scopeHint}</div>
          ) : null}
          {error ? (
            <div className="border-b border-rose-200 bg-rose-50 px-4 py-2 text-xs text-rose-700">{error}</div>
          ) : null}
          <div className="border-b border-slate-200 bg-slate-50/70 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-900">Academic Review Queue (Optional)</h2>
            <p className="mt-1 text-xs text-slate-500">仅展示 AE 主动送到 academic 的稿件；可继续送外审或转入决策阶段。</p>
          </div>
          <table className="w-full table-fixed">
            <thead className="bg-slate-50/70">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Title</th>
                <th className="w-56 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Journal</th>
                <th className="w-40 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Status</th>
                <th className="w-44 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Updated</th>
                <th className="w-32 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-sm text-slate-500">Loading...</td>
                </tr>
              ) : academicManuscripts.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-sm text-slate-500">
                    {scopeHint ? 'No manuscript in your assigned journal scope.' : 'No manuscripts awaiting academic check.'}
                  </td>
                </tr>
              ) : (
                academicManuscripts.map((m) => (
                  <tr key={m.id} className="border-t border-slate-100 hover:bg-slate-50/60">
                    <td className="px-4 py-3 text-sm text-slate-900">{m.title}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{m.journal?.title || '—'}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{m.pre_check_status}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{m.updated_at ? new Date(m.updated_at).toLocaleString() : '—'}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => openDecisionModal(m.id)}
                        className="rounded-md border border-violet-200 bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-700 hover:bg-violet-100"
                      >
                        Make Decision
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 bg-slate-50/70 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-900">Final Decision Queue</h2>
            <p className="mt-1 text-xs text-slate-500">终审稿件（decision/decision_done）+ 已有 first decision 草稿的稿件，可直接进入 Decision Workspace。</p>
          </div>
          <table className="w-full table-fixed">
            <thead className="bg-slate-50/70">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Title</th>
                <th className="w-40 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Status</th>
                <th className="w-56 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Latest First Draft</th>
                <th className="w-44 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Updated</th>
                <th className="w-40 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-sm text-slate-500">Loading...</td>
                </tr>
              ) : finalDecisionManuscripts.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-sm text-slate-500">
                    {scopeHint ? 'No final-decision manuscript in your assigned journal scope.' : 'No manuscripts awaiting final decision.'}
                  </td>
                </tr>
              ) : (
                finalDecisionManuscripts.map((m) => (
                  <tr key={m.id} className="border-t border-slate-100 hover:bg-slate-50/60">
                    <td className="px-4 py-3 text-sm text-slate-900">{m.title}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{m.status || '—'}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      {m.latest_first_decision_draft?.decision ? (
                        <div>
                          <div className="font-medium text-slate-800">{m.latest_first_decision_draft.decision}</div>
                          <div className="text-xs text-slate-500">
                            {m.latest_first_decision_draft.updated_at
                              ? new Date(m.latest_first_decision_draft.updated_at).toLocaleString()
                              : '—'}
                          </div>
                        </div>
                      ) : (
                        'No draft'
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">{m.updated_at ? new Date(m.updated_at).toLocaleString() : '—'}</td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/editor/decision/${encodeURIComponent(m.id)}`}
                        className="inline-flex items-center rounded-md border border-violet-200 bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-700 hover:bg-violet-100"
                      >
                        Open Decision Workspace
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {selectedManuscriptId && (
          <AcademicCheckModal
            isOpen={modalOpen}
            onClose={() => setModalOpen(false)}
            manuscriptId={selectedManuscriptId}
            onSuccess={fetchQueue}
          />
        )}
        </main>
      </div>
    </QueryProvider>
  )
}
