'use client'

import { useMemo, useState } from 'react'
import { ArrowRight } from 'lucide-react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button, buttonVariants } from '@/components/ui/button'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import { getStatusLabel } from '@/lib/statusStyles'
import { cn } from '@/lib/utils'

type Props = {
  manuscriptId: string
  status: string
  finalPdfPath?: string | null
  invoice?: { status?: string | null; amount?: number | string | null } | null
  onReload?: () => Promise<void> | void
}

function isPaid(invoice?: Props['invoice']) {
  const amountRaw = invoice?.amount
  const amountParsed = typeof amountRaw === 'string' ? Number.parseFloat(amountRaw) : Number(amountRaw)
  const amount = Number.isFinite(amountParsed) ? amountParsed : 0
  const status = (invoice?.status ?? '').toString().trim().toLowerCase()
  if (!status && amountRaw == null) return false
  return amount <= 0 || status === 'paid' || status === 'waived'
}

export function ProductionStatusCard({
  manuscriptId,
  status,
  finalPdfPath,
  invoice,
  onReload,
}: Props) {
  const normalized = (status || '').toLowerCase()
  const [pending, setPending] = useState(false)

  const paymentOk = isPaid(invoice)
  const hasFinal = Boolean((finalPdfPath || '').trim())
  
  const gateHint = useMemo(() => {
    return {
      paymentOk,
      hasFinal,
    }
  }, [hasFinal, paymentOk])

  const shouldShowMarkPaid = !paymentOk

  async function markPaid() {
    const toastId = toast.loading('Confirming payment…')
    setPending(true)
    try {
      const res = await EditorApi.confirmInvoicePaid(manuscriptId)
      if (!res?.success) throw new Error(res?.detail || res?.message || 'Confirm payment failed')
      toast.success('Payment confirmed.', { id: toastId })
      void onReload?.()
    } catch (e: any) {
      toast.error(e instanceof Error ? e.message : 'Confirm payment failed', { id: toastId })
    } finally {
      setPending(false)
    }
  }

  return (
    <Card data-testid="production-status-card">
      <CardHeader>
        <CardTitle className="text-lg">Production</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex items-center justify-between gap-3">
          <span className="text-muted-foreground">Current Stage</span>
          <span className="text-foreground font-semibold" data-testid="production-stage">
            {getStatusLabel(normalized)}
          </span>
        </div>

        {gateHint ? (
          <div className="rounded-lg border border-border bg-card p-3 text-xs text-muted-foreground space-y-1">
            <div className="flex items-center justify-between">
              <span>Payment</span>
              <span className={gateHint.paymentOk ? 'text-emerald-700 font-semibold' : 'text-amber-700 font-semibold'}>
                {gateHint.paymentOk ? 'OK' : 'Pending'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Final SOP Approval</span>
              <span className={normalized === 'approved_for_publish' || normalized === 'published' ? 'text-emerald-700 font-semibold' : 'text-amber-700 font-semibold'}>
                {normalized === 'approved_for_publish' || normalized === 'published' ? 'Approved' : 'Pending'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Final PDF</span>
              <span className={gateHint.hasFinal ? 'text-emerald-700 font-semibold' : 'text-amber-700 font-semibold'}>
                {gateHint.hasFinal ? 'Uploaded' : 'Missing'}
              </span>
            </div>
          </div>
        ) : null}

        {shouldShowMarkPaid ? (
          <div className="rounded-lg border border-border bg-card p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Payment</span>
              <span className="text-amber-700 font-medium">Pending</span>
            </div>
            <Button type="button" variant="outline" className="w-full" onClick={markPaid} disabled={pending}>
              Mark Paid
            </Button>
          </div>
        ) : null}

        <div className="flex flex-col gap-2 pt-2 border-t border-border">
          <Link
            href={`/editor/production/${encodeURIComponent(manuscriptId)}`}
            className={cn(buttonVariants({ variant: 'outline' }), 'w-full justify-between')}
          >
            <span>Open Production Workspace</span>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}
