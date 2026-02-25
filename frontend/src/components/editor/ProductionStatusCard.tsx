'use client'

import { useMemo, useState } from 'react'
import { Loader2, ArrowLeft, ArrowRight } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import { getStatusLabel } from '@/lib/statusStyles'
import ProductionUploadDialog from '@/components/ProductionUploadDialog'

type Props = {
  manuscriptId: string
  status: string
  finalPdfPath?: string | null
  invoice?: { status?: string | null; amount?: number | string | null } | null
  onStatusChange?: (nextStatus: string) => void
  onReload?: () => Promise<void> | void
}

const NEXT: Record<string, string | null> = {
  approved: 'layout',
  layout: 'english_editing',
  english_editing: 'proofreading',
  proofreading: 'published',
  published: null,
}

const PREV: Record<string, string | null> = {
  approved: null,
  layout: 'approved',
  english_editing: 'layout',
  proofreading: 'english_editing',
  published: null,
}

function nextActionLabel(status: string): string {
  const s = (status || '').toLowerCase()
  if (s === 'approved') return 'Start Layout'
  if (s === 'layout') return 'Start English Editing'
  if (s === 'english_editing') return 'Start Proofreading'
  if (s === 'proofreading') return 'Publish'
  return 'Advance'
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
  onStatusChange,
  onReload,
}: Props) {
  const normalized = (status || '').toLowerCase()
  const nextStatus = NEXT[normalized] ?? null
  const prevStatus = PREV[normalized] ?? null

  const [pending, setPending] = useState<'advance' | 'revert' | null>(null)
  const [optimistic, setOptimistic] = useState<string | null>(null)

  const effectiveStatus = optimistic ?? normalized

  const gateHint = useMemo(() => {
    if ((nextStatus || '').toLowerCase() !== 'published') return null
    const paymentOk = isPaid(invoice)
    const hasFinal = Boolean((finalPdfPath || '').trim())
    return {
      paymentOk,
      hasFinal,
    }
  }, [finalPdfPath, invoice, nextStatus])

  const showAdvance = nextStatus != null
  const showRevert = prevStatus != null
  const paymentOk = isPaid(invoice)
  const shouldShowMarkPaid = !paymentOk
  const shouldShowUpload = effectiveStatus !== 'published'

  async function markPaid() {
    const toastId = toast.loading('Confirming payment…')
    try {
      const res = await EditorApi.confirmInvoicePaid(manuscriptId)
      if (!res?.success) throw new Error(res?.detail || res?.message || 'Confirm payment failed')
      toast.success('Payment confirmed.', { id: toastId })
      void onReload?.()
    } catch (e: any) {
      toast.error(e instanceof Error ? e.message : 'Confirm payment failed', { id: toastId })
    }
  }

  async function runAdvance() {
    if (!nextStatus) return

    const previous = normalized
    const optimisticNext = nextStatus.toLowerCase()

    setPending('advance')
    setOptimistic(optimisticNext)
    onStatusChange?.(optimisticNext)

    try {
      const res = await EditorApi.advanceProduction(manuscriptId)
      if (!res?.success) throw new Error(res?.detail || res?.message || 'Advance failed')
      const newStatus = String(res?.data?.new_status || optimisticNext).toLowerCase()
      setOptimistic(null)
      onStatusChange?.(newStatus)
      toast.success(`Moved to ${getStatusLabel(newStatus)}`)
      void onReload?.()
    } catch (e: any) {
      setOptimistic(null)
      onStatusChange?.(previous)

      const detail =
        e instanceof Error ? e.message : typeof e === 'string' ? e : 'Advance failed'
      // 中文注释：尽量把门禁错误翻译成更友好的提示
      if (String(detail).toLowerCase().includes('payment required')) {
        toast.error('Waiting for Payment.')
      } else if (String(detail).toLowerCase().includes('production pdf')) {
        toast.error('Production PDF required.')
      } else {
        toast.error(detail)
      }
    } finally {
      setPending(null)
    }
  }

  async function runRevert() {
    if (!prevStatus) return

    const previous = normalized
    const optimisticNext = prevStatus.toLowerCase()

    setPending('revert')
    setOptimistic(optimisticNext)
    onStatusChange?.(optimisticNext)

    try {
      const res = await EditorApi.revertProduction(manuscriptId)
      if (!res?.success) throw new Error(res?.detail || res?.message || 'Revert failed')
      const newStatus = String(res?.data?.new_status || optimisticNext).toLowerCase()
      setOptimistic(null)
      onStatusChange?.(newStatus)
      toast.success(`Reverted to ${getStatusLabel(newStatus)}`)
      void onReload?.()
    } catch (e: any) {
      setOptimistic(null)
      onStatusChange?.(previous)
      const detail =
        e instanceof Error ? e.message : typeof e === 'string' ? e : 'Revert failed'
      toast.error(detail)
    } finally {
      setPending(null)
    }
  }

  return (
    <Card data-testid="production-status-card">
      <CardHeader>
        <CardTitle className="text-lg">Production</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex items-center justify-between gap-3">
          <span className="text-slate-500">Current Stage</span>
          <span className="text-slate-900" data-testid="production-stage">
            {getStatusLabel(effectiveStatus)}
          </span>
        </div>

        {gateHint ? (
          <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-600 space-y-1">
            <div className="flex items-center justify-between">
              <span>Payment</span>
              <span className={gateHint.paymentOk ? 'text-emerald-700' : 'text-amber-700'}>
                {gateHint.paymentOk ? 'OK' : 'Pending'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Final PDF</span>
              <span className={gateHint.hasFinal ? 'text-emerald-700' : 'text-amber-700'}>
                {gateHint.hasFinal ? 'Uploaded' : 'Missing'}
              </span>
            </div>
            <div className="text-slate-500">Note: Production Gate may be disabled in MVP.</div>
          </div>
        ) : null}

        {shouldShowUpload ? (
          <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-2">
            <div className="flex items-center justify-between gap-3">
              <span className="text-slate-500">Final PDF</span>
              <span className="font-mono text-[11px] text-slate-700 truncate max-w-[180px]" title={finalPdfPath || ''}>
                {finalPdfPath ? 'Uploaded' : 'Missing'}
              </span>
            </div>
            <ProductionUploadDialog
              manuscriptId={manuscriptId}
              disabled={pending != null}
              onUploaded={() => {
                void onReload?.()
              }}
            />
          </div>
        ) : null}

        {shouldShowMarkPaid ? (
          <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Payment</span>
              <span className="text-amber-700 font-medium">Pending</span>
            </div>
            <Button type="button" variant="outline" className="w-full" onClick={markPaid} disabled={pending != null}>
              Mark Paid
            </Button>
          </div>
        ) : null}

        <div className="flex flex-col gap-2">
          {showAdvance ? (
            <Button className="w-full justify-between" onClick={runAdvance} disabled={pending != null}>
              <span>{nextActionLabel(normalized)}</span>
              {pending === 'advance' ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
            </Button>
          ) : (
            <div className="text-sm text-slate-500">No next actions available.</div>
          )}

          {showRevert ? (
            <Button
              className="w-full justify-between"
              variant="outline"
              onClick={runRevert}
              disabled={pending != null}
            >
              <span>Revert</span>
              {pending === 'revert' ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowLeft className="h-4 w-4" />}
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}
