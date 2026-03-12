import { describe, expect, it } from 'vitest'

import { getDecisionOptionLabel, getDecisionOptionsForStage } from '@/components/editor/decision/DecisionEditor'

describe('getDecisionOptionsForStage', () => {
  it('uses five academic recommendation options in recommendation mode', () => {
    expect(getDecisionOptionsForStage('decision', 'recommendation')).toEqual([
      'accept',
      'accept_after_minor_revision',
      'major_revision',
      'reject_resubmit',
      'reject_decline',
    ])
  })

  it('keeps workflow execution options for internal editors', () => {
    expect(getDecisionOptionsForStage('decision', 'execute')).toEqual([
      'minor_revision',
      'major_revision',
      'reject',
      'add_reviewer',
    ])
    expect(getDecisionOptionsForStage('decision_done', 'execute')).toEqual([
      'accept',
      'minor_revision',
      'major_revision',
      'reject',
    ])
  })

  it('uses add additional reviewer label for add_reviewer option', () => {
    expect(getDecisionOptionLabel('add_reviewer')).toBe('Add Additional Reviewer')
  })

  it('does not expose decision workspace options before manuscript enters decision queues', () => {
    expect(getDecisionOptionsForStage('resubmitted', 'execute')).toEqual([])
    expect(getDecisionOptionsForStage('under_review', 'recommendation')).toEqual([])
    expect(getDecisionOptionsForStage('pre_check', 'execute')).toEqual([])
  })
})
