import type { ReviewerRecommendation } from '@/services/matchmaking'

type AiRecommendationPanelProps = {
  manuscriptId: string
  aiLoading: boolean
  aiMessage: string | null
  aiRecommendations: ReviewerRecommendation[]
  selectedReviewers: string[]
  onAnalyze: () => void
  onInvite: (reviewerId: string) => void
  isReviewerBlocked: (reviewerId: string) => boolean
}

export function AiRecommendationPanel(props: AiRecommendationPanelProps) {
  const { manuscriptId, aiLoading, aiMessage, aiRecommendations, selectedReviewers, onAnalyze, onInvite, isReviewerBlocked } = props

  return (
    <div className="mb-6 rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="font-semibold text-foreground">AI Recommendations</div>
        <button
          type="button"
          onClick={onAnalyze}
          disabled={aiLoading || !manuscriptId}
          className="px-3 py-2 text-sm font-semibold rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-colors"
          data-testid="ai-analyze"
        >
          {aiLoading ? 'Analyzing...' : 'AI Analysis'}
        </button>
      </div>

      {aiLoading && (
        <div className="mt-3 flex items-center text-sm text-muted-foreground">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
          <span className="ml-2">Running local embedding match...</span>
        </div>
      )}

      {!aiLoading && aiMessage && (
        <div className="mt-3 text-sm text-muted-foreground" data-testid="ai-message">
          {aiMessage}
        </div>
      )}

      {!aiLoading && aiRecommendations.length > 0 && (
        <div className="mt-4 space-y-2" data-testid="ai-recommendations">
          {aiRecommendations.map((rec) => {
            const isSelected = selectedReviewers.includes(rec.reviewer_id)
            const blocked = isReviewerBlocked(rec.reviewer_id)
            return (
              <div key={rec.reviewer_id} className="flex items-center justify-between rounded-md border border-border p-3 hover:bg-muted/40">
                <div className="min-w-0">
                  <div className="font-medium text-foreground truncate">{rec.name || rec.email}</div>
                  <div className="text-xs text-muted-foreground truncate">{rec.email}</div>
                  <div className="text-xs text-muted-foreground mt-1">Match Score: {(rec.match_score * 100).toFixed(1)}%</div>
                </div>
                <button
                  type="button"
                  onClick={() => onInvite(rec.reviewer_id)}
                  disabled={blocked}
                  className={`ml-3 px-3 py-2 text-sm font-semibold rounded-md transition-colors ${
                    blocked
                      ? 'bg-muted text-muted-foreground cursor-not-allowed'
                      : isSelected
                        ? 'bg-green-100 text-green-700 hover:bg-green-200'
                        : 'bg-primary text-white hover:bg-primary/90'
                  }`}
                  data-testid={`ai-invite-${rec.reviewer_id}`}
                >
                  {blocked ? 'Blocked' : isSelected ? 'Selected' : 'Select'}
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
