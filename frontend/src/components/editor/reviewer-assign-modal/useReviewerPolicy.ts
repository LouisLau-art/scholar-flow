import { useCallback, useMemo } from 'react'
import type { InvitePolicy, InvitePolicyHit } from './types'

type UseReviewerPolicyParams = {
  policyByReviewerId: Record<string, InvitePolicy>
  assignedIds: string[]
}

export function useReviewerPolicy(params: UseReviewerPolicyParams) {
  const { policyByReviewerId, assignedIds } = params
  const assignedIdSet = useMemo(() => new Set(assignedIds), [assignedIds])

  const isReviewerBlocked = useCallback(
    (reviewerId: string) => {
      if (assignedIdSet.has(reviewerId)) return false
      const policy = policyByReviewerId[reviewerId] || {}
      return Boolean(policy.conflict)
    },
    [assignedIdSet, policyByReviewerId]
  )

  const reviewerNeedsOverride = useCallback(
    (reviewerId: string) => {
      const policy = policyByReviewerId[reviewerId] || {}
      return Boolean(policy.cooldown_active && policy.allow_override)
    },
    [policyByReviewerId]
  )

  const getPolicyBadgeClass = useCallback((hit: InvitePolicyHit) => {
    const severity = String(hit.severity || '').toLowerCase()
    if (severity === 'error') return 'bg-rose-100 text-rose-700 border-rose-200'
    if (severity === 'warning') return 'bg-amber-100 text-amber-700 border-amber-200'
    return 'bg-sky-100 text-sky-700 border-sky-200'
  }, [])

  return {
    isReviewerBlocked,
    reviewerNeedsOverride,
    getPolicyBadgeClass,
  }
}
