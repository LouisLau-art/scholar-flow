import { describe, expect, it } from 'vitest'

import { isReviewCompleted } from '@/lib/decision/reviewUtils'

describe('isReviewCompleted', () => {
  it('treats comments as sufficient completion evidence without score', () => {
    expect(
      isReviewCompleted({
        status: 'pending',
        comments_for_author: 'Detailed reviewer feedback',
        score: null,
      })
    ).toBe(true)
  })

  it('does not infer completion from empty review data', () => {
    expect(
      isReviewCompleted({
        status: 'pending',
        comments_for_author: '',
        confidential_comments_to_editor: '',
        score: null,
      })
    ).toBe(false)
  })
})
