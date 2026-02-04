import * as Sentry from '@sentry/nextjs'

const dsn =
  process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN || undefined

try {
  Sentry.init({
    dsn,
    environment:
      process.env.SENTRY_ENVIRONMENT ||
      process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ||
      process.env.NODE_ENV,
    enabled: !!dsn,
    tracesSampleRate: 1.0,
  })
} catch (e) {
  // 中文注释: 零崩溃原则
  console.warn('[sentry] edge init failed (ignored):', e)
}

