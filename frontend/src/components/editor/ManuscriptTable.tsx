'use client'

import Link from 'next/link'
import { format } from 'date-fns'
import { Badge } from '@/components/ui/badge'
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
  emptyText?: string
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-x-auto" data-testid="editor-process-table">
      <Table>
        <TableHeader>
          <TableRow className="bg-slate-50/50">
            <TableHead className="w-[180px] whitespace-nowrap">Manuscript ID</TableHead>
            <TableHead className="whitespace-nowrap">Journal</TableHead>
            <TableHead className="whitespace-nowrap">Status</TableHead>
            <TableHead className="whitespace-nowrap">Updated</TableHead>
            <TableHead className="whitespace-nowrap">People</TableHead>
            <TableHead className="text-right whitespace-nowrap">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="py-10 text-center text-sm text-slate-500">
                {emptyText}
              </TableCell>
            </TableRow>
          ) : (
            rows.map((r) => {
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
                  <TableCell className="font-mono text-[10px] sm:text-xs">
                    <Link
                      href={`/editor/manuscript/${r.id}`}
                      className="inline-flex items-center gap-2 text-slate-900 hover:text-blue-600 font-medium"
                    >
                      <span className="truncate max-w-[150px]">{r.id}</span>
                      <ArrowRight className="h-3 w-3" />
                    </Link>
                  </TableCell>
                  <TableCell className="text-sm text-slate-700 whitespace-nowrap">
                    {r.journals?.title || (r.journals?.slug ? r.journals.slug : '—')}
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <Badge variant="outline" className={getStatusBadgeClass(status)}>
                        {getStatusLabel(status)}
                      </Badge>
                      {precheckLabel !== '—' ? (
                        <p className="text-[11px] text-slate-500 whitespace-nowrap truncate max-w-[260px]">
                          Pre-check: {precheckLabel}
                        </p>
                      ) : null}
                      {r.is_overdue ? (
                        <span className="inline-flex items-center gap-1 rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700">
                          Overdue
                          <span className="text-[11px]">({r.overdue_tasks_count || 0})</span>
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">On track</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-slate-600 whitespace-nowrap">{fmt(r.updated_at)}</TableCell>
                  <TableCell className="text-sm text-slate-700">
                    <div className="min-w-[210px] space-y-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-xs">
                          <span className="text-slate-500">Owner:</span>{' '}
                          <span className="font-medium text-slate-700">{ownerLabel}</span>
                        </p>
                        <BindingOwnerDropdown
                          manuscriptId={r.id}
                          currentOwner={r.owner}
                          onBound={onOwnerBound}
                          disabled={!canBindOwner}
                        />
                      </div>
                      <p className="truncate text-xs">
                        <span className="text-slate-500">Editor:</span>{' '}
                        <span className="font-medium text-slate-700">{editorLabel}</span>
                      </p>
                      {showAssigneeLine ? (
                        <p className="truncate text-xs">
                          <span className="text-slate-500">Assignee:</span>{' '}
                          <span className="font-medium text-slate-700">{currentAssignee}</span>
                        </p>
                      ) : null}
                    </div>
                  </TableCell>
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
                </TableRow>
              )
            })
          )}
        </TableBody>
      </Table>
    </div>
  )
}
