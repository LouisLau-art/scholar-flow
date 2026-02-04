import { withSentryConfig } from '@sentry/nextjs'

/** @type {import('next').NextConfig} */
const nextConfig = {
  // 中文注释:
  // - 不对浏览器公开 sourcemap（避免 DevTools 一直 404 .map 的噪音）
  // - sourcemap 如需调试，请通过 Sentry 上传（需要配置 SENTRY_AUTH_TOKEN/ORG/PROJECT）
  productionBrowserSourceMaps: false,
  experimental: {
    instrumentationHook: true,
  },
  async rewrites() {
    const backendOriginRaw =
      process.env.BACKEND_ORIGIN ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://127.0.0.1:8000'
    const backendOrigin = backendOriginRaw.replace(/\/$/, '')
    const rules = [
      {
        source: '/api/v1/:path*',
        destination: `${backendOrigin}/api/v1/:path*`,
      },
    ]

    // 中文注释: Sentry 同源 tunnel，绕过浏览器隐私/跟踪保护对 ingest 域名的拦截
    const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN || process.env.SENTRY_DSN
    if (dsn) {
      try {
        const url = new URL(dsn)
        const host = url.host
        const projectId = url.pathname.replace(/^\//, '')
        if (host && projectId) {
          rules.push({
            source: '/monitoring',
            destination: `https://${host}/api/${projectId}/envelope/`,
          })
        }
      } catch {
        // ignore invalid DSN
      }
    }

    return rules
  },
}

const hasSentryAuth =
  !!process.env.SENTRY_AUTH_TOKEN &&
  !!process.env.SENTRY_ORG &&
  !!process.env.SENTRY_PROJECT

const sentryBuildOptions = {
  // 中文注释:
  // - 必须始终启用 withSentryConfig：否则 `sentry.*.config.ts` 不会被自动注入到构建入口，导致线上“点测试按钮但 Sentry 无事件”。
  // - 没有配置 token/org/project 时：禁用 sourcemaps 上传，但保留运行时上报（DSN）。
  authToken: process.env.SENTRY_AUTH_TOKEN,
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  silent: true,
  sourcemaps: {
    disable: !hasSentryAuth,
  },
  // 让客户端上传更多 bundle sourcemaps，方便定位
  widenClientFileUpload: true,
  // 不把 sourcemap 公开给用户（只上传到 Sentry）
  hideSourceMaps: true,
  // 避免在控制台刷 sentry debug log
  disableLogger: true,
}

export default withSentryConfig(nextConfig, sentryBuildOptions)
