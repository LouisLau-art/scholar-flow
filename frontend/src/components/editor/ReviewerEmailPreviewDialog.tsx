'use client'

import { Loader2, Mail, Send } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { SafeDialog, SafeDialogContent } from '@/components/ui/safe-dialog'
import type { ReviewerEmailPreviewData } from '@/app/(admin)/editor/manuscript/[id]/types'

type ReviewerEmailPreviewDialogProps = {
  open: boolean
  loading: boolean
  sending: boolean
  preview: ReviewerEmailPreviewData | null
  recipientEmail: string
  onRecipientEmailChange: (value: string) => void
  onClose: () => void
  onSend: () => void
}

export function ReviewerEmailPreviewDialog({
  open,
  loading,
  sending,
  preview,
  recipientEmail,
  onRecipientEmailChange,
  onClose,
  onSend,
}: ReviewerEmailPreviewDialogProps) {
  const reviewerEmail = String(preview?.reviewer_email || '').trim().toLowerCase()
  const normalizedRecipient = String(recipientEmail || '').trim().toLowerCase()
  const recipientOverridden = Boolean(normalizedRecipient && reviewerEmail && normalizedRecipient !== reviewerEmail)

  return (
    <SafeDialog open={open} onClose={onClose} closeDisabled={sending}>
      <SafeDialogContent closeDisabled={sending} className="max-w-5xl">
        <DialogHeader>
          <DialogTitle>Preview Reviewer Email</DialogTitle>
          <DialogDescription>
            发送前先确认最终收件人和渲染后的邮件内容。若收件人不是 reviewer 本人，本次仅作为预览/测试发送，不推进 reviewer 邀请状态。
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex min-h-[320px] items-center justify-center text-sm text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            正在渲染邮件预览...
          </div>
        ) : preview ? (
          <div className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
              <div className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="reviewer-email-preview-subject">Subject</Label>
                  <Input id="reviewer-email-preview-subject" value={preview.subject} readOnly />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="reviewer-email-preview-html">HTML Preview</Label>
                  <div className="overflow-hidden rounded-md border bg-white">
                    <iframe
                      id="reviewer-email-preview-html"
                      title="Reviewer email HTML preview"
                      srcDoc={preview.html}
                      className="h-[420px] w-full bg-white"
                      sandbox=""
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="reviewer-email-preview-recipient">Recipient</Label>
                  <Input
                    id="reviewer-email-preview-recipient"
                    type="email"
                    value={recipientEmail}
                    onChange={(event) => onRecipientEmailChange(event.target.value)}
                    placeholder={preview.reviewer_email}
                    autoComplete="off"
                  />
                  <div className="text-xs text-muted-foreground">
                    默认发送给 reviewer：<span className="font-medium text-foreground">{preview.reviewer_email}</span>
                  </div>
                  {recipientOverridden ? (
                    <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                      当前收件人已改为非 reviewer 邮箱。本次只会发送测试/预览邮件，不会推进 assignment 到 invited，也不会影响稿件状态。
                    </div>
                  ) : null}
                </div>

                <div className="rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
                  <div className="flex items-center gap-2 font-medium text-foreground">
                    <Mail className="h-3.5 w-3.5" />
                    {preview.template_display_name || preview.template_key}
                  </div>
                  <div className="mt-2 space-y-1">
                    <div>Event: {preview.event_type}</div>
                    <div>Journal: {preview.journal_title || 'ScholarFlow Journal'}</div>
                    <div>Review URL: {preview.review_url}</div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="reviewer-email-preview-text">Plain Text</Label>
                  <Textarea
                    id="reviewer-email-preview-text"
                    value={preview.text}
                    readOnly
                    className="min-h-[220px] resize-y text-xs"
                  />
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="min-h-[240px] rounded-md border border-dashed border-border/70 bg-muted/20 p-6 text-sm text-muted-foreground">
            邮件预览不可用。
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={sending}>
            Cancel
          </Button>
          <Button onClick={onSend} disabled={loading || !preview || !recipientEmail.trim() || sending}>
            {sending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
            {recipientOverridden ? 'Send Preview Email' : 'Send Email'}
          </Button>
        </DialogFooter>
      </SafeDialogContent>
    </SafeDialog>
  )
}
