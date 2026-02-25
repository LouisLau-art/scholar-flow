'use client'

import { useEffect, useMemo, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { EditorApi } from '@/services/editorApi'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'

export type QuickPrecheckDecision = 'approve' | 'revision'

function readDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: unknown } | undefined
    if (typeof first?.msg === 'string') return first.msg
  }
  return ''
}

function normalizeQuickPrecheckError(raw: unknown): string {
  const msg = (typeof raw === 'string' ? raw : '').toLowerCase()
  if (msg.includes('comment is required')) {
    return '选择 Request Revision 时必须填写 Comment。'
  }
  if (msg.includes('only allowed') || msg.includes('conflict') || msg.includes('current:')) {
    return '稿件状态已变化，请刷新列表后重试。'
  }
  if (msg.includes('forbidden') || msg.includes('not allowed')) {
    return '你没有权限执行该操作。'
  }
  return typeof raw === 'string' && raw.trim() ? raw : 'Quick pre-check failed'
}

export function QuickPrecheckModal({
  open,
  onOpenChange,
  manuscriptId,
  manuscriptTitle,
  onUpdated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  manuscriptId: string
  manuscriptTitle?: string
  onUpdated?: (updated: { id: string; status?: string; updated_at?: string }) => void
}) {
  const [decision, setDecision] = useState<QuickPrecheckDecision>('approve')
  const [comment, setComment] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setDecision('approve')
    setComment('')
  }, [open])

  const needsComment = decision === 'revision'
  const canSubmit = useMemo(() => {
    if (!needsComment) return true
    return comment.trim().length > 0
  }, [needsComment, comment])

  async function submit() {
    const toastId = toast.loading('Saving...')
    try {
      setSaving(true)
      const res = await EditorApi.quickPrecheck(manuscriptId, {
        decision,
        comment: comment.trim() || undefined,
      })
      if (!res?.success) {
        const detail = readDetail(res?.detail)
        throw new Error(normalizeQuickPrecheckError(detail || res?.message))
      }
      const updated = res.data || {}
      toast.success('Updated', { id: toastId })
      onUpdated?.({ id: updated.id || manuscriptId, status: updated.status, updated_at: updated.updated_at })
      onOpenChange(false)
    } catch (e) {
      const message = normalizeQuickPrecheckError(e instanceof Error ? e.message : '')
      toast.error(message, { id: toastId })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Quick Pre-check</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-lg border border-border bg-muted/50 p-3">
            <div className="text-xs text-muted-foreground">Manuscript</div>
            <div className="mt-1 font-mono text-[11px] text-foreground break-all">{manuscriptId}</div>
            {manuscriptTitle ? <div className="mt-1 text-sm font-medium text-foreground">{manuscriptTitle}</div> : null}
          </div>

          <div className="space-y-2">
            <Label className="text-sm">Decision</Label>
            <RadioGroup value={decision} onValueChange={(v) => setDecision(v as QuickPrecheckDecision)} className="grid gap-2">
              <div className="flex items-start gap-2 rounded-md border border-border p-3">
                <RadioGroupItem value="approve" id="qp-approve" className="mt-1" />
                <label htmlFor="qp-approve" className="flex-1 cursor-pointer">
                  <div className="font-medium">Approve (Send to review)</div>
                  <div className="text-xs text-muted-foreground">Moves status to Under Review</div>
                </label>
              </div>
              <div className="flex items-start gap-2 rounded-md border border-border p-3">
                <RadioGroupItem value="revision" id="qp-revision" className="mt-1" />
                <label htmlFor="qp-revision" className="flex-1 cursor-pointer">
                  <div className="font-medium">Request Revision</div>
                  <div className="text-xs text-muted-foreground">Moves status to Minor Revision</div>
                </label>
              </div>
            </RadioGroup>
          </div>

          <div className="space-y-2">
            <Label className="text-sm">
              Comment {needsComment ? <span className="text-red-600">*</span> : <span className="text-muted-foreground">(optional)</span>}
            </Label>
            <Textarea
              placeholder={needsComment ? 'Required for revision…' : 'Optional note…'}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="min-h-[120px]"
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={submit} disabled={saving || !canSubmit} className="gap-2">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Confirm
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
