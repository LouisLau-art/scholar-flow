'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import ReviewerAssignModal from '@/components/ReviewerAssignModal'
import { authService } from '@/services/auth'

export function ReviewerAssignmentSearch(props: {
  manuscriptId: string
  onChanged?: () => void
  disabled?: boolean
  currentOwnerId?: string
  currentOwnerLabel?: string
  canBindOwner?: boolean
  viewerRoles?: string[]
}) {
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const handleAssign = async (
    reviewerIds: string[],
    options?: { overrides?: Array<{ reviewerId: string; reason: string }> }
  ) => {
    if (!props.manuscriptId) return false
    setSubmitting(true)
    const toastId = toast.loading('Assigning reviewers...')
    try {
      const token = await authService.getAccessToken()
      if (!token) throw new Error('Please sign in again.')
      const overrideMap = new Map(
        (options?.overrides || []).map((item) => [String(item.reviewerId), String(item.reason || '')])
      )

      for (const reviewerId of reviewerIds) {
        const overrideReason = overrideMap.get(String(reviewerId))
        const res = await fetch('/api/v1/reviews/assign', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            manuscript_id: props.manuscriptId,
            reviewer_id: reviewerId,
            override_cooldown: Boolean(overrideReason),
            override_reason: overrideReason || undefined,
          }),
        })
        if (!res.ok) {
          const raw = await res.text().catch(() => '')
          let detail = raw
          try {
            const json = raw ? JSON.parse(raw) : null
            detail = json?.detail || json?.message || raw
          } catch {
            detail = raw
          }
          throw new Error(detail || 'Assign failed')
        }
      }

      toast.success('Assigned.', { id: toastId })
      props.onChanged?.()
      return true
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Assign failed', { id: toastId })
      return false
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <Button variant="default" className="w-full" onClick={() => setOpen(true)} disabled={submitting || Boolean(props.disabled)}>
        Manage Reviewers
      </Button>

      {open && !props.disabled && (
        <ReviewerAssignModal
          isOpen={open}
          onClose={() => setOpen(false)}
          onAssign={handleAssign}
          manuscriptId={props.manuscriptId}
          currentOwnerId={props.currentOwnerId}
          currentOwnerLabel={props.currentOwnerLabel}
          canBindOwner={props.canBindOwner}
          viewerRoles={props.viewerRoles}
        />
      )}
    </>
  )
}
