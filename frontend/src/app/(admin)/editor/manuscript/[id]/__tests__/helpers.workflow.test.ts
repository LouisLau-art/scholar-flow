import { describe, expect, it } from 'vitest'

import { allowedNext, getNextActionCard } from '@/app/(admin)/editor/manuscript/[id]/helpers'

describe('workflow helpers', () => {
  it('routes pre-check technical return to revision_before_review', () => {
    expect(allowedNext('pre_check')).toEqual(['under_review', 'revision_before_review'])
  })

  it('allows internal editors to send academic pre-check manuscripts to decision', () => {
    expect(allowedNext('pre_check', { preCheckStatus: 'academic' })).toEqual([
      'under_review',
      'decision',
      'revision_before_review',
    ])
  })

  it('keeps review-stage direct actions out of manual status buttons', () => {
    expect(allowedNext('under_review')).toEqual(['decision'])
    expect(allowedNext('resubmitted')).toEqual(['under_review', 'decision'])
  })

  it('describes review-stage exit using direct revision and decision actions', () => {
    const nextAction = getNextActionCard({ status: 'under_review', reviewer_invites: [] } as any, {
      canRecordFirstDecision: true,
      canSubmitFinalDecision: false,
    } as any)

    expect(nextAction.phase).toBe('External Review')
    expect(nextAction.title).toContain('Exit Review Stage')
    expect(nextAction.description).toContain('major/minor revision')
    expect(nextAction.description).toContain('AE recommendation')
    expect(nextAction.blockers).toContain('尚未发出审稿邀请')
  })

  it('keeps review-stage copy neutral for detail viewers without action permissions', () => {
    const nextAction = getNextActionCard({ status: 'under_review', reviewer_invites: [] } as any, {
      canManageReviewers: false,
      canRecordFirstDecision: false,
      canSubmitFinalDecision: false,
    } as any)

    expect(nextAction.phase).toBe('External Review')
    expect(nextAction.title).not.toContain('Exit Review Stage')
    expect(nextAction.description).not.toContain('Exit Review Stage')
    expect(nextAction.blockers).toContain('当前账号无外审收口或决策权限')
  })

  it('describes revision_before_review as waiting for author technical resubmission', () => {
    const nextAction = getNextActionCard({ status: 'revision_before_review' } as any, {} as any)

    expect(nextAction.phase).toBe('Author Revision')
    expect(nextAction.title).toContain('外审前技术修回')
    expect(nextAction.description).toContain('pre-check')
  })
})
