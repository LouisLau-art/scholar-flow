import { describe, expect, it } from 'vitest'

import { resolveReviewerInviteSummaryState } from '@/app/(admin)/editor/manuscript/[id]/helpers'

describe('resolveReviewerInviteSummaryState', () => {
  it('returns selected when invite evidence is empty', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-1',
        status: 'selected',
      })
    ).toBe('selected')
  })

  it('returns invited when invited/opened evidence exists', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-2',
        status: 'invited',
        invited_at: '2026-03-05T00:00:00Z',
      })
    ).toBe('invited')
  })

  it('returns opened for opened evidence before acceptance', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-3',
        status: 'opened',
        opened_at: '2026-03-06T00:00:00Z',
      })
    ).toBe('opened')
  })

  it('returns accepted/submitted separately', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-4',
        status: 'accepted',
      })
    ).toBe('accepted')

    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-5',
        status: 'submitted',
      })
    ).toBe('submitted')
  })

  it('returns declined for declined evidence', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-6',
        status: 'declined',
      })
    ).toBe('declined')
  })
})
