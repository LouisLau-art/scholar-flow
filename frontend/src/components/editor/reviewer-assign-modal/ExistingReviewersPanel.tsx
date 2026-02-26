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

export function ExistingReviewersPanel(props: ExistingReviewersPanelProps) {
  const { existingReviewers, onRequestRemove } = props
  if (!existingReviewers.length) return null

  return (
    <div className="mb-6 rounded-lg border border-border bg-muted/40 p-4">
      <h3 className="font-semibold text-foreground mb-3">Current Reviewers ({existingReviewers.length})</h3>
      <div className="space-y-2">
        {existingReviewers.map((r) => (
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
              <span
                className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                  r.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                }`}
              >
                {r.status}
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
        ))}
      </div>
    </div>
  )
}
