import { describe, expect, it } from 'vitest'

import { getDecisionOptionsForStage } from '@/components/editor/decision/DecisionEditor'

describe('getDecisionOptionsForStage', () => {
  it('hides accept in first decision queue', () => {
    expect(getDecisionOptionsForStage('decision')).toEqual(['minor_revision', 'major_revision', 'reject'])
    expect(getDecisionOptionsForStage('under_review')).toEqual(['minor_revision', 'major_revision', 'reject'])
  })

  it('allows accept in final decision contexts', () => {
    expect(getDecisionOptionsForStage('decision_done')).toEqual(['accept', 'minor_revision', 'major_revision', 'reject'])
  })

  it('does not expose accept before manuscript enters final decision queue', () => {
    expect(getDecisionOptionsForStage('resubmitted')).toEqual(['minor_revision', 'major_revision', 'reject'])
    expect(getDecisionOptionsForStage('under_review')).toEqual(['minor_revision', 'major_revision', 'reject'])
  })
})
