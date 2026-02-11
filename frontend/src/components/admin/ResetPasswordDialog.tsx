'use client'

import { useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { User } from '@/types/user'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface ResetPasswordDialogProps {
  isOpen: boolean
  user: User | null
  onClose: () => void
  onConfirm: (userId: string) => Promise<void>
}

export function ResetPasswordDialog({ isOpen, user, onClose, onConfirm }: ResetPasswordDialogProps) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleConfirm = async () => {
    if (!user) return
    setSubmitting(true)
    setError(null)
    try {
      await onConfirm(user.id)
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to reset password')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => (!open ? onClose() : undefined)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reset User Password</DialogTitle>
          <DialogDescription>
            This will reset the user password to a system-generated temporary value.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 rounded-md border border-amber-200 bg-amber-50 p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-amber-800">
            <AlertTriangle className="h-4 w-4" />
            Sensitive operation
          </div>
          <div className="text-sm text-amber-900">
            Target user: <span className="font-semibold">{user?.full_name || user?.email || '-'}</span>
          </div>
          <div className="text-sm text-amber-900">
            The system will generate a random temporary password for this reset.
          </div>
          <div className="text-xs text-amber-700">
            Ask the user to log in and immediately change their password in Settings.
          </div>
        </div>

        {error ? (
          <div className="rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
        ) : null}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={submitting}>
            {submitting ? 'Resetting...' : 'Confirm Reset'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
