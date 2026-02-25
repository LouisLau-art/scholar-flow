'use client'

import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { getStatusBadgeClass, getStatusLabel } from '@/lib/statusStyles'
import { ArrowLeft, FileText } from 'lucide-react'
import { format, parseISO } from 'date-fns'

type Person = { full_name?: string | null; email?: string | null } | null

export type ManuscriptDetailsHeaderData = {
  id: string
  title?: string | null
  status?: string | null
  updated_at?: string | null
  owner?: Person
  editor?: Person
  invoice?: { status?: string | null; amount?: number | string | null } | null
  invoice_metadata?: { authors?: string | null } | null
}

function fmtTs(value: string | null | undefined) {
  if (!value) return '—'
  try {
    const dt = parseISO(value)
    return format(dt, 'yyyy-MM-dd HH:mm')
  } catch {
    return '—'
  }
}

function apcLabel(invoice?: { status?: string | null; amount?: number | string | null } | null) {
  const status = String(invoice?.status || '').toLowerCase()
  if (!status) return 'Invoice missing'
  if (status === 'paid') return 'Paid'
  if (status === 'unpaid') return 'Unpaid'
  return status
}

export function ManuscriptDetailsHeader({ ms }: { ms: ManuscriptDetailsHeaderData }) {
  const status = String(ms.status || '')
  const primaryAuthors = (ms.invoice_metadata?.authors || '').trim()
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex items-start gap-3">
        <div className="mt-1 rounded-xl bg-card p-2 shadow-sm ring-1 ring-border">
          <FileText className="h-5 w-5 text-primary" />
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="truncate text-2xl font-serif font-bold tracking-tight text-foreground sm:text-3xl">
              {ms.title || 'Untitled Manuscript'}
            </h1>
            <Badge className={`border ${getStatusBadgeClass(status)}`}>{getStatusLabel(status)}</Badge>
          </div>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{ms.id}</p>
          <div className="mt-3 grid grid-cols-1 gap-2 text-sm text-muted-foreground sm:grid-cols-2">
            <div className="flex items-center justify-between gap-3 sm:justify-start sm:gap-2">
              <span className="text-muted-foreground">Authors</span>
              <span className="text-foreground sm:truncate">{primaryAuthors || '—'}</span>
            </div>
            <div className="flex items-center justify-between gap-3 sm:justify-start sm:gap-2">
              <span className="text-muted-foreground">APC</span>
              <span className="text-foreground">
                {apcLabel(ms.invoice)}{' '}
                {ms.invoice?.amount != null && ms.invoice?.amount !== '' ? `($${ms.invoice.amount})` : ''}
              </span>
            </div>
            <div className="flex items-center justify-between gap-3 sm:justify-start sm:gap-2">
              <span className="text-muted-foreground">Owner</span>
              <span className="text-foreground">{ms.owner?.full_name || ms.owner?.email || '—'}</span>
            </div>
            <div className="flex items-center justify-between gap-3 sm:justify-start sm:gap-2">
              <span className="text-muted-foreground">Assign Editor</span>
              <span className="text-foreground">{ms.editor?.full_name || ms.editor?.email || '—'}</span>
            </div>
            <div className="flex items-center justify-between gap-3 sm:justify-start sm:gap-2">
              <span className="text-muted-foreground">Updated</span>
              <span className="text-foreground">{fmtTs(ms.updated_at)}</span>
            </div>
          </div>
        </div>
      </div>

      <Link href="/dashboard" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
        <ArrowLeft className="h-4 w-4" />
        返回编辑台
      </Link>
    </div>
  )
}
