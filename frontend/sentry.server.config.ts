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

    // UAT 阶段全量追踪（按需求）
    tracesSampleRate: 1.0,

    // 中文注释: Next.js 服务器侧也要做隐私兜底，避免把请求体（尤其 multipart/pdf）送到 Sentry。
    beforeSend(event) {
      const request = (event as any).request
      if (request && typeof request === 'object') {
        if ('data' in request) request.data = '[Filtered]'
        if ('body' in request) request.body = '[Filtered]'
        if ('cookies' in request) request.cookies = '[Filtered]'
        if (request.headers && typeof request.headers === 'object') {
          // 移除敏感 header
          const headers: Record<string, string> = {}
          for (const [k, v] of Object.entries(request.headers)) {
            const key = k.toLowerCase()
            if (key === 'authorization' || key === 'cookie' || key === 'set-cookie') {
              continue
            }
            headers[k] = String(v)
          }
          request.headers = headers
        }
      }
      return event
    },
  })
} catch (e) {
  // 中文注释: 零崩溃原则
  console.warn('[sentry] server init failed (ignored):', e)
}

