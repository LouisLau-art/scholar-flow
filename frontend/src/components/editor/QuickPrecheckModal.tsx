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

export type QuickPrecheckDecision = 'approve' | 'reject' | 'revision'

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

  const needsComment = decision === 'reject' || decision === 'revision'
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
        throw new Error(res?.detail || res?.message || 'Quick pre-check failed')
      }
      const updated = res.data || {}
      toast.success('Updated', { id: toastId })
      onUpdated?.({ id: updated.id || manuscriptId, status: updated.status, updated_at: updated.updated_at })
      onOpenChange(false)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Quick pre-check failed', { id: toastId })
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
          <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
            <div className="text-xs text-slate-500">Manuscript</div>
            <div className="mt-1 font-mono text-[11px] text-slate-800 break-all">{manuscriptId}</div>
            {manuscriptTitle ? <div className="mt-1 text-sm font-medium text-slate-900">{manuscriptTitle}</div> : null}
          </div>

          <div className="space-y-2">
            <Label className="text-sm">Decision</Label>
            <RadioGroup value={decision} onValueChange={(v) => setDecision(v as QuickPrecheckDecision)} className="grid gap-2">
              <div className="flex items-start gap-2 rounded-md border border-slate-200 p-3">
                <RadioGroupItem value="approve" id="qp-approve" className="mt-1" />
                <label htmlFor="qp-approve" className="flex-1 cursor-pointer">
                  <div className="font-medium">Approve (Send to review)</div>
                  <div className="text-xs text-slate-500">Moves status to Under Review</div>
                </label>
              </div>
              <div className="flex items-start gap-2 rounded-md border border-slate-200 p-3">
                <RadioGroupItem value="revision" id="qp-revision" className="mt-1" />
                <label htmlFor="qp-revision" className="flex-1 cursor-pointer">
                  <div className="font-medium">Request Revision</div>
                  <div className="text-xs text-slate-500">Moves status to Minor Revision</div>
                </label>
              </div>
              <div className="flex items-start gap-2 rounded-md border border-slate-200 p-3">
                <RadioGroupItem value="reject" id="qp-reject" className="mt-1" />
                <label htmlFor="qp-reject" className="flex-1 cursor-pointer">
                  <div className="font-medium">Reject</div>
                  <div className="text-xs text-slate-500">Moves status to Rejected</div>
                </label>
              </div>
            </RadioGroup>
          </div>

          <div className="space-y-2">
            <Label className="text-sm">
              Comment {needsComment ? <span className="text-red-600">*</span> : <span className="text-slate-400">(optional)</span>}
            </Label>
            <Textarea
              placeholder={needsComment ? 'Required for reject/revision…' : 'Optional note…'}
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

