import { describe, expect, it } from 'vitest'

import { getDecisionOptionsForStage } from '@/components/editor/decision/DecisionEditor'

describe('getDecisionOptionsForStage', () => {
  it('shows add reviewer in first decision queue but still hides accept', () => {
    expect(getDecisionOptionsForStage('decision')).toEqual(['minor_revision', 'major_revision', 'reject', 'add_reviewer'])
  })

  it('allows accept in final decision contexts but not add reviewer', () => {
    expect(getDecisionOptionsForStage('decision_done')).toEqual(['accept', 'minor_revision', 'major_revision', 'reject'])
  })

  it('does not expose decision workspace options before manuscript enters decision queues', () => {
    expect(getDecisionOptionsForStage('resubmitted')).toEqual([])
    expect(getDecisionOptionsForStage('under_review')).toEqual([])
    expect(getDecisionOptionsForStage('pre_check')).toEqual([])
  })
})
