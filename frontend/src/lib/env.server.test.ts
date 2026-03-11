import { afterEach, describe, expect, it, vi } from 'vitest'

async function loadServerEnvModule(env: Record<string, string | undefined>) {
  vi.resetModules()
  const original = {
    NEXT_PUBLIC_APP_ENV: process.env.NEXT_PUBLIC_APP_ENV,
    NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL,
    VERCEL_PROJECT_PRODUCTION_URL: process.env.VERCEL_PROJECT_PRODUCTION_URL,
    VERCEL_URL: process.env.VERCEL_URL,
  }

  for (const [key, value] of Object.entries(env)) {
    if (value === undefined) {
      delete process.env[key]
    } else {
      process.env[key] = value
    }
  }

  const mod = await import('./env.server')

  Object.assign(process.env, original)
  for (const [key, value] of Object.entries(original)) {
    if (value === undefined) delete process.env[key]
  }

  return mod
}

describe('server env staging detection', () => {
  afterEach(() => {
    vi.resetModules()
  })

  it('treats Vercel host hints as staging on the server', async () => {
    const mod = await loadServerEnvModule({
      NEXT_PUBLIC_APP_ENV: 'production',
      NEXT_PUBLIC_SITE_URL: undefined,
      VERCEL_PROJECT_PRODUCTION_URL: 'scholar-flow-q1yw.vercel.app',
      VERCEL_URL: undefined,
    })

    expect(mod.IS_SERVER_STAGING).toBe(true)
  })
})
