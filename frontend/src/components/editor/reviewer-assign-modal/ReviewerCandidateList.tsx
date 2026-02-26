import { Check } from 'lucide-react'
import type { InvitePolicy, InvitePolicyHit, ReviewerWithPolicy } from './types'

type ReviewerCandidateListProps = {
  isLoading: boolean
  orderedReviewers: ReviewerWithPolicy[]
  assignedIds: string[]
  selectedReviewers: string[]
  policyByReviewerId: Record<string, InvitePolicy>
  canCurrentUserOverrideCooldown: boolean
  hasMoreReviewers: boolean
  isLoadingMoreReviewers: boolean
  reviewerPage: number
  searchTerm: string
  onToggleReviewer: (reviewerId: string) => void
  onLoadMore: (nextPage: number, query: string) => void
  isReviewerBlocked: (reviewerId: string) => boolean
  reviewerNeedsOverride: (reviewerId: string) => boolean
  getPolicyBadgeClass: (hit: InvitePolicyHit) => string
}

export function ReviewerCandidateList(props: ReviewerCandidateListProps) {
  const {
    isLoading,
    orderedReviewers,
    assignedIds,
    selectedReviewers,
    policyByReviewerId,
    canCurrentUserOverrideCooldown,
    hasMoreReviewers,
    isLoadingMoreReviewers,
    reviewerPage,
    searchTerm,
    onToggleReviewer,
    onLoadMore,
    isReviewerBlocked,
    reviewerNeedsOverride,
    getPolicyBadgeClass,
  } = props

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (orderedReviewers.length === 0) {
    return <div className="text-center py-8 text-muted-foreground">No reviewers found. Add one to the library?</div>
  }

  return (
    <div className="space-y-2" data-testid="reviewer-list">
      {orderedReviewers.map((reviewer) => {
        const policy = reviewer.invite_policy || policyByReviewerId[reviewer.id] || {}
        const isAssigned = assignedIds.includes(reviewer.id)
        const isSelected = selectedReviewers.includes(reviewer.id)
        const showAsSelected = isAssigned || isSelected
        const blockedByPolicy = !isAssigned && isReviewerBlocked(reviewer.id)
        const rowDisabled = isAssigned || blockedByPolicy
        const canOverride = !isAssigned && reviewerNeedsOverride(reviewer.id) && canCurrentUserOverrideCooldown
        const hits = (policy.hits || []).filter(Boolean)

        return (
          <button
            key={reviewer.id}
            type="button"
            data-testid={`reviewer-row-${reviewer.id}`}
            aria-pressed={isSelected}
            onClick={() => onToggleReviewer(reviewer.id)}
            disabled={rowDisabled}
            className={`w-full flex items-center justify-between p-3 rounded-lg transition-all border text-left ${
              isAssigned
                ? 'bg-primary/10 border-primary/30 shadow-sm cursor-not-allowed'
                : blockedByPolicy
                  ? 'bg-rose-50 border-rose-200 cursor-not-allowed'
                  : isSelected
                    ? 'bg-primary/10 border-primary/30 shadow-sm'
                    : 'hover:bg-muted/40 border-transparent hover:border-border'
            }`}
          >
            <div className="flex items-center gap-3">
              <div
                className={`h-10 w-10 rounded-full flex items-center justify-center text-sm font-medium ${
                  showAsSelected ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                }`}
              >
                {reviewer.full_name?.charAt(0) || (reviewer.email || '?').charAt(0)}
              </div>
              <div>
                <div className={`font-medium ${showAsSelected ? 'text-primary' : 'text-foreground'}`}>
                  {reviewer.full_name || 'Unnamed'}
                </div>
                <div className="text-sm text-muted-foreground">{reviewer.email}</div>
                {hits.length > 0 && (
                  <div className="mt-1 flex flex-wrap items-center gap-1" data-testid={`policy-hits-${reviewer.id}`}>
                    {hits.map((hit, idx) => (
                      <span
                        key={`${reviewer.id}-hit-${idx}-${hit.code}`}
                        className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-semibold ${getPolicyBadgeClass(hit)}`}
                      >
                        {hit.label || hit.code}
                      </span>
                    ))}
                  </div>
                )}
                {hits.length > 0 && <div className="mt-1 text-[11px] text-muted-foreground">{hits.map((h) => h.detail).filter(Boolean).join(' ')}</div>}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isAssigned && <span className="text-xs font-semibold bg-muted text-foreground px-2 py-1 rounded">Assigned</span>}
              {blockedByPolicy && <span className="text-xs font-semibold bg-rose-100 text-rose-700 px-2 py-1 rounded">Blocked</span>}
              {canOverride && <span className="text-xs font-semibold bg-amber-100 text-amber-700 px-2 py-1 rounded">Override</span>}
              {showAsSelected && <Check className="h-5 w-5 text-primary" />}
            </div>
          </button>
        )
      })}
      {hasMoreReviewers && (
        <div className="pt-2 flex justify-center">
          <button
            type="button"
            onClick={() => onLoadMore(reviewerPage + 1, searchTerm)}
            disabled={isLoadingMoreReviewers}
            className="px-3 py-1.5 rounded-md border border-border text-sm text-foreground hover:bg-muted/70 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            data-testid="reviewer-load-more"
          >
            {isLoadingMoreReviewers ? 'Loading…' : 'Load more'}
          </button>
        </div>
      )}
    </div>
  )
}
