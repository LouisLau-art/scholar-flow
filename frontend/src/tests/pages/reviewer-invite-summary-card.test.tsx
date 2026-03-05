import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ReviewerInviteSummaryCard } from '@/app/(admin)/editor/manuscript/[id]/detail-sections'

describe('ReviewerInviteSummaryCard deferred state', () => {
  it('shows loading state before deferred context is loaded', () => {
    render(
      <ReviewerInviteSummaryCard
        reviewerInvites={[]}
        deferredLoaded={false}
        deferredLoading
      />
    )

    expect(screen.getByText('Reviewer summary loading...')).toBeInTheDocument()
    expect(screen.queryByText('No reviewers assigned yet.')).not.toBeInTheDocument()
  })

  it('shows empty state after deferred context has loaded', () => {
    render(
      <ReviewerInviteSummaryCard
        reviewerInvites={[]}
        deferredLoaded
        deferredLoading={false}
      />
    )

    expect(screen.getByText('No reviewers assigned yet.')).toBeInTheDocument()
  })

  it('shows retry action when deferred context fails', () => {
    const onRetry = vi.fn()
    render(
      <ReviewerInviteSummaryCard
        reviewerInvites={[]}
        deferredLoaded={false}
        deferredLoading={false}
        loadError="Deferred detail context loading timed out."
        onRetry={onRetry}
      />
    )

    expect(screen.getByText('Deferred detail context loading timed out.')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('reviewer-summary-retry'))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})
