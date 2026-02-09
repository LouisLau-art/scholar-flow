'use client'

import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { ProcessFilterBar } from '@/components/editor/ProcessFilterBar'
import { ManuscriptTable, type ProcessRow } from '@/components/editor/ManuscriptTable'
import { EditorApi, type ManuscriptsProcessFilters } from '@/services/editorApi'
import { Loader2 } from 'lucide-react'
import type { EditorRbacContext } from '@/types/rbac'
import { buildProcessScopeEmptyHint, deriveEditorCapability } from '@/lib/rbac'

export function ManuscriptsProcessPanel({
  onAssign,
  onDecide,
  refreshKey,
}: {
  onAssign: (row: ProcessRow) => void
  onDecide: (row: ProcessRow) => void
  refreshKey?: number
}) {
  const searchParams = useSearchParams()
  const filters: ManuscriptsProcessFilters = useMemo(() => {
    const q = (searchParams?.get('q') || '').trim() || undefined
    const journalId = searchParams?.get('journal_id') || undefined
    const editorId = searchParams?.get('editor_id') || undefined
    const overdueOnly = ['1', 'true', 'yes', 'on'].includes((searchParams?.get('overdue_only') || '').toLowerCase())
    const rawStatuses = searchParams?.getAll('status') || []
    const statuses =
      rawStatuses.length === 1 && rawStatuses[0]?.includes(',')
        ? rawStatuses[0].split(',').map((s) => s.trim()).filter(Boolean)
        : rawStatuses
    return {
      q,
      journalId,
      editorId,
      statuses: statuses.length ? statuses : undefined,
      overdueOnly,
    }
  }, [searchParams])
  const filtersKey = useMemo(() => JSON.stringify(filters), [filters])
  const [rows, setRows] = useState<ProcessRow[]>([])
  const [loading, setLoading] = useState(false)
  const [rbacContext, setRbacContext] = useState<EditorRbacContext | null>(null)
  const capability = useMemo(() => deriveEditorCapability(rbacContext), [rbacContext])
  const scopeHint = useMemo(() => buildProcessScopeEmptyHint(rbacContext), [rbacContext])
  const emptyText =
    scopeHint && rows.length === 0
      ? 'No manuscript in your assigned journal scope.'
      : 'No manuscripts found.'

  async function load(nextFilters: ManuscriptsProcessFilters) {
    try {
      setLoading(true)
      const res = await EditorApi.getManuscriptsProcess(nextFilters)
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || 'Failed to load manuscripts')
      }
      setRows(res.data || [])
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to load manuscripts')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load(filters)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey, filtersKey])

  useEffect(() => {
    let alive = true
    async function loadRbac() {
      try {
        const res = await EditorApi.getRbacContext()
        if (!alive) return
        if (res?.success && res?.data) {
          setRbacContext(res.data)
          return
        }
        setRbacContext(null)
      } catch {
        if (alive) setRbacContext(null)
      }
    }
    loadRbac()
    return () => {
      alive = false
    }
  }, [])

  function applyRowUpdate(updated: { id: string; status?: string; updated_at?: string }) {
    setRows((prev) => {
      const next = prev.map((r) =>
        r.id === updated.id ? { ...r, status: updated.status ?? r.status, updated_at: updated.updated_at ?? r.updated_at } : r
      )
      if (filters.statuses?.length && updated.status && !filters.statuses.includes(updated.status)) {
        return next.filter((r) => r.id !== updated.id)
      }
      return next
    })
  }

  return (
    <div className="space-y-4">
      <ProcessFilterBar />
      {scopeHint ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          {scopeHint}
        </div>
      ) : null}

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-sm text-slate-500 flex items-center justify-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      ) : (
        <ManuscriptTable
          rows={rows}
          emptyText={emptyText}
          onAssign={onAssign}
          onDecide={onDecide}
          onOwnerBound={() => load(filters)}
          canBindOwner={capability.canBindOwner}
          canAssign={capability.canViewProcess}
          canDecide={capability.canRecordFirstDecision || capability.canSubmitFinalDecision}
          canQuickPrecheck={capability.canRecordFirstDecision}
          onRowUpdated={(u) => {
            applyRowUpdate(u)
            // 轻量“后台同步”：避免本地状态与服务端过滤/排序偏离
            load(filters)
          }}
        />
      )}
    </div>
  )
}
