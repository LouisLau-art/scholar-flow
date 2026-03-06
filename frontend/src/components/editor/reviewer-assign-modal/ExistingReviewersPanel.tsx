type ExistingReviewer = {
  id: string
  reviewer_name?: string
  reviewer_email?: string
  status?: string
}

type ExistingReviewersPanelProps = {
  existingReviewers: ExistingReviewer[]
  onRequestRemove: (reviewer: ExistingReviewer) => void
}

function resolveAssignmentBadge(statusRaw: string | undefined) {
  const status = String(statusRaw || '').trim().toLowerCase()
  if (status === 'completed' || status === 'submitted') {
    return { label: 'Submitted', className: 'bg-emerald-100 text-emerald-700' }
  }
  if (status === 'accepted') {
    return { label: 'Accepted', className: 'bg-sky-100 text-sky-700' }
  }
  if (status === 'opened') {
    return { label: 'Opened', className: 'bg-indigo-100 text-indigo-700' }
  }
  if (status === 'invited') {
    return { label: 'Invited', className: 'bg-amber-100 text-amber-700' }
  }
  if (status === 'declined') {
    return { label: 'Declined', className: 'bg-rose-100 text-rose-700' }
  }
  return { label: 'Selected', className: 'bg-slate-200 text-slate-700' }
}

export function ExistingReviewersPanel(props: ExistingReviewersPanelProps) {
  const { existingReviewers, onRequestRemove } = props
  if (!existingReviewers.length) return null

  return (
    <div className="mb-6 rounded-lg border border-border bg-muted/40 p-4">
      <h3 className="font-semibold text-foreground mb-3">Current Reviewers ({existingReviewers.length})</h3>
      <div className="space-y-2">
        {existingReviewers.map((r) => {
          const badge = resolveAssignmentBadge(r.status)
          return (
            <div key={r.id} className="flex items-center justify-between bg-card p-3 rounded border border-border shadow-sm">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold">
                  {r.reviewer_name?.charAt(0) || '?'}
                </div>
                <div>
                  <div className="font-medium text-foreground text-sm">{r.reviewer_name}</div>
                  <div className="text-xs text-muted-foreground">{r.reviewer_email}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${badge.className}`}>
                  {badge.label}
                </span>
                <button
                  onClick={() => onRequestRemove(r)}
                  className="text-red-600 hover:text-red-800 text-xs font-medium px-2 py-1 rounded hover:bg-red-50 transition-colors"
                  data-testid={`reviewer-remove-${r.id}`}
                >
                  Remove
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
