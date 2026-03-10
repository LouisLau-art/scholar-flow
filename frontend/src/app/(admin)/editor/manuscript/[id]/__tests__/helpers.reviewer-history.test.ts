import { describe, expect, it } from 'vitest'

import {
  formatReviewerHistoryAssignmentState,
  formatReviewerHistoryDecisionSummary,
} from '@/app/(admin)/editor/manuscript/[id]/helpers'

describe('reviewer history helpers', () => {
  it('renders accepted label from pending assignment with accepted timestamp', () => {
    expect(
      formatReviewerHistoryAssignmentState({
        assignment_status: 'pending',
        accepted_at: '2026-03-10T00:06:00Z',
      })
    ).toBe('Accepted')
  })

  it('renders cancelled summary with reason', () => {
    expect(
      formatReviewerHistoryDecisionSummary({
        assignment_status: 'cancelled',
        cancelled_at: '2026-03-10T00:06:00Z',
        cancel_reason: 'Enough reviews received',
      })
    ).toBe('Cancelled · Enough reviews received')
  })

  it('renders declined summary with humanized reason and note', () => {
    expect(
      formatReviewerHistoryDecisionSummary({
        assignment_status: 'declined',
        decline_reason: 'too_busy',
        decline_note: 'On leave this week',
      })
    ).toBe('Too busy · On leave this week')
  })
})
