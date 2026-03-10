import { afterEach, describe, expect, it, vi } from 'vitest'

async function loadEnvModule(env: Record<string, string | undefined>) {
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

  const mod = await import('./env')

  Object.assign(process.env, original)
  for (const [key, value] of Object.entries(original)) {
    if (value === undefined) delete process.env[key]
  }

  return mod
}

describe('env staging detection', () => {
  afterEach(() => {
    vi.resetModules()
  })

  it('returns true when NEXT_PUBLIC_APP_ENV is staging', async () => {
    const mod = await loadEnvModule({
      NEXT_PUBLIC_APP_ENV: 'staging',
      NEXT_PUBLIC_SITE_URL: undefined,
      VERCEL_PROJECT_PRODUCTION_URL: undefined,
      VERCEL_URL: undefined,
    })

    expect(mod.APP_ENV).toBe('staging')
    expect(mod.IS_STAGING).toBe(true)
  })

  it('falls back to known UAT hostname hints when env is not explicitly staging', async () => {
    const mod = await loadEnvModule({
      NEXT_PUBLIC_APP_ENV: 'production',
      NEXT_PUBLIC_SITE_URL: 'https://scholar-flow-q1yw.vercel.app',
      VERCEL_PROJECT_PRODUCTION_URL: undefined,
      VERCEL_URL: undefined,
    })

    expect(mod.APP_ENV).toBe('production')
    expect(mod.IS_STAGING).toBe(true)
  })

  it('stays false for normal production hostnames', async () => {
    const mod = await loadEnvModule({
      NEXT_PUBLIC_APP_ENV: 'production',
      NEXT_PUBLIC_SITE_URL: 'https://scholarflow.example.com',
      VERCEL_PROJECT_PRODUCTION_URL: undefined,
      VERCEL_URL: undefined,
    })

    expect(mod.IS_STAGING).toBe(false)
  })
})
