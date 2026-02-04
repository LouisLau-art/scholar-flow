import * as Sentry from '@sentry/nextjs'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function GET() {
  const dsn = process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN

  const summarizeDsn = (raw?: string | null) => {
    if (!raw) return { host: null, projectId: null }
    try {
      const url = new URL(raw)
      const host = url.host
      const projectId = url.pathname.replace(/^\//, '') || null
      return { host, projectId }
    } catch {
      return { host: null, projectId: null }
    }
  }

  // 中文注释:
  // - 用于验证 Sentry 是否能捕获 Next.js 服务端（API Route）异常
  // - 不能直接 throw：避免在构建/预渲染检查阶段触发失败
  // - 若 withSentryConfig 注入失败：这里做一次“兜底 init”，确保能定位问题
  try {
    const maybeGetClient = (Sentry as unknown as any).getClient
    const hasClient = typeof maybeGetClient === 'function' ? !!maybeGetClient() : true
    if (!hasClient && dsn) {
      Sentry.init({
        dsn,
        enabled: true,
        environment:
          process.env.SENTRY_ENVIRONMENT ||
          process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ||
          process.env.NODE_ENV,
        tracesSampleRate: 1.0,
      })
    }
  } catch {
    // ignore
  }

  const err = new Error('Sentry test error (next api route)')
  const eventId = Sentry.captureException(err)
  const flushed = await Sentry.flush(2000)
  const dsnSummary = summarizeDsn(dsn)

  return Response.json(
    {
      ok: false,
      error: 'Triggered server error for Sentry test.',
      eventId,
      flushed,
      dsnConfigured: !!dsn,
      dsn: dsnSummary,
      environment:
        process.env.SENTRY_ENVIRONMENT ||
        process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ||
        null,
      nodeEnv: process.env.NODE_ENV || null,
    },
    { status: 500, headers: { 'x-sentry-event-id': String(eventId || '') } },
  )
}
