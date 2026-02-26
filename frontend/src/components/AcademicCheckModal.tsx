import React, { useState } from 'react'
import { editorService } from '../services/editorService'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { UI_COPY } from '@/lib/ui-copy'

interface AcademicCheckModalProps {
  isOpen: boolean
  onClose: () => void
  manuscriptId: string
  onSuccess: () => void
}

export const AcademicCheckModal: React.FC<AcademicCheckModalProps> = ({ isOpen, onClose, manuscriptId, onSuccess }) => {
  const [decision, setDecision] = useState<string>('')
  const [comment, setComment] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string>('')

  const handleSubmit = async () => {
    if (!decision) return
    setIsSubmitting(true)
    setError('')
    try {
      await editorService.submitAcademicCheck(
        manuscriptId,
        decision as 'review' | 'decision_phase',
        comment || undefined
      )
      onSuccess()
      onClose()
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to submit check')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => (!open ? onClose() : undefined)}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Academic Pre-check Decision</DialogTitle>
          <DialogDescription>Choose the next route for this manuscript.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <RadioGroup value={decision} onValueChange={setDecision} className="space-y-3">
            <div className="flex items-start gap-2">
              <RadioGroupItem id="academic-check-review" value="review" />
              <Label htmlFor="academic-check-review" className="cursor-pointer text-sm font-medium">
                Send to External Review
              </Label>
            </div>
            <div className="flex items-start gap-2">
              <RadioGroupItem id="academic-check-decision" value="decision_phase" />
              <Label htmlFor="academic-check-decision" className="cursor-pointer text-sm font-medium">
                Proceed to Decision Phase (Reject/Revision)
              </Label>
            </div>
          </RadioGroup>

          <div className="space-y-1.5">
            <Label htmlFor="academic-check-comment">Comment (Optional)</Label>
            <Textarea
              id="academic-check-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              maxLength={2000}
              disabled={isSubmitting}
              placeholder="Add context for review/decision route..."
              className="min-h-[96px]"
            />
            {error ? <div className="text-xs text-red-600">{error}</div> : null}
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="button" onClick={handleSubmit} disabled={!decision || isSubmitting}>
            {isSubmitting ? UI_COPY.submitting : 'Submit'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
