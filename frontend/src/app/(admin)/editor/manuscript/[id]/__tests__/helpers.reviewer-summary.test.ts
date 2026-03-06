import { describe, expect, it } from 'vitest'

import { resolveReviewerInviteSummaryState } from '@/app/(admin)/editor/manuscript/[id]/helpers'

describe('resolveReviewerInviteSummaryState', () => {
  it('returns selected for reviewer rows without invitation evidence', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-blank',
        status: 'selected',
      })
    ).toBe('selected')
  })

  it('returns invited when invite timestamp exists', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-invited',
        status: 'invited',
        invited_at: '2026-03-05T00:00:00Z',
      })
    ).toBe('invited')
  })

  it('returns opened when reviewer has opened invite but not accepted', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-opened',
        status: 'opened',
        opened_at: '2026-03-06T00:00:00Z',
      })
    ).toBe('opened')
  })

  it('returns accepted for accepted reviewers', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-accepted',
        status: 'accepted',
      })
    ).toBe('accepted')
  })

  it('returns submitted for submitted reviewers', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-submitted',
        status: 'completed',
      })
    ).toBe('submitted')
  })

  it('returns declined when reviewer declined', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-decline',
        status: 'declined',
      })
    ).toBe('declined')
  })
})
