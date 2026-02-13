'use client'

import { useEffect, useMemo, useState } from 'react'
import { Loader2, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { ManuscriptApi } from '@/services/manuscriptApi'
import type { ProductionCorrectionItem, ProofreadingContext, ProofreadingDecision } from '@/types/production'
import { canSubmitProofreading } from '@/lib/production-utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'

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
  const latest = context?.cycle?.latest_response || null

  // 中文注释: 若该轮次已经提交过校对反馈，表单需要回显并只读。
  // 否则作者会误以为“提交失败/内容丢失”，无法形成可追溯证据链。
  useEffect(() => {
    if (!context?.cycle?.id) return

    if (!latest?.id) {
      setDecision('confirm_clean')
      setSummary('')
      setItems([{ ...EMPTY_ITEM }])
      return
    }

    setDecision(latest.decision)
    setSummary(String(latest.summary || ''))

    if (latest.decision === 'submit_corrections') {
      const normalized = (latest.corrections || []).map((row) => ({
        id: row.id,
        line_ref: row.line_ref || '',
        original_text: row.original_text || '',
        suggested_text: String(row.suggested_text || ''),
        reason: row.reason || '',
        sort_order: row.sort_order,
      }))
      setItems(normalized.length > 0 ? normalized : [{ ...EMPTY_ITEM }])
    } else {
      setItems([{ ...EMPTY_ITEM }])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [context?.cycle?.id, latest?.id])

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
    <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
      <div>
        <h2 className="text-sm font-bold uppercase tracking-wide text-slate-700">Proofreading Response</h2>
        <p className="mt-1 text-xs text-slate-500">请选择“确认无误”或“提交修正清单”。</p>
        {latest?.submitted_at ? (
          <p className="mt-2 text-xs text-slate-500">已提交于 {new Date(latest.submitted_at).toLocaleString()}</p>
        ) : null}
      </div>

      <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
        <RadioGroup
          value={decision}
          onValueChange={(value) => setDecision(value as ProofreadingDecision)}
          className="gap-3"
          disabled={isReadOnly}
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="confirm_clean" id="proof-confirm-clean" />
            <Label htmlFor="proof-confirm-clean" className="text-sm text-slate-700">
              确认无误（Confirm clean proof）
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="submit_corrections" id="proof-submit-corrections" />
            <Label htmlFor="proof-submit-corrections" className="text-sm text-slate-700">
              提交修正清单（Submit correction list）
            </Label>
          </div>
        </RadioGroup>
      </div>

      <div>
        <Label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
          Summary (Optional)
        </Label>
        <Textarea
          value={summary}
          onChange={(event) => setSummary(event.target.value)}
          disabled={isReadOnly}
          placeholder="例如：整体可发布，仅需修正图2注释。"
        />
      </div>

      {decision === 'submit_corrections' ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Correction Items</p>
            <Button
              type="button"
              onClick={addItem}
              disabled={isReadOnly}
              variant="ghost"
              size="sm"
              className="gap-1 text-blue-600 hover:text-blue-600"
            >
              <Plus className="h-3.5 w-3.5" /> Add Item
            </Button>
          </div>

          {items.map((item, idx) => (
            <div key={idx} className="space-y-2 rounded-md border border-slate-200 p-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-slate-700">Item #{idx + 1}</p>
                <Button
                  type="button"
                  onClick={() => removeItem(idx)}
                  disabled={isReadOnly || items.length <= 1}
                  variant="ghost"
                  size="sm"
                  className="gap-1 text-rose-600 hover:text-rose-600"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Remove
                </Button>
              </div>

              <Input
                value={item.line_ref || ''}
                onChange={(event) => updateItem(idx, { line_ref: event.target.value })}
                disabled={isReadOnly}
                placeholder="Line/Paragraph reference (e.g. Page 3, para 2)"
              />
              <Textarea
                value={item.original_text || ''}
                onChange={(event) => updateItem(idx, { original_text: event.target.value })}
                disabled={isReadOnly}
                placeholder="Original text"
              />
              <Textarea
                value={item.suggested_text || ''}
                onChange={(event) => updateItem(idx, { suggested_text: event.target.value })}
                disabled={isReadOnly}
                placeholder="Suggested correction (required)"
              />
              <Textarea
                value={item.reason || ''}
                onChange={(event) => updateItem(idx, { reason: event.target.value })}
                disabled={isReadOnly}
                placeholder="Reason"
              />
            </div>
          ))}
        </div>
      ) : null}

      <Button type="button" onClick={() => void submit()} disabled={!canSubmit || submitting} className="w-full gap-2">
        {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        Submit Proofreading
      </Button>

      {isReadOnly ? <p className="text-xs text-amber-700">该轮次已提交或已过截止时间，当前为只读。</p> : null}
    </section>
  )
}
