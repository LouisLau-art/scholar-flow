'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { ProcessFilterBar } from '@/components/editor/ProcessFilterBar'
import { ManuscriptTable, type ProcessRow } from '@/components/editor/ManuscriptTable'
import { EditorApi, type ManuscriptsProcessFilters } from '@/services/editorApi'
import { Loader2 } from 'lucide-react'
import type { EditorRbacContext } from '@/types/rbac'
import { buildProcessScopeEmptyHint, deriveEditorCapability } from '@/lib/rbac'

const PROCESS_ROWS_CACHE_TTL_MS = 60_000
const RBAC_CACHE_TTL_MS = 300_000

const processRowsCache = new Map<string, { rows: ProcessRow[]; cachedAt: number }>()
let rbacContextCache: { data: EditorRbacContext | null; cachedAt: number } | null = null

export function ManuscriptsProcessPanel({
  onAssign,
  onDecide,
  refreshKey,
  viewMode = 'actionable',
}: {
  onAssign?: (row: ProcessRow) => void
  onDecide?: (row: ProcessRow) => void
  refreshKey?: number
  viewMode?: 'actionable' | 'monitor'
}) {
  const searchParams = useSearchParams()
  const searchKey = searchParams?.toString() || ''
  const filters: ManuscriptsProcessFilters = useMemo(() => {
    const parsed = new URLSearchParams(searchKey)
    const q = (parsed.get('q') || '').trim() || undefined
    const journalId = parsed.get('journal_id') || undefined
    const editorId = parsed.get('editor_id') || undefined
    const overdueOnly = ['1', 'true', 'yes', 'on'].includes((parsed.get('overdue_only') || '').toLowerCase())
    const rawStatuses = parsed.getAll('status')
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
  }, [searchKey])
  const filtersKey = useMemo(() => JSON.stringify(filters), [filters])
  const [rows, setRows] = useState<ProcessRow[]>([])
  const [loading, setLoading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [rbacContext, setRbacContext] = useState<EditorRbacContext | null>(null)
  const requestIdRef = useRef(0)
  const rowsRef = useRef<ProcessRow[]>([])
  const rbacRequestIdRef = useRef(0)

  useEffect(() => {
    rowsRef.current = rows
  }, [rows])

  const capability = useMemo(() => deriveEditorCapability(rbacContext), [rbacContext])
  const readOnlyView = viewMode === 'monitor'
  const scopeHint = useMemo(() => buildProcessScopeEmptyHint(rbacContext), [rbacContext])
  const emptyText =
    scopeHint && rows.length === 0
      ? 'No manuscript in your assigned journal scope.'
      : 'No manuscripts found.'

  async function load(
    nextFilters: ManuscriptsProcessFilters,
    options?: { preferCache?: boolean; silent?: boolean; suppressErrorToast?: boolean }
  ) {
    const key = JSON.stringify(nextFilters)
    const now = Date.now()
    const cached = processRowsCache.get(key)
    const cacheValid = Boolean(cached && now - cached.cachedAt < PROCESS_ROWS_CACHE_TTL_MS)

    if (options?.preferCache && cacheValid && cached) {
      setRows(cached.rows)
    }

    const hasVisibleRows = (cacheValid && Boolean(cached?.rows.length)) || rowsRef.current.length > 0
    const blockUi = !options?.silent && !hasVisibleRows
    if (blockUi) setLoading(true)
    else setIsRefreshing(true)

    const currentRequestId = ++requestIdRef.current
    try {
      const res = await EditorApi.getManuscriptsProcess(nextFilters)
      if (currentRequestId !== requestIdRef.current) return
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || 'Failed to load manuscripts')
      }
      const nextRows: ProcessRow[] = res.data || []
      processRowsCache.set(key, { rows: nextRows, cachedAt: Date.now() })
      setRows(nextRows)
    } catch (e) {
      if (currentRequestId !== requestIdRef.current) return
      if (!options?.suppressErrorToast) {
        toast.error(e instanceof Error ? e.message : 'Failed to load manuscripts')
      }
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setLoading(false)
        setIsRefreshing(false)
      }
    }
  }

  useEffect(() => {
    load(filters, { preferCache: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey, filtersKey])

  useEffect(() => {
    let alive = true
    const now = Date.now()
    if (rbacContextCache && now - rbacContextCache.cachedAt < RBAC_CACHE_TTL_MS) {
      setRbacContext(rbacContextCache.data)
    }

    async function loadRbac() {
      const currentRequestId = ++rbacRequestIdRef.current
      try {
        const res = await EditorApi.getRbacContext()
        if (!alive || currentRequestId !== rbacRequestIdRef.current) return
        if (res?.success && res?.data) {
          rbacContextCache = { data: res.data, cachedAt: Date.now() }
          setRbacContext(res.data)
          return
        }
        rbacContextCache = { data: null, cachedAt: Date.now() }
        setRbacContext(null)
      } catch {
        if (alive && currentRequestId === rbacRequestIdRef.current) {
          rbacContextCache = { data: null, cachedAt: Date.now() }
          setRbacContext(null)
        }
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
      <ProcessFilterBar rbacContext={rbacContext} />
      {scopeHint ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          {scopeHint}
        </div>
      ) : null}
      {isRefreshing && !loading ? (
        <div className="flex items-center justify-end gap-1 text-xs text-slate-500">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Syncing latest data...
        </div>
      ) : null}

      {loading && rows.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-sm text-slate-500 flex items-center justify-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      ) : (
        <ManuscriptTable
          rows={rows}
          emptyText={emptyText}
          onAssign={readOnlyView ? undefined : onAssign}
          onDecide={readOnlyView ? undefined : onDecide}
          onOwnerBound={() => load(filters, { silent: true })}
          canBindOwner={!readOnlyView && capability.canBindOwner}
          canAssign={!readOnlyView && capability.canViewProcess}
          canDecide={!readOnlyView && (capability.canRecordFirstDecision || capability.canSubmitFinalDecision)}
          canQuickPrecheck={!readOnlyView && capability.canRecordFirstDecision}
          readOnly={readOnlyView}
          onRowUpdated={
            readOnlyView
              ? undefined
              : (u) => {
                  applyRowUpdate(u)
                  // 轻量“后台同步”：避免本地状态与服务端过滤/排序偏离
                  load(filters, { silent: true, suppressErrorToast: true })
                }
          }
        />
      )}
    </div>
  )
}
