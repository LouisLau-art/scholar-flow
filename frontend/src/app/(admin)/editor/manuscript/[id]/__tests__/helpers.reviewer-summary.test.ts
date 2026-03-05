import { describe, expect, it } from 'vitest'

import { resolveReviewerInviteSummaryState } from '@/app/(admin)/editor/manuscript/[id]/helpers'

describe('resolveReviewerInviteSummaryState', () => {
  it('returns blank for reviewer rows without invite evidence', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-blank',
        status: 'pending',
      })
    ).toBe('blank')
  })

  it('returns invited when invite timestamp exists', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-invited',
        status: 'pending',
        invited_at: '2026-03-05T00:00:00Z',
      })
    ).toBe('invited')
  })

  it('returns agree for accepted or submitted reviewers', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-accepted',
        status: 'accepted',
      })
    ).toBe('agree')

    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-submitted',
        status: 'completed',
      })
    ).toBe('agree')
  })

  it('returns decline when reviewer declined', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-decline',
        status: 'declined',
      })
    ).toBe('decline')
  })
})
