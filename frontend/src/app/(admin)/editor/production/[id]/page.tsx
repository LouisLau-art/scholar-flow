'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import { ProductionWorkspacePanel } from '@/components/editor/production/ProductionWorkspacePanel'
import { ProductionActionPanel } from '@/components/editor/production/ProductionActionPanel'
import { ProductionTimeline } from '@/components/editor/production/ProductionTimeline'
import type { ProductionWorkspaceContext } from '@/types/production'

type StaffOption = {
  id: string
  name: string
  email?: string | null
  roles?: string[] | null
}

export default function EditorProductionWorkspacePage() {
  const params = useParams()
  const manuscriptId = String((params as Record<string, string>)?.id || '')

  const [loading, setLoading] = useState(true)
  const [context, setContext] = useState<ProductionWorkspaceContext | null>(null)
  const [staff, setStaff] = useState<StaffOption[]>([])

  const load = async () => {
    setLoading(true)
    try {
      const [ctxRes, staffRes] = await Promise.all([
        EditorApi.getProductionWorkspaceContext(manuscriptId),
        EditorApi.listInternalStaff(''),
      ])

      if (!ctxRes?.success || !ctxRes?.data) {
        throw new Error(ctxRes?.detail || ctxRes?.message || 'Failed to load production workspace')
      }

      const staffRows = (staffRes?.data || []) as Array<Record<string, any>>
      const options: StaffOption[] = staffRows.map((item) => ({
        id: String(item.id || ''),
        name: String(item.full_name || item.name || item.email || item.id || ''),
        email: item.email ? String(item.email) : null,
        roles: Array.isArray(item.roles) ? (item.roles as string[]) : null,
      }))

      setContext(ctxRes.data as ProductionWorkspaceContext)
      setStaff(options)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to load production workspace')
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

  const previewUrl = useMemo(() => {
    if (!context) return null
    return context.active_cycle?.galley_signed_url || context.manuscript.pdf_url || null
  }, [context])

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
        Production workspace is unavailable for this manuscript.
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur sm:px-6">
        <div className="mx-auto flex max-w-[1700px] items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Production Pipeline Workspace</p>
            <h1 className="truncate text-lg font-semibold text-slate-900 sm:text-xl">{context.manuscript.title || 'Untitled Manuscript'}</h1>
            <p className="text-xs text-slate-500">Current status: {context.manuscript.status || '--'}</p>
          </div>
          <Link
            href={`/editor/manuscript/${encodeURIComponent(manuscriptId)}`}
            className="inline-flex shrink-0 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            <ArrowLeft className="h-4 w-4" />
            返回稿件详情
          </Link>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1700px] grid-cols-1 gap-4 px-4 py-4 md:grid-cols-12 sm:px-6">
        <section className="md:col-span-5 lg:col-span-5">
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            {previewUrl ? (
              <iframe
                title="Production Workspace PDF Preview"
                src={previewUrl}
                className="h-[calc(100vh-140px)] min-h-[520px] w-full"
              />
            ) : (
              <div className="flex h-[calc(100vh-140px)] min-h-[520px] items-center justify-center text-sm text-slate-500">
                PDF preview is unavailable.
              </div>
            )}
          </div>
        </section>

        <section className="space-y-3 md:col-span-4 lg:col-span-4">
          <ProductionTimeline cycles={context.cycle_history || []} />
        </section>

        <section className="space-y-3 md:col-span-3 lg:col-span-3">
          <ProductionWorkspacePanel manuscriptId={manuscriptId} context={context} staff={staff} onReload={load} />
          <ProductionActionPanel
            manuscriptId={manuscriptId}
            activeCycle={context.active_cycle || null}
            canApprove={Boolean(context.permissions?.can_approve)}
            onApproved={load}
          />
        </section>
      </div>
    </main>
  )
}
