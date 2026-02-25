'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { format } from 'date-fns'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { getStatusBadgeClass, getStatusLabel } from '@/lib/statusStyles'
import { BindingOwnerDropdown } from '@/components/editor/BindingOwnerDropdown'
import { ArrowRight } from 'lucide-react'
import { ManuscriptActions } from '@/components/editor/ManuscriptActions'

export type ProcessRow = {
  id: string
  title?: string
  created_at?: string
  updated_at?: string
  status?: string
  pre_check_status?: string | null
  current_role?: string | null
  current_assignee?: { id: string; full_name?: string | null; email?: string | null } | null
  assigned_at?: string | null
  technical_completed_at?: string | null
  academic_completed_at?: string | null
  is_overdue?: boolean
  overdue_tasks_count?: number
  journals?: { title?: string; slug?: string } | null
  owner?: { id: string; full_name?: string | null; email?: string | null } | null
  editor?: { id: string; full_name?: string | null; email?: string | null } | null
}

function fmt(ts?: string) {
  if (!ts) return '—'
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return '—'
  return format(d, 'yyyy-MM-dd HH:mm')
}

const INITIAL_VISIBLE_ROWS = 50
const VISIBLE_ROWS_STEP = 50

export function ManuscriptTable({
  rows,
  onAssign,
  onDecide,
  onOwnerBound,
  onRowUpdated,
  canBindOwner = true,
  canAssign = true,
  canDecide = true,
  canQuickPrecheck = true,
  readOnly = false,
  emptyText = 'No manuscripts found.',
}: {
  rows: ProcessRow[]
  onAssign?: (row: ProcessRow) => void
  onDecide?: (row: ProcessRow) => void
  onOwnerBound?: () => void
  onRowUpdated?: (updated: { id: string; status?: string; updated_at?: string }) => void
  canBindOwner?: boolean
  canAssign?: boolean
  canDecide?: boolean
  canQuickPrecheck?: boolean
  readOnly?: boolean
  emptyText?: string
}) {
  const [visibleCount, setVisibleCount] = useState(INITIAL_VISIBLE_ROWS)

  useEffect(() => {
    setVisibleCount(INITIAL_VISIBLE_ROWS)
  }, [rows.length])

  const visibleRows = useMemo(() => rows.slice(0, visibleCount), [rows, visibleCount])
  const remainingRows = Math.max(rows.length - visibleRows.length, 0)

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden" data-testid="editor-process-table">
      <Table className="table-fixed">
        <TableHeader>
          <TableRow className="bg-slate-50/50">
            <TableHead className={readOnly ? 'w-[26%]' : 'w-[25%]'}>Manuscript</TableHead>
            <TableHead className={readOnly ? 'w-[35%]' : 'w-[33%]'}>Status</TableHead>
            <TableHead className={readOnly ? 'w-[15%]' : 'w-[14%]'}>Updated</TableHead>
            <TableHead className={readOnly ? 'w-[24%]' : 'w-[20%]'}>People</TableHead>
            {!readOnly ? <TableHead className="w-[8%] text-right">Actions</TableHead> : null}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={readOnly ? 4 : 5} className="py-10 text-center text-sm text-slate-500">
                {emptyText}
              </TableCell>
            </TableRow>
          ) : (
            visibleRows.map((r) => {
              const status = r.status || ''
              const stage = (r.pre_check_status || '').toLowerCase()
              const isPrecheck = status.toLowerCase() === 'pre_check'
              const precheckLabel =
                isPrecheck && stage
                  ? `${stage} (${(r.current_role || '').replaceAll('_', ' ') || 'unassigned'})`
                  : '—'
              const currentAssignee = r.current_assignee?.full_name || r.current_assignee?.email || r.current_assignee?.id || '—'
              const ownerLabel = r.owner?.full_name || r.owner?.email || '—'
              const editorLabel = r.editor?.full_name || r.editor?.email || '—'
              const showAssigneeLine = currentAssignee !== '—' && currentAssignee !== editorLabel
              return (
                <TableRow key={r.id} className="hover:bg-slate-50/50 transition-colors">
                  <TableCell className="text-xs">
                    <Link
                      href={`/editor/manuscript/${r.id}`}
                      className="inline-flex items-center gap-2 text-slate-900 hover:text-blue-600 font-medium max-w-full"
                    >
                      <span className="block min-w-0 max-w-full truncate font-mono">{r.id}</span>
                      <ArrowRight className="h-3 w-3" />
                    </Link>
                    <p className="mt-1 truncate text-xs text-slate-500">
                      Journal: {r.journals?.title || (r.journals?.slug ? r.journals.slug : '—')}
                    </p>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <Badge variant="outline" className={getStatusBadgeClass(status)}>
                        {getStatusLabel(status)}
                      </Badge>
                      {precheckLabel !== '—' ? (
                        <p className="text-xs text-slate-500 break-words">
                          Pre-check: {precheckLabel}
                        </p>
                      ) : null}
                      {r.is_overdue ? (
                        <span className="inline-flex items-center gap-1 rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700">
                          Overdue
                          <span className="text-[0.7rem]">({r.overdue_tasks_count || 0})</span>
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">On track</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-slate-600">{fmt(r.updated_at)}</TableCell>
                  <TableCell className="text-sm text-slate-700">
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-xs min-w-0">
                          <span className="text-slate-500">Owner:</span>{' '}
                          <span className="font-medium text-slate-700">{ownerLabel}</span>
                        </p>
                        {!readOnly ? (
                          <BindingOwnerDropdown
                            manuscriptId={r.id}
                            currentOwner={r.owner}
                            onBound={onOwnerBound}
                            disabled={!canBindOwner}
                          />
                        ) : null}
                      </div>
                      {showAssigneeLine ? (
                        <p className="truncate text-xs">
                          <span className="text-slate-500">Assignee:</span>{' '}
                          <span className="font-medium text-slate-700">{currentAssignee}</span>
                        </p>
                      ) : null}
                    </div>
                  </TableCell>
                  {!readOnly ? (
                    <TableCell className="text-right">
                      <ManuscriptActions
                        row={r}
                        onAssign={onAssign}
                        onDecide={onDecide}
                        onRowUpdated={onRowUpdated}
                        canAssign={canAssign}
                        canDecide={canDecide}
                        canQuickPrecheck={canQuickPrecheck}
                      />
                    </TableCell>
                  ) : null}
                </TableRow>
              )
            })
          )}
        </TableBody>
      </Table>
      {remainingRows > 0 ? (
        <div className="flex items-center justify-center border-t border-slate-100 bg-slate-50/40 px-4 py-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setVisibleCount((prev) => prev + VISIBLE_ROWS_STEP)}
          >
            Load more ({remainingRows} remaining)
          </Button>
        </div>
      ) : null}
    </div>
  )
}
