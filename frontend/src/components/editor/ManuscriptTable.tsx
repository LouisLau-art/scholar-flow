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
}: {
  rows: ProcessRow[]
  onAssign?: (row: ProcessRow) => void
  onDecide?: (row: ProcessRow) => void
  onOwnerBound?: () => void
  onRowUpdated?: (updated: { id: string; status?: string; updated_at?: string }) => void
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-x-auto" data-testid="editor-process-table">
      <Table>
        <TableHeader>
          <TableRow className="bg-slate-50/50">
            <TableHead className="w-[200px] whitespace-nowrap">Manuscript ID</TableHead>
            <TableHead className="whitespace-nowrap">Journal</TableHead>
            <TableHead className="whitespace-nowrap">Submitted</TableHead>
            <TableHead className="whitespace-nowrap">Status</TableHead>
            <TableHead className="whitespace-nowrap">Updated</TableHead>
            <TableHead className="whitespace-nowrap">Assign Editor</TableHead>
            <TableHead className="whitespace-nowrap">Owner</TableHead>
            <TableHead className="text-right whitespace-nowrap">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={8} className="py-10 text-center text-sm text-slate-500">
                No manuscripts found.
              </TableCell>
            </TableRow>
          ) : (
            rows.map((r) => {
              const status = r.status || ''
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
                  <TableCell className="text-sm text-slate-600 whitespace-nowrap">{fmt(r.created_at)}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={getStatusBadgeClass(status)}>
                      {getStatusLabel(status)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-slate-600 whitespace-nowrap">{fmt(r.updated_at)}</TableCell>
                  <TableCell className="text-sm text-slate-700 font-medium">
                    {r.editor?.full_name || r.editor?.email || '—'}
                  </TableCell>
                  <TableCell className="text-sm text-slate-700">
                    <div className="flex items-center gap-2">
                      <div className="min-w-[100px] max-w-[150px] truncate font-medium">
                        {r.owner?.full_name || r.owner?.email || '—'}
                      </div>
                      <BindingOwnerDropdown
                        manuscriptId={r.id}
                        currentOwner={r.owner}
                        onBound={onOwnerBound}
                      />
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <ManuscriptActions row={r} onAssign={onAssign} onDecide={onDecide} onRowUpdated={onRowUpdated} />
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
