import type { Page, Route } from '@playwright/test'

function resolveSupabaseStorageKey(): string {
  const raw = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
  try {
    const ref = new URL(raw).hostname.split('.')[0]
    if (ref) return `sb-${ref}-auth-token`
  } catch {
    // ignore
  }
  return 'sb-mmvulyrfsorqdpdrzbkd-auth-token'
}

const SUPABASE_STORAGE_KEY = resolveSupabaseStorageKey()

function base64UrlEncode(input: string) {
  return Buffer.from(input, 'utf-8')
    .toString('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
}

function buildFakeJwt(userId: string, email: string, exp: number) {
  // 中文注释: 前端只需要“可解码”的 JWT 形态用于 session 解析；不做签名校验。
  const header = base64UrlEncode(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = base64UrlEncode(
    JSON.stringify({
      aud: 'authenticated',
      exp,
      sub: userId,
      email,
      role: 'authenticated',
    })
  )
  const signature = 'test-signature'
  return `${header}.${payload}.${signature}`
}

export function buildSession(userId = '00000000-0000-0000-0000-000000000000', email = 'test@example.com') {
  const now = Math.floor(Date.now() / 1000)
  const accessToken = buildFakeJwt(userId, email, now + 3600)
  return {
    access_token: accessToken,
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
  // Set LocalStorage for client-side use
  await page.addInitScript(({ storageKey, sessionValue }) => {
    window.localStorage.setItem(storageKey, JSON.stringify(sessionValue))
  }, { storageKey: SUPABASE_STORAGE_KEY, sessionValue: session })

  // Set Cookie for server-side (Middleware) use
  // Supabase Next.js auth-helpers use cookies to persist session across SSR
  const cookieValue = encodeURIComponent(JSON.stringify(session))
  await page.context().addCookies([
    {
      name: SUPABASE_STORAGE_KEY,
      value: cookieValue,
      domain: 'localhost',
      path: '/',
      expires: session.expires_at,
      httpOnly: false, // Must be accessible by client if needed, though Supabase handles it
      secure: false,
      sameSite: 'Lax'
    }
  ])
}

export async function fulfillJson(route: Route, status: number, body: unknown) {
  await route.fulfill({
    status,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
