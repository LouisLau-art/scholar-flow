'use client'

import { useMemo, useState } from 'react'
import { Loader2, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { ManuscriptApi } from '@/services/manuscriptApi'
import type { ProductionCorrectionItem, ProofreadingContext, ProofreadingDecision } from '@/types/production'
import { canSubmitProofreading } from '@/lib/production-utils'

type Props = {
  manuscriptId: string
  context: ProofreadingContext
  onSubmitted: () => Promise<void>
}

const EMPTY_ITEM: ProductionCorrectionItem = {
  line_ref: '',
  original_text: '',
  suggested_text: '',
  reason: '',
}

export function ProofreadingForm({ manuscriptId, context, onSubmitted }: Props) {
  const [decision, setDecision] = useState<ProofreadingDecision>('confirm_clean')
  const [summary, setSummary] = useState('')
  const [items, setItems] = useState<ProductionCorrectionItem[]>([{ ...EMPTY_ITEM }])
  const [submitting, setSubmitting] = useState(false)

  const isReadOnly = !context.can_submit || context.is_read_only

  const canSubmit = useMemo(() => {
    return canSubmitProofreading(decision, items, isReadOnly)
  }, [decision, isReadOnly, items])

  const updateItem = (idx: number, patch: Partial<ProductionCorrectionItem>) => {
    setItems((prev) => prev.map((item, i) => (i === idx ? { ...item, ...patch } : item)))
  }

  const addItem = () => {
    setItems((prev) => [...prev, { ...EMPTY_ITEM }])
  }

  const removeItem = (idx: number) => {
    setItems((prev) => prev.filter((_, i) => i !== idx))
  }

  const submit = async () => {
    if (!canSubmit) {
      toast.error('请完善校对内容后再提交')
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        decision,
        summary: summary || undefined,
        corrections:
          decision === 'submit_corrections'
            ? items
                .map((item) => ({
                  line_ref: item.line_ref || undefined,
                  original_text: item.original_text || undefined,
                  suggested_text: String(item.suggested_text || '').trim(),
                  reason: item.reason || undefined,
                }))
                .filter((item) => item.suggested_text.length > 0)
            : [],
      }

      const res = await ManuscriptApi.submitProofreading(manuscriptId, context.cycle.id, payload)
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || '提交校对失败')
      }
      toast.success('校对结果已提交')
      await onSubmitted()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '提交校对失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 space-y-4">
      <div>
        <h2 className="text-sm font-bold uppercase tracking-wide text-slate-700">Proofreading Response</h2>
        <p className="mt-1 text-xs text-slate-500">请选择“确认无误”或“提交修正清单”。</p>
      </div>

      <div className="space-y-2 rounded-md border border-slate-200 bg-slate-50 p-3">
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="radio"
            checked={decision === 'confirm_clean'}
            onChange={() => setDecision('confirm_clean')}
            disabled={isReadOnly}
          />
          Confirm clean proof
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="radio"
            checked={decision === 'submit_corrections'}
            onChange={() => setDecision('submit_corrections')}
            disabled={isReadOnly}
          />
          Submit correction list
        </label>
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">Summary (Optional)</label>
        <textarea
          rows={3}
          value={summary}
          onChange={(event) => setSummary(event.target.value)}
          disabled={isReadOnly}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          placeholder="例如：整体可发布，仅需修正图2注释。"
        />
      </div>

      {decision === 'submit_corrections' ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Correction Items</p>
            <button
              type="button"
              onClick={addItem}
              disabled={isReadOnly}
              className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:underline disabled:opacity-60"
            >
              <Plus className="h-3.5 w-3.5" /> Add Item
            </button>
          </div>

          {items.map((item, idx) => (
            <div key={idx} className="rounded-md border border-slate-200 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-slate-700">Item #{idx + 1}</p>
                <button
                  type="button"
                  onClick={() => removeItem(idx)}
                  disabled={isReadOnly || items.length <= 1}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-rose-600 hover:underline disabled:opacity-60"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Remove
                </button>
              </div>

              <input
                value={item.line_ref || ''}
                onChange={(event) => updateItem(idx, { line_ref: event.target.value })}
                disabled={isReadOnly}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Line/Paragraph reference (e.g. Page 3, para 2)"
              />
              <textarea
                rows={2}
                value={item.original_text || ''}
                onChange={(event) => updateItem(idx, { original_text: event.target.value })}
                disabled={isReadOnly}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Original text"
              />
              <textarea
                rows={2}
                value={item.suggested_text || ''}
                onChange={(event) => updateItem(idx, { suggested_text: event.target.value })}
                disabled={isReadOnly}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Suggested correction (required)"
              />
              <textarea
                rows={2}
                value={item.reason || ''}
                onChange={(event) => updateItem(idx, { reason: event.target.value })}
                disabled={isReadOnly}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Reason"
              />
            </div>
          ))}
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => void submit()}
        disabled={!canSubmit || submitting}
        className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
      >
        {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        Submit Proofreading
      </button>

      {isReadOnly ? <p className="text-xs text-amber-700">该轮次已提交或已过截止时间，当前为只读。</p> : null}
    </section>
  )
}
