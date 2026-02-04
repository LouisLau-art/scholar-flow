'use client'

import { useEffect, useState } from 'react'
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
  const [filters, setFilters] = useState<ManuscriptsProcessFilters>({})
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
  }, [refreshKey])

  return (
    <div className="space-y-4">
      <ProcessFilterBar
        initial={filters}
        onSearch={(f) => {
          setFilters(f)
          load(f)
        }}
      />

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
        />
      )}
    </div>
  )
}
