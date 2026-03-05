'use client'

import * as React from 'react'

import { Dialog, DialogContent } from '@/components/ui/dialog'

interface SafeDialogProps extends Omit<React.ComponentProps<typeof Dialog>, 'open' | 'onOpenChange'> {
  open: boolean
  onClose: () => void
  closeDisabled?: boolean
}

export function SafeDialog({ open, onClose, closeDisabled = false, ...props }: SafeDialogProps) {
  const handleOpenChange = React.useCallback(
    (nextOpen: boolean) => {
      if (nextOpen || closeDisabled) return
      onClose()
    },
    [closeDisabled, onClose]
  )

  return <Dialog open={open} onOpenChange={handleOpenChange} {...props} />
}

interface SafeDialogContentProps extends React.ComponentProps<typeof DialogContent> {
  closeDisabled?: boolean
}

export const SafeDialogContent = React.forwardRef<
  React.ElementRef<typeof DialogContent>,
  SafeDialogContentProps
>(
  (
    {
      closeDisabled = false,
      onEscapeKeyDown,
      onPointerDownOutside,
      onInteractOutside,
      ...props
    },
    ref
  ) => {
    const handleEscapeKeyDown = React.useCallback(
      (event: Parameters<NonNullable<React.ComponentProps<typeof DialogContent>['onEscapeKeyDown']>>[0]) => {
        if (closeDisabled) event.preventDefault()
        onEscapeKeyDown?.(event)
      },
      [closeDisabled, onEscapeKeyDown]
    )

    const handlePointerDownOutside = React.useCallback(
      (event: Parameters<NonNullable<React.ComponentProps<typeof DialogContent>['onPointerDownOutside']>>[0]) => {
        if (closeDisabled) event.preventDefault()
        onPointerDownOutside?.(event)
      },
      [closeDisabled, onPointerDownOutside]
    )

    const handleInteractOutside = React.useCallback(
      (event: Parameters<NonNullable<React.ComponentProps<typeof DialogContent>['onInteractOutside']>>[0]) => {
        if (closeDisabled) event.preventDefault()
        onInteractOutside?.(event)
      },
      [closeDisabled, onInteractOutside]
    )

    return (
      <DialogContent
        ref={ref}
        onEscapeKeyDown={handleEscapeKeyDown}
        onPointerDownOutside={handlePointerDownOutside}
        onInteractOutside={handleInteractOutside}
        {...props}
      />
    )
  }
)
SafeDialogContent.displayName = 'SafeDialogContent'

export function useDialogReopenGuard(reopenGuardMs = 300) {
  const reopenGuardUntilRef = React.useRef(0)

  const canOpen = React.useCallback(() => Date.now() >= reopenGuardUntilRef.current, [])

  const markClosed = React.useCallback(() => {
    reopenGuardUntilRef.current = Date.now() + reopenGuardMs
  }, [reopenGuardMs])

  return React.useMemo(
    () => ({
      canOpen,
      markClosed,
    }),
    [canOpen, markClosed]
  )
}
