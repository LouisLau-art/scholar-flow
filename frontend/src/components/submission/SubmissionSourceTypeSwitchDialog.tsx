'use client'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

type SubmissionSourceTypeSwitchDialogProps = {
  open: boolean
  pendingSourceType: 'word' | 'zip' | null
  onConfirm: () => void
  onCancel: () => void
}

export function SubmissionSourceTypeSwitchDialog(props: SubmissionSourceTypeSwitchDialogProps) {
  const nextLabel =
    props.pendingSourceType === 'word' ? 'Word manuscript' : props.pendingSourceType === 'zip' ? 'LaTeX source ZIP' : 'the other source type'

  return (
    <Dialog open={props.open} onOpenChange={(open) => (!open ? props.onCancel() : undefined)}>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>Switch manuscript source type?</DialogTitle>
          <DialogDescription>
            Switching to {nextLabel} will remove the currently uploaded manuscript source file. Your PDF manuscript and cover letter will be kept.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={props.onCancel}>
            Cancel
          </Button>
          <Button type="button" onClick={props.onConfirm}>
            Switch and Remove Current File
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
