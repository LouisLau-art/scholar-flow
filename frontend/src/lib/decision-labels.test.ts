import { describe, expect, it } from 'vitest'

import {
  ACADEMIC_RECOMMENDATION_OPTIONS,
  getDecisionOptionLabel,
} from '@/lib/decision-labels'

describe('decision label compatibility', () => {
  it('exposes five academic recommendation options', () => {
    expect(ACADEMIC_RECOMMENDATION_OPTIONS).toEqual([
      'accept',
      'accept_after_minor_revision',
      'major_revision',
      'reject_resubmit',
      'reject_decline',
    ])
  })

  it('returns labels for new academic recommendation values', () => {
    expect(getDecisionOptionLabel('accept_after_minor_revision')).toBe('Accept After Minor Revision')
    expect(getDecisionOptionLabel('reject_resubmit')).toBe('Reject and Encourage Resubmitting after Revision')
    expect(getDecisionOptionLabel('reject_decline')).toBe('Reject and Decline Resubmitting')
  })
})
