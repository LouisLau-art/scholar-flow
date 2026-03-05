import { describe, expect, it } from 'vitest'

import { resolveReviewerInviteSummaryState } from '@/app/(admin)/editor/manuscript/[id]/helpers'

describe('resolveReviewerInviteSummaryState', () => {
  it('returns blank when invite evidence is empty', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-1',
        status: 'invited',
      })
    ).toBe('blank')
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

  it('returns agree for accepted/submitted evidence', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-3',
        status: 'accepted',
      })
    ).toBe('agree')

    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-4',
        status: 'submitted',
      })
    ).toBe('agree')
  })

  it('returns decline for declined evidence', () => {
    expect(
      resolveReviewerInviteSummaryState({
        id: 'ra-5',
        status: 'declined',
      })
    ).toBe('decline')
  })
})
