'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDateTimeLocal } from '@/lib/date-display'
import { UI_COPY } from '@/lib/ui-copy'
import type { FinanceInvoiceRow } from '@/types/finance'
import { cn } from '@/lib/utils'
import { cva } from 'class-variance-authority'

type Props = {
  rows: FinanceInvoiceRow[]
  loading?: boolean
  confirmingInvoiceId?: string | null
  onConfirm?: (row: FinanceInvoiceRow) => void
  emptyText?: string
}

const financeStatusBadgeVariants = cva('border-transparent', {
  variants: {
    status: {
      paid: 'bg-primary/10 text-primary',
      waived: 'bg-secondary text-secondary-foreground',
      unpaid: 'bg-destructive/10 text-destructive',
    },
  },
  defaultVariants: {
    status: 'unpaid',
  },
})

function formatAmount(amount: number, currency: string) {
  return `${currency} ${amount.toFixed(2)}`
}

export function FinanceInvoicesTable(props: Props) {
  if (props.loading) {
    return <div className="p-8 text-sm text-muted-foreground">{UI_COPY.loading} invoices</div>
  }

  if (!props.rows.length) {
    return <div className="p-8 text-sm text-muted-foreground">{props.emptyText || '当前无匹配账单'}</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="bg-foreground text-primary-foreground">
          <tr>
            <th className="px-4 py-3 font-semibold">Invoice</th>
            <th className="px-4 py-3 font-semibold">Manuscript</th>
            <th className="px-4 py-3 font-semibold">Amount</th>
            <th className="px-4 py-3 font-semibold">Status</th>
            <th className="px-4 py-3 font-semibold">Updated</th>
            <th className="px-4 py-3 text-right font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border bg-card">
          {props.rows.map((row) => {
            const confirming = props.confirmingInvoiceId === row.invoice_id
            return (
              <tr key={row.invoice_id} className="hover:bg-muted/40 transition-colors">
                <td className="px-4 py-3 align-top">
                  <div className="font-medium text-foreground">{row.invoice_number || row.invoice_id}</div>
                  <div className="text-xs text-muted-foreground">{row.invoice_id}</div>
                </td>
                <td className="px-4 py-3 align-top">
                  <div className="font-medium text-foreground">{row.manuscript_title}</div>
                  <div className="text-xs text-muted-foreground">{row.authors || 'Author'}</div>
                </td>
                <td className="px-4 py-3 text-foreground">{formatAmount(Number(row.amount || 0), row.currency || 'USD')}</td>
                <td className="px-4 py-3">
                  <Badge variant="outline" className={cn(financeStatusBadgeVariants({ status: row.effective_status }))}>
                    {row.effective_status.toUpperCase()}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-muted-foreground">{formatDateTimeLocal(row.updated_at)}</td>
                <td className="px-4 py-3">
                  <div className="flex justify-end">
                    <Button
                      type="button"
                      size="sm"
                      disabled={confirming || row.effective_status !== 'unpaid'}
                      onClick={() => props.onConfirm?.(row)}
                    >
                      {confirming ? UI_COPY.confirming : 'Mark Paid'}
                    </Button>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
