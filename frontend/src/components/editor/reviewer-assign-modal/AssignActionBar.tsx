type AssignActionBarProps = {
  selectedCount: number
  overrideCount: number
  isSubmitting: boolean
  onCancel: () => void
  onAssign: () => void
}

export function AssignActionBar(props: AssignActionBarProps) {
  const { selectedCount, overrideCount, isSubmitting, onCancel, onAssign } = props

  return (
    <div className="flex items-center justify-between p-6 border-t border-border bg-muted/40">
      <button onClick={onCancel} className="px-4 py-2 text-muted-foreground hover:text-foreground transition-colors">
        Cancel
      </button>
      <button
        onClick={onAssign}
        disabled={selectedCount === 0 || isSubmitting}
        className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-colors"
        data-testid="reviewer-assign"
      >
        {isSubmitting
          ? 'Assigning…'
          : `Assign ${selectedCount || ''} Reviewer${selectedCount === 1 ? '' : 's'}${
              overrideCount ? ` (${overrideCount} override)` : ''
            }`}
      </button>
    </div>
  )
}
