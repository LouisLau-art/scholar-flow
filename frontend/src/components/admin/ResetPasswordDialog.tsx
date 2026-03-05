'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, X } from 'lucide-react'
import { User } from '@/types/user'
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
    <div className="fixed inset-0 z-[80] flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Dismiss modal"
        className="absolute inset-0 bg-black/70"
        onClick={() => {
          if (!submitting) onClose()
        }}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label="Reset User Password"
        data-testid="reset-password-modal-v2"
        className="relative z-[81] w-full max-w-lg rounded-lg border border-border bg-background p-6 shadow-lg"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="absolute right-4 top-4 rounded-sm opacity-70 hover:opacity-100"
          aria-label="Close"
          disabled={submitting}
          onClick={() => {
            if (!submitting) onClose()
          }}
        >
          <X className="h-4 w-4" />
        </Button>

        <div className="pr-10">
          <h2 className="text-lg font-semibold leading-none tracking-tight">Reset User Password</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            This will reset the user password to a system-generated temporary value.
          </p>
        </div>

        <div className="mt-4 space-y-3 rounded-md border border-secondary-foreground/20 bg-secondary p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-secondary-foreground">
            <AlertTriangle className="h-4 w-4" />
            Sensitive operation
          </div>
          <div className="text-sm text-foreground">
            Target user: <span className="font-semibold">{user?.full_name || user?.email || '-'}</span>
          </div>
          <div className="text-sm text-foreground">
            The system will generate a random temporary password for this reset.
          </div>
          <div className="text-xs text-secondary-foreground">
            Ask the user to log in and immediately change their password in Settings.
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
            {submitting ? 'Resetting...' : 'Confirm Reset'}
          </Button>
        </div>
      </div>
    </div>
  )
}
