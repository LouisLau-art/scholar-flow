'use client'

import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { ProcessFilterBar } from '@/components/editor/ProcessFilterBar'
import { ManuscriptTable, type ProcessRow } from '@/components/editor/ManuscriptTable'
import { EditorApi, type ManuscriptsProcessFilters } from '@/services/editorApi'
import { Loader2 } from 'lucide-react'

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
    }
  }, [searchParams])
  const filtersKey = useMemo(() => JSON.stringify(filters), [filters])
  const [rows, setRows] = useState<ProcessRow[]>([])
  const [loading, setLoading] = useState(false)

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

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-sm text-slate-500 flex items-center justify-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      ) : (
        <ManuscriptTable
          rows={rows}
          onAssign={onAssign}
          onDecide={onDecide}
          onOwnerBound={() => load(filters)}
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
