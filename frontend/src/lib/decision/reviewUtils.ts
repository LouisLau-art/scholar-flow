export type ReviewFeedbackLike = {
  status?: string | null
  score?: number | string | null
  comments_for_author?: string | null
  confidential_comments_to_editor?: string | null
}

export function getScoreNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'string') {
    const n = Number(value)
    return Number.isFinite(n) ? n : null
  }
  return null
}

export function isReviewCompleted(review: ReviewFeedbackLike): boolean {
  const status = String(review.status || '').toLowerCase()
  if (status === 'completed' || status === 'submitted' || status === 'done') return true
  if (getScoreNumber(review.score) !== null) return true
  if ((review.comments_for_author || '').trim()) return true
  if ((review.confidential_comments_to_editor || '').trim()) return true
  return false
}

export function getLatestRevisionDecisionType(
  revisions: Array<{ round_number?: number | null; decision_type?: string | null }>
): 'major' | 'minor' | null {
  const latest = revisions.reduce((acc, cur) => {
    if (!acc) return cur
    if ((cur?.round_number ?? 0) > (acc?.round_number ?? 0)) return cur
    return acc
  }, null as { round_number?: number | null; decision_type?: string | null } | null)

  const value = String(latest?.decision_type || '').toLowerCase()
  return value === 'major' || value === 'minor' ? (value as 'major' | 'minor') : null
}
