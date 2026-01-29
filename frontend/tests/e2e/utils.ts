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
