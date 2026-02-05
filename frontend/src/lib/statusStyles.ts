export type ManuscriptStatus =
  | 'pre_check'
  | 'under_review'
  | 'major_revision'
  | 'minor_revision'
  | 'resubmitted'
  | 'decision'
  | 'decision_done'
  | 'approved'
  | 'layout'
  | 'english_editing'
  | 'proofreading'
  | 'published'
  | 'rejected'
  | string

export function getStatusLabel(status: ManuscriptStatus): string {
  switch (status) {
    case 'pre_check':
      return 'Pre-check'
    case 'under_review':
      return 'Under Review'
    case 'major_revision':
      return 'Major Revision'
    case 'minor_revision':
      return 'Minor Revision'
    case 'resubmitted':
      return 'Resubmitted'
    case 'decision':
      return 'Decision'
    case 'decision_done':
      return 'Decision Done'
    case 'approved':
      return 'Accepted'
    case 'layout':
      return 'Layout'
    case 'english_editing':
      return 'English Editing'
    case 'proofreading':
      return 'Proofreading'
    case 'published':
      return 'Published'
    case 'rejected':
      return 'Rejected'
    default:
      return status
  }
}

export function getStatusBadgeClass(status: ManuscriptStatus): string {
  switch (status) {
    case 'pre_check':
      return 'bg-slate-100 text-slate-700 border-slate-200'
    case 'under_review':
      return 'bg-blue-50 text-blue-700 border-blue-200'
    case 'decision':
    case 'decision_done':
      return 'bg-amber-100 text-amber-900 border-amber-200'
    case 'major_revision':
    case 'minor_revision':
    case 'resubmitted':
      return 'bg-violet-50 text-violet-800 border-violet-200'
    case 'approved':
    case 'layout':
    case 'english_editing':
    case 'proofreading':
      return 'bg-emerald-50 text-emerald-800 border-emerald-200'
    case 'published':
      return 'bg-indigo-100 text-indigo-700 border-indigo-200'
    case 'rejected':
      return 'bg-rose-50 text-rose-700 border-rose-200'
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200'
  }
}

// Backward-compatible alias used by some pages/components.
export function getStatusColor(status: ManuscriptStatus): string {
  return getStatusBadgeClass(status)
}
