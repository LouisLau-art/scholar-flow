import { createRef } from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ReviewerFeedbackSummaryCard } from '@/app/(admin)/editor/manuscript/[id]/detail-sections'

describe('ReviewerFeedbackSummaryCard', () => {
  it('does not render placeholder score badges for reviewer reports', () => {
    render(
      <ReviewerFeedbackSummaryCard
        canViewReviewerFeedback
        reviewCardRef={createRef<HTMLDivElement>()}
        reviewsActivated
        reviewsLoading={false}
        reviewsError={null}
        onRetry={() => {}}
        reviewReports={[
          {
            id: 'rr-1',
            reviewer_name: 'ReviewerLouis',
            status: 'completed',
            score: 5,
            comments_for_author: '很棒',
            confidential_comments_to_editor: '不行',
            created_at: '2026-03-09T07:28:00Z',
          },
        ]}
      />
    )

    expect(screen.queryByText(/Score 5/i)).not.toBeInTheDocument()
    expect(screen.getByText('completed')).toBeInTheDocument()
    expect(screen.getByText('很棒')).toBeInTheDocument()
  })
})
