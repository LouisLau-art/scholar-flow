'use client'

import Link from 'next/link'
import { format } from 'date-fns'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { getStatusBadgeClass, getStatusLabel } from '@/lib/statusStyles'
import { BindingOwnerDropdown } from '@/components/editor/BindingOwnerDropdown'
import { ArrowRight, Users, Gavel } from 'lucide-react'

export type ProcessRow = {
  id: string
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
}: {
  rows: ProcessRow[]
  onAssign?: (row: ProcessRow) => void
  onDecide?: (row: ProcessRow) => void
  onOwnerBound?: () => void
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden" data-testid="editor-process-table">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[220px]">Manuscript ID</TableHead>
            <TableHead>Journal</TableHead>
            <TableHead>Submitted</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Updated</TableHead>
            <TableHead>Assign Editor</TableHead>
            <TableHead>Owner</TableHead>
            <TableHead className="text-right">Actions</TableHead>
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
                <TableRow key={r.id}>
                  <TableCell className="font-mono text-xs">
                    <Link
                      href={`/editor/manuscript/${r.id}`}
                      className="inline-flex items-center gap-2 text-slate-900 hover:text-blue-600"
                    >
                      <span className="truncate max-w-[180px]">{r.id}</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </TableCell>
                  <TableCell className="text-sm text-slate-700">
                    {r.journals?.title || (r.journals?.slug ? r.journals.slug : '—')}
                  </TableCell>
                  <TableCell className="text-sm text-slate-700">{fmt(r.created_at)}</TableCell>
                  <TableCell>
                    <Badge className={`border ${getStatusBadgeClass(status)}`}>{getStatusLabel(status)}</Badge>
                  </TableCell>
                  <TableCell className="text-sm text-slate-700">{fmt(r.updated_at)}</TableCell>
                  <TableCell className="text-sm text-slate-700">
                    {r.editor?.full_name || r.editor?.email || '—'}
                  </TableCell>
                  <TableCell className="text-sm text-slate-700">
                    <div className="flex items-center gap-2">
                      <div className="min-w-0">
                        <div className="truncate">{r.owner?.full_name || r.owner?.email || '—'}</div>
                      </div>
                      <BindingOwnerDropdown
                        manuscriptId={r.id}
                        currentOwner={r.owner}
                        onBound={onOwnerBound}
                      />
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button size="sm" variant="outline" className="gap-2" onClick={() => onAssign?.(r)}>
                        <Users className="h-4 w-4" />
                        Assign
                      </Button>
                      <Button size="sm" className="gap-2" onClick={() => onDecide?.(r)}>
                        <Gavel className="h-4 w-4" />
                        Decide
                      </Button>
                    </div>
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
