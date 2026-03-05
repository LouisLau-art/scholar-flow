import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

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
})
