import * as Sentry from '@sentry/nextjs'

const dsn =
  process.env.NEXT_PUBLIC_SENTRY_DSN || process.env.SENTRY_DSN || undefined

try {
  const replayIntegrationFactory = (Sentry as unknown as any).replayIntegration
  const integrations = replayIntegrationFactory
    ? [
        replayIntegrationFactory({
          // 中文注释: 防止把 PDF/图片等媒体内容录进 replay（满足“PDF 内容不上传”约束）
          blockAllMedia: true,
        }),
      ]
    : []

  Sentry.init({
    dsn,
    environment:
      process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ||
      process.env.SENTRY_ENVIRONMENT ||
      process.env.NODE_ENV,
    enabled: !!dsn,
    // 中文注释:
    // - Firefox/隐私模式可能会把 `*.ingest.sentry.io` 当作 tracker 拦截（Network 里表现为 status=0 / time=0）。
    // - 使用同源 tunnel 把上报流量先打到本站，再由 Vercel 代理转发到 Sentry，能显著提升命中率。
    // - tunnel 路由由 `frontend/next.config.mjs` 的 rewrites 提供。
    tunnel: '/monitoring',

    // UAT 阶段全量采样（按需求）
    tracesSampleRate: 1.0,
    replaysSessionSampleRate: 1.0,
    replaysOnErrorSampleRate: 1.0,

    integrations,

    beforeSend(event) {
      // 中文注释: 最小化隐私风险（避免上传任何“可能是 PDF/base64/超长文本”的内容）
      const request = (event as any).request
      if (request && typeof request === 'object') {
        if ('data' in request) request.data = '[Filtered]'
        if ('body' in request) request.body = '[Filtered]'
        if ('cookies' in request) request.cookies = '[Filtered]'
      }
      return event
    },
  })
} catch (e) {
  // 中文注释: 零崩溃原则 — 监控不可影响页面可用性
  console.warn('[sentry] client init failed (ignored):', e)
}
