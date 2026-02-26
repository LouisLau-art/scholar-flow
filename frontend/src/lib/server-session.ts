import { cookies } from 'next/headers'

type SessionUser = {
  id: string
  email?: string
}

function tryParseJson<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

function decodeCookieValue(raw: string): string {
  try {
    return decodeURIComponent(raw)
  } catch {
    return raw
  }
}

function extractAccessToken(payload: unknown): string | null {
  if (!payload) return null
  if (Array.isArray(payload)) {
    for (const item of payload) {
      const token = extractAccessToken(item)
      if (token) return token
    }
    return null
  }
  if (typeof payload !== 'object') return null
  const obj = payload as Record<string, unknown>

  if (typeof obj.access_token === 'string' && obj.access_token) return obj.access_token
  if (typeof obj.token === 'string' && obj.token) return obj.token

  const nestedKeys = ['currentSession', 'session', 'data'] as const
  for (const key of nestedKeys) {
    const token = extractAccessToken(obj[key])
    if (token) return token
  }
  return null
}

function extractUser(payload: unknown): SessionUser | null {
  if (!payload || typeof payload !== 'object') return null
  const obj = payload as Record<string, unknown>
  const candidate = (obj.user && typeof obj.user === 'object' ? obj.user : obj) as Record<string, unknown>
  if (typeof candidate.id !== 'string' || !candidate.id) return null
  return {
    id: candidate.id,
    email: typeof candidate.email === 'string' ? candidate.email : undefined,
  }
}

function getSupabaseCookiePayloads(): unknown[] {
  const store = cookies()
  const sessionCookies = store
    .getAll()
    .filter((entry) => entry.name.startsWith('sb-') && entry.name.endsWith('-auth-token'))

  const payloads: unknown[] = []
  for (const entry of sessionCookies) {
    const decoded = decodeCookieValue(entry.value)
    const parsed = tryParseJson<unknown>(decoded) ?? tryParseJson<unknown>(entry.value)
    if (parsed) payloads.push(parsed)
  }
  return payloads
}

export function getServerAccessToken(): string | null {
  const payloads = getSupabaseCookiePayloads()
  for (const payload of payloads) {
    const token = extractAccessToken(payload)
    if (token) return token
  }
  return null
}

export function getServerSessionUser(): SessionUser | null {
  const payloads = getSupabaseCookiePayloads()
  for (const payload of payloads) {
    const user = extractUser(payload)
    if (user) return user
    if (typeof payload === 'object' && payload && 'data' in payload) {
      const nested = extractUser((payload as Record<string, unknown>).data)
      if (nested) return nested
    }
  }
  return null
}
