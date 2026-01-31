import type { Page, Route } from '@playwright/test'

const SUPABASE_STORAGE_KEY = 'sb-mmvulyrfsorqdpdrzbkd-auth-token'

export function buildSession(userId = '00000000-0000-0000-0000-000000000000', email = 'test@example.com') {
  const now = Math.floor(Date.now() / 1000)
  return {
    access_token: 'test-access-token',
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
