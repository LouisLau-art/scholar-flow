'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { User } from '@/types/user'
import { Button } from '@/components/ui/button'
import {
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { SafeDialog, SafeDialogContent } from '@/components/ui/safe-dialog'

interface ResetPasswordDialogProps {
  isOpen: boolean
  user: User | null
  onClose: () => void
  onConfirm: (userId: string) => Promise<void>
}

export function ResetPasswordDialog({ isOpen, user, onClose, onConfirm }: ResetPasswordDialogProps) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    if (!isOpen) return
    const onEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || submitting) return
      event.preventDefault()
      onClose()
    }
    window.addEventListener('keydown', onEscape)
    return () => {
      window.removeEventListener('keydown', onEscape)
    }
  }, [isOpen, onClose, submitting])

  useEffect(() => {
    if (!isOpen) {
      setSubmitting(false)
      setError(null)
    }
  }, [isOpen])

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

  if (!isOpen) return null

  return (
    <SafeDialog open={isOpen} onClose={onClose} closeDisabled={submitting}>
      <SafeDialogContent
        aria-label="Reset User Password"
        data-testid="reset-password-modal-v2"
        className="max-w-lg"
        closeDisabled={submitting}
      >
        <DialogHeader className="pr-10">
          <DialogTitle>Reset User Password</DialogTitle>
          <DialogDescription className="mt-1">
            This will send a secure password reset link to the user email.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 space-y-3 rounded-md border border-secondary-foreground/20 bg-secondary p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-secondary-foreground">
            <AlertTriangle className="h-4 w-4" />
            Sensitive operation
          </div>
          <div className="text-sm text-foreground">
            Target user: <span className="font-semibold">{user?.full_name || user?.email || '-'}</span>
          </div>
          <div className="text-sm text-foreground">
            The user will receive a recovery link and can set a new password securely.
          </div>
          <div className="text-xs text-secondary-foreground">
            No temporary password will be shown in admin panel.
          </div>
        </div>

        {error ? (
          <div className="mt-3 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
        ) : null}

        <div className="mt-4 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:space-x-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={submitting}>
            {submitting ? 'Sending Link...' : 'Send Reset Link'}
          </Button>
        </div>
      </SafeDialogContent>
    </SafeDialog>
  )
}
