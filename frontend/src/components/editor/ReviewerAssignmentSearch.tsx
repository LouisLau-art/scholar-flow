'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import ReviewerAssignModal from '@/components/ReviewerAssignModal'
import { authService } from '@/services/auth'

export function ReviewerAssignmentSearch(props: { manuscriptId: string; onChanged?: () => void }) {
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const handleAssign = async (reviewerIds: string[]) => {
    if (!props.manuscriptId) return false
    setSubmitting(true)
    const toastId = toast.loading('Assigning reviewers...')
    try {
      const token = await authService.getAccessToken()
      if (!token) throw new Error('Please sign in again.')

      for (const reviewerId of reviewerIds) {
        const res = await fetch('/api/v1/reviews/assign', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ manuscript_id: props.manuscriptId, reviewer_id: reviewerId }),
        })
        if (!res.ok) {
          const text = await res.text().catch(() => '')
          throw new Error(text || 'Assign failed')
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
      <Button variant="default" className="w-full" onClick={() => setOpen(true)} disabled={submitting}>
        Manage Reviewers
      </Button>

      {open && (
        <ReviewerAssignModal
          isOpen={open}
          onClose={() => setOpen(false)}
          onAssign={handleAssign}
          manuscriptId={props.manuscriptId}
        />
      )}
    </>
  )
}

