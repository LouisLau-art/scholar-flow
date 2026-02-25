'use client'

import { useMemo, useState } from 'react'
import dynamic from 'next/dynamic'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { authService } from '@/services/auth'

const ReviewerAssignModal = dynamic(() => import('@/components/ReviewerAssignModal'), {
  ssr: false,
})

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
  const manuscriptId = useMemo(() => String(props.manuscriptId || '').trim(), [props.manuscriptId])
  const normalizedViewerRoles = useMemo(
    () =>
      (props.viewerRoles || [])
        .map((role) => String(role).trim().toLowerCase())
        .filter(Boolean)
        .sort(),
    [props.viewerRoles]
  )

  const handleAssign = async (
    reviewerIds: string[],
    options?: { overrides?: Array<{ reviewerId: string; reason: string }> }
  ) => {
    if (!manuscriptId) return false
    setSubmitting(true)
    const toastId = toast.loading('Assigning reviewers...')
    try {
      const token = await authService.getAccessToken()
      if (!token) throw new Error('Please sign in again.')
      const overrideMap = new Map(
        (options?.overrides || []).map((item) => [String(item.reviewerId), String(item.reason || '')])
      )
      const failures: Array<{ reviewerId: string; detail: string }> = []
      let successCount = 0

      for (const reviewerId of reviewerIds) {
        const overrideReason = overrideMap.get(String(reviewerId))
        const res = await fetch('/api/v1/reviews/assign', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            manuscript_id: manuscriptId,
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
          failures.push({ reviewerId: String(reviewerId), detail: detail || 'Assign failed' })
          continue
        }
        successCount += 1
      }

      if (successCount > 0) {
        props.onChanged?.()
      }

      if (failures.length === 0) {
        toast.success(`Assigned ${successCount} reviewer(s).`, { id: toastId })
        return true
      }

      const sample = failures[0]
      const summary = `Assigned ${successCount}, failed ${failures.length}.`
      const detailText = `${sample.reviewerId}: ${sample.detail}`
      if (successCount > 0) {
        toast.warning(`${summary} ${detailText}`, { id: toastId })
      } else {
        toast.error(sample.detail || 'Assign failed', { id: toastId })
      }
      return false
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
          manuscriptId={manuscriptId}
          currentOwnerId={props.currentOwnerId}
          currentOwnerLabel={props.currentOwnerLabel}
          canBindOwner={props.canBindOwner}
          viewerRoles={normalizedViewerRoles}
        />
      )}
    </>
  )
}
