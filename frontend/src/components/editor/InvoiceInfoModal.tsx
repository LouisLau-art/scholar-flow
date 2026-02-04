'use client'

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
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
  saving?: boolean
}) {
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Edit Invoice Info</DialogTitle>
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

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => props.onOpenChange(false)}>
              Cancel
            </Button>
            <Button disabled={!!props.saving} onClick={props.onSave}>
              {props.saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Save
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

