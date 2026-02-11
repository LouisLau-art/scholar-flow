'use client'

import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { getStatusBadgeClass, getStatusLabel } from '@/lib/statusStyles'
import { ArrowLeft } from 'lucide-react'
import { format, parseISO } from 'date-fns'

type Person = { full_name?: string | null; email?: string | null } | null

export type ManuscriptHeaderData = {
  id: string
  title?: string | null
  status?: string | null
  updated_at?: string | null
  owner?: Person
  editor?: Person
  invoice?: { status?: string | null; amount?: number | string | null } | null
  invoice_metadata?: { authors?: string | null; funding_info?: string | null } | null
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

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-900 break-words">{value}</div>
    </div>
  )
}

export function ManuscriptHeader({ ms }: { ms: ManuscriptHeaderData }) {
  const status = String(ms.status || '')
  const authors = (ms.invoice_metadata?.authors || '').trim()
  const funding = (ms.invoice_metadata?.funding_info || '').trim()

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-serif font-bold text-slate-900 tracking-tight truncate">
              {ms.title || 'Untitled Manuscript'}
            </h1>
            <Badge className={`border ${getStatusBadgeClass(status)}`}>{getStatusLabel(status)}</Badge>
          </div>
          <div className="mt-1 font-mono text-xs text-slate-400">{ms.id}</div>
        </div>

        <Link href="/dashboard" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
          <ArrowLeft className="h-4 w-4" />
          返回编辑台
        </Link>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Authors" value={authors || '—'} />
        <Field label="Funding" value={funding || '—'} />
        <Field
          label="APC"
          value={
            <>
              {apcLabel(ms.invoice)}{' '}
              {ms.invoice?.amount != null && ms.invoice?.amount !== '' ? `($${ms.invoice.amount})` : ''}
            </>
          }
        />
        <Field label="Internal Owner" value={ms.owner?.full_name || ms.owner?.email || '—'} />
        <Field label="Assigned Editor" value={ms.editor?.full_name || ms.editor?.email || '—'} />
        <Field label="Updated" value={fmtTs(ms.updated_at)} />
      </div>
    </div>
  )
}
