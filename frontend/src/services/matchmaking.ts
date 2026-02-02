import { authService } from '@/services/auth'

export type ReviewerRecommendation = {
  reviewer_id: string
  name: string
  email: string
  match_score: number
}

export type MatchmakingAnalyzeResponse = {
  recommendations: ReviewerRecommendation[]
  insufficient_data: boolean
  message: string | null
}

export async function analyzeReviewerMatchmaking(manuscriptId: string): Promise<MatchmakingAnalyzeResponse> {
  const token = await authService.getAccessToken()
  if (!token) {
    throw new Error('Missing access token')
  }

  const res = await fetch('/api/v1/matchmaking/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ manuscript_id: manuscriptId }),
  })

  const body = await res.json()
  if (!res.ok || !body?.success) {
    throw new Error(body?.detail || body?.message || 'Matchmaking analysis failed')
  }
  return body.data as MatchmakingAnalyzeResponse
}

