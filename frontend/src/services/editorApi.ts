import { authService } from '@/services/auth'

export type ManuscriptsProcessFilters = {
  journalId?: string
  manuscriptId?: string
  statuses?: string[]
  ownerId?: string
  editorId?: string
}

async function authedFetch(input: RequestInfo, init?: RequestInit) {
  const token = await authService.getAccessToken()
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (token) headers.Authorization = `Bearer ${token}`
  return fetch(input, { ...init, headers })
}

export const EditorApi = {
  async listJournals() {
    const res = await authedFetch('/api/v1/editor/journals')
    return res.json()
  },

  async listInternalStaff(search?: string) {
    const qs = search ? `?search=${encodeURIComponent(search)}` : ''
    const res = await authedFetch(`/api/v1/editor/internal-staff${qs}`)
    return res.json()
  },

  async getManuscriptsProcess(filters: ManuscriptsProcessFilters) {
    const params = new URLSearchParams()
    if (filters.journalId) params.set('journal_id', filters.journalId)
    if (filters.manuscriptId) params.set('manuscript_id', filters.manuscriptId)
    if (filters.ownerId) params.set('owner_id', filters.ownerId)
    if (filters.editorId) params.set('editor_id', filters.editorId)
    for (const s of filters.statuses || []) params.append('status', s)
    const qs = params.toString()
    const res = await authedFetch(`/api/v1/editor/manuscripts/process${qs ? `?${qs}` : ''}`)
    return res.json()
  },

  async getManuscriptDetail(manuscriptId: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}`)
    return res.json()
  },

  async patchManuscriptStatus(manuscriptId: string, status: string, comment?: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, comment }),
    })
    return res.json()
  },

  async updateInvoiceInfo(
    manuscriptId: string,
    payload: { authors?: string; affiliation?: string; apc_amount?: number; funding_info?: string }
  ) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/invoice-info`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return res.json()
  },

  async bindOwner(manuscriptId: string, ownerId: string) {
    const res = await authedFetch(`/api/v1/editor/manuscripts/${manuscriptId}/bind-owner`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner_id: ownerId }),
    })
    return res.json()
  },
}
