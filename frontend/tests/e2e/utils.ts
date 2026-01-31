import type { Page, Route } from '@playwright/test'
import crypto from 'crypto'

const SUPABASE_STORAGE_KEY = 'sb-mmvulyrfsorqdpdrzbkd-auth-token'

function base64UrlEncode(input: string | Buffer) {
  const buf = typeof input === 'string' ? Buffer.from(input, 'utf8') : input
  return buf.toString('base64').replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_')
}

function signHs256(data: string, secret: string) {
  return base64UrlEncode(crypto.createHmac('sha256', secret).update(data).digest())
}

export function createTestJwt(
  payload: Record<string, unknown>,
  secret = process.env.E2E_JWT_SECRET || 'mock-secret-replace-later',
) {
  const header = { alg: 'HS256', typ: 'JWT' }
  const encodedHeader = base64UrlEncode(JSON.stringify(header))
  const encodedPayload = base64UrlEncode(JSON.stringify(payload))
  const signingInput = `${encodedHeader}.${encodedPayload}`
  const signature = signHs256(signingInput, secret)
  return `${signingInput}.${signature}`
}

export function buildSession(
  userId = '00000000-0000-0000-0000-000000000000',
  email = 'test@example.com',
) {
  const now = Math.floor(Date.now() / 1000)
  const access_token = createTestJwt({
    sub: userId,
    email,
    aud: 'authenticated',
    iat: now,
    exp: now + 3600,
  })
  return {
    access_token,
    refresh_token: 'test-refresh-token',
    token_type: 'bearer',
    expires_in: 3600,
    expires_at: now + 3600,
    user: {
      id: userId,
      email,
    },
  }
}

export async function seedSession(page: Page, session = buildSession()) {
  await page.addInitScript(({ storageKey, sessionValue }) => {
    window.localStorage.setItem(storageKey, JSON.stringify(sessionValue))
  }, { storageKey: SUPABASE_STORAGE_KEY, sessionValue: session })
}

export async function fulfillJson(route: Route, status: number, body: unknown) {
  await route.fulfill({
    status,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function callInternalTestApi(path: '/reset-db' | '/seed-db') {
  const baseUrl = (process.env.E2E_BACKEND_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')
  const token = process.env.E2E_ADMIN_BEARER_TOKEN
  if (!token) {
    throw new Error('E2E_ADMIN_BEARER_TOKEN is required when E2E_ENABLE_DB_RESET=true')
  }
  const res = await fetch(`${baseUrl}/api/v1/internal${path}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Internal test API ${path} failed: ${res.status} ${text}`)
  }
}
