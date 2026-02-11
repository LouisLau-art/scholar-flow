import { authService } from '@/services/auth'
import type { Journal, JournalCreatePayload, JournalUpdatePayload } from '@/types/journal'

const API_BASE = '/api/v1/admin/journals'

async function authedFetch(input: RequestInfo, init?: RequestInit): Promise<Response> {
  const token = await authService.getAccessToken()
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
    'Content-Type': 'application/json',
  }
  if (token) headers.Authorization = `Bearer ${token}`
  return fetch(input, { ...init, headers })
}

async function parseError(response: Response, fallback: string): Promise<string> {
  try {
    const json = await response.json()
    return String(json?.detail || json?.message || fallback)
  } catch {
    return fallback
  }
}

export const adminJournalService = {
  async list(includeInactive = false): Promise<Journal[]> {
    const query = includeInactive ? '?include_inactive=true' : ''
    const res = await authedFetch(`${API_BASE}${query}`, { method: 'GET' })
    if (!res.ok) {
      throw new Error(await parseError(res, 'Failed to load journals'))
    }
    return res.json()
  },

  async create(payload: JournalCreatePayload): Promise<Journal> {
    const res = await authedFetch(API_BASE, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      throw new Error(await parseError(res, 'Failed to create journal'))
    }
    return res.json()
  },

  async update(journalId: string, payload: JournalUpdatePayload): Promise<Journal> {
    const res = await authedFetch(`${API_BASE}/${encodeURIComponent(journalId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      throw new Error(await parseError(res, 'Failed to update journal'))
    }
    return res.json()
  },

  async deactivate(journalId: string): Promise<Journal> {
    const res = await authedFetch(`${API_BASE}/${encodeURIComponent(journalId)}`, {
      method: 'DELETE',
    })
    if (!res.ok) {
      throw new Error(await parseError(res, 'Failed to deactivate journal'))
    }
    return res.json()
  },
}
