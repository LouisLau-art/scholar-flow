'use client'

import { Loader2, Send } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { derivePlainTextFromHtml } from '@/lib/derive-plain-text-from-html'
import { DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { SafeDialog, SafeDialogContent } from '@/components/ui/safe-dialog'
import type { AuthorEmailPreviewData } from '@/services/editor-api/types'
import { ReviewerEmailComposeEditor } from './ReviewerEmailComposeEditor'

type AuthorEmailPreviewDialogProps = {
  open: boolean
  title?: string
  description?: string
  loading: boolean
  sending: boolean
  preview: AuthorEmailPreviewData | null
  recipientEmail: string
  ccValue: string
  replyToValue: string
  subjectValue: string
  htmlValue: string
  onSubjectChange: (value: string) => void
  onHtmlChange: (value: string) => void
  onRecipientEmailChange: (value: string) => void
  onCcChange: (value: string) => void
  onReplyToChange: (value: string) => void
  onClose: () => void
  onSend: () => void
  onMarkExternalSent?: () => void
}

export function AuthorEmailPreviewDialog({
  open,
  title = 'Preview Author Email',
  description = '发送前先确认最终收件人和渲染后的邮件内容。',
  loading,
  sending,
  preview,
  recipientEmail,
  ccValue,
  replyToValue,
  subjectValue,
  htmlValue,
  onSubjectChange,
  onHtmlChange,
  onRecipientEmailChange,
  onCcChange,
  onReplyToChange,
  onClose,
  onSend,
  onMarkExternalSent,
}: AuthorEmailPreviewDialogProps) {
  const authorEmail = String(preview?.recipient_email || '').trim().toLowerCase()
  const normalizedRecipient = String(recipientEmail || '').trim().toLowerCase()
  const recipientOverridden = Boolean(normalizedRecipient && authorEmail && normalizedRecipient !== authorEmail)
  const derivedPlainText = derivePlainTextFromHtml(htmlValue)

  return (
    <SafeDialog open={open} onClose={onClose} closeDisabled={sending}>
      <SafeDialogContent closeDisabled={sending} className="max-w-5xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            {description}
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
                  <Label htmlFor="author-email-preview-subject">Subject</Label>
                  <Input
                    id="author-email-preview-subject"
                    value={subjectValue}
                    disabled={sending}
                    onChange={(event) => onSubjectChange(event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="author-email-preview-html">Email Body</Label>
                  <ReviewerEmailComposeEditor value={htmlValue} disabled={sending} onChange={onHtmlChange} />
                </div>
              </div>

              <div className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="author-email-preview-recipient">To (Recipient)</Label>
                  <Input
                    id="author-email-preview-recipient"
                    type="email"
                    value={recipientEmail}
                    disabled={sending}
                    onChange={(event) => onRecipientEmailChange(event.target.value)}
                    placeholder={preview.recipient_email}
                    autoComplete="off"
                  />
                  <div className="text-xs text-muted-foreground">
                    默认发送给作者：<span className="font-medium text-foreground">{preview.recipient_email}</span>
                  </div>
                  {recipientOverridden ? (
                    <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                      当前收件人已更改。如果只想测试发送效果，这会发送一封预览邮件给新地址。
                    </div>
                  ) : null}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="author-email-preview-cc">CC</Label>
                  <Input
                    id="author-email-preview-cc"
                    value={ccValue}
                    disabled={sending}
                    onChange={(event) => onCcChange(event.target.value)}
                    placeholder={(preview.resolved_recipients?.cc || []).join(', ')}
                    autoComplete="off"
                  />
                  <div className="text-xs text-muted-foreground">多个邮箱可用逗号分隔。</div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="author-email-preview-reply-to">Reply-To</Label>
                  <Input
                    id="author-email-preview-reply-to"
                    value={replyToValue}
                    disabled={sending}
                    onChange={(event) => onReplyToChange(event.target.value)}
                    placeholder={(preview.resolved_recipients?.reply_to || []).join(', ')}
                    autoComplete="off"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="author-email-preview-text">Plain Text Preview</Label>
                  <Textarea
                    id="author-email-preview-text"
                    value={derivedPlainText}
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

        <DialogFooter className="flex flex-col sm:flex-row gap-2">
          {onMarkExternalSent && (
            <Button
              variant="secondary"
              onClick={onMarkExternalSent}
              disabled={sending}
              className="sm:mr-auto"
            >
              Mark as Sent Externally
            </Button>
          )}
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
