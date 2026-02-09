import { authService } from '@/services/auth'
import type { ProofreadingDecision, ProductionCorrectionItem } from '@/types/production'

async function authedFetch(input: RequestInfo, init?: RequestInit) {
  const token = await authService.getAccessToken()
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (token) headers.Authorization = `Bearer ${token}`
  return fetch(input, { ...init, headers })
}

export const ManuscriptApi = {
  async getProofreadingContext(manuscriptId: string) {
    const res = await authedFetch(`/api/v1/manuscripts/${encodeURIComponent(manuscriptId)}/proofreading-context`)
    return res.json()
  },

  async getProductionGalleySignedUrl(manuscriptId: string, cycleId: string) {
    const res = await authedFetch(
      `/api/v1/manuscripts/${encodeURIComponent(manuscriptId)}/production-cycles/${encodeURIComponent(cycleId)}/galley-signed`
    )
    return res.json()
  },

  async submitProofreading(
    manuscriptId: string,
    cycleId: string,
    payload: {
      decision: ProofreadingDecision
      summary?: string
      corrections?: ProductionCorrectionItem[]
    }
  ) {
    const res = await authedFetch(
      `/api/v1/manuscripts/${encodeURIComponent(manuscriptId)}/production-cycles/${encodeURIComponent(cycleId)}/proofreading`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }
    )
    return res.json()
  },
}
