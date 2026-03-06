import { authService } from '@/services/auth'
import type {
  EmailTemplate,
  EmailTemplateCreatePayload,
  EmailTemplateUpdatePayload,
} from '@/types/email-template'

const API_BASE = '/api/v1/admin/email-templates'

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

export const adminEmailTemplateService = {
  async list(options?: { includeInactive?: boolean; scene?: string }): Promise<EmailTemplate[]> {
    const params = new URLSearchParams()
    if (options?.includeInactive) params.set('include_inactive', 'true')
    if (options?.scene && String(options.scene).trim()) params.set('scene', String(options.scene).trim())
    const qs = params.toString()
    const res = await authedFetch(`${API_BASE}${qs ? `?${qs}` : ''}`, { method: 'GET' })
    if (!res.ok) {
      throw new Error(await parseError(res, 'Failed to load email templates'))
    }
    return res.json()
  },

  async create(payload: EmailTemplateCreatePayload): Promise<EmailTemplate> {
    const res = await authedFetch(API_BASE, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      throw new Error(await parseError(res, 'Failed to create email template'))
    }
    return res.json()
  },

  async update(templateId: string, payload: EmailTemplateUpdatePayload): Promise<EmailTemplate> {
    const res = await authedFetch(`${API_BASE}/${encodeURIComponent(templateId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      throw new Error(await parseError(res, 'Failed to update email template'))
    }
    return res.json()
  },

  async deactivate(templateId: string): Promise<EmailTemplate> {
    const res = await authedFetch(`${API_BASE}/${encodeURIComponent(templateId)}`, {
      method: 'DELETE',
    })
    if (!res.ok) {
      throw new Error(await parseError(res, 'Failed to deactivate email template'))
    }
    return res.json()
  },
}
