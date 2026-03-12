import type { AcademicRecommendation, DecisionLabelValue } from '@/types/decision'

export const ACADEMIC_RECOMMENDATION_OPTIONS: AcademicRecommendation[] = [
  'accept',
  'accept_after_minor_revision',
  'major_revision',
  'reject_resubmit',
  'reject_decline',
]

export function getDecisionOptionLabel(decision: DecisionLabelValue): string {
  switch (decision) {
    case 'accept':
      return 'Accept'
    case 'accept_after_minor_revision':
      return 'Accept After Minor Revision'
    case 'minor_revision':
      return 'Minor Revision'
    case 'major_revision':
      return 'Major Revision'
    case 'add_reviewer':
      return 'Add Additional Reviewer'
    case 'reject_resubmit':
      return 'Reject and Encourage Resubmitting after Revision'
    case 'reject_decline':
      return 'Reject and Decline Resubmitting'
    case 'reject':
    default:
      return 'Reject'
  }
}
