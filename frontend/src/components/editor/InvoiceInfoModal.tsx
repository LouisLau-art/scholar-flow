'use client'

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Loader2 } from 'lucide-react'

export type InvoiceInfoForm = {
  authors: string
  affiliation: string
  apcAmount: string
  fundingInfo: string
}

export function InvoiceInfoModal(props: {
  open: boolean
  onOpenChange: (open: boolean) => void
  form: InvoiceInfoForm
  onChange: (patch: Partial<InvoiceInfoForm>) => void
  onSave: () => Promise<void> | void
  onSaveAndSend?: () => Promise<void> | void
  saving?: boolean
  sendingEmail?: boolean
  canSendEmail?: boolean
  invoiceNumber?: string | null
}) {
  const actionBusy = Boolean(props.saving || props.sendingEmail)

  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Edit Invoice Info</DialogTitle>
          <DialogDescription>
            Confirm the author, affiliation, APC amount, and funding details before saving or sending the invoice email.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <Input
            placeholder="Authors"
            value={props.form.authors}
            onChange={(e) => props.onChange({ authors: e.target.value })}
          />
          <Input
            placeholder="Affiliation"
            value={props.form.affiliation}
            onChange={(e) => props.onChange({ affiliation: e.target.value })}
          />
          <Input
            placeholder="APC Amount (USD)"
            inputMode="decimal"
            value={props.form.apcAmount}
            onChange={(e) => props.onChange({ apcAmount: e.target.value })}
          />
          <Textarea
            placeholder="Funding Info"
            value={props.form.fundingInfo}
            onChange={(e) => props.onChange({ fundingInfo: e.target.value })}
          />

          {props.canSendEmail ? (
            <div className="rounded-md border border-border/70 bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
              <div className="font-medium text-foreground">
                {props.invoiceNumber ? `Invoice ${props.invoiceNumber}` : 'Invoice email ready'}
              </div>
              <div>Invoice email will be sent with PDF attachment once the invoice info is confirmed.</div>
            </div>
          ) : null}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => props.onOpenChange(false)}>
              Cancel
            </Button>
            <Button disabled={actionBusy} onClick={props.onSave}>
              {props.saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Save
            </Button>
            {props.canSendEmail && props.onSaveAndSend ? (
              <Button disabled={actionBusy} onClick={props.onSaveAndSend}>
                {props.sendingEmail ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Save & Send Invoice Email
              </Button>
            ) : null}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
