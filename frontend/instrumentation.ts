import * as Sentry from '@sentry/nextjs'

export async function register() {
  try {
    const runtime = process.env.NEXT_RUNTIME
    if (runtime === 'edge') {
      await import('./sentry.edge.config')
      return
    }
    await import('./sentry.server.config')
  } catch (e) {
    // 中文注释: 零崩溃原则 — 监控不可影响服务启动
    console.warn('[sentry] instrumentation register failed (ignored):', e)
  }
}

// 中文注释: 捕获 App Router 的服务端请求错误
export const onRequestError = Sentry.captureRequestError

