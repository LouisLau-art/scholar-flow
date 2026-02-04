import { withSentryConfig } from '@sentry/nextjs'

/** @type {import('next').NextConfig} */
const nextConfig = {
  productionBrowserSourceMaps: true,
  async rewrites() {
    const backendOriginRaw =
      process.env.BACKEND_ORIGIN ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://127.0.0.1:8000'
    const backendOrigin = backendOriginRaw.replace(/\/$/, '')
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendOrigin}/api/v1/:path*`,
      },
    ]
  },
}

const hasSentryAuth =
  !!process.env.SENTRY_AUTH_TOKEN &&
  !!process.env.SENTRY_ORG &&
  !!process.env.SENTRY_PROJECT

// 中文注释:
// - 没有配置 token/org/project 时：仍可在浏览器/后端看到 Sentry 事件（DSN），但不会上传 sourcemaps。
// - 配置完整时：构建阶段自动上传 sourcemaps，Sentry 里可直接定位到源码行。
const sentryWebpackPluginOptions = {
  authToken: process.env.SENTRY_AUTH_TOKEN,
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  silent: true,
}

const sentryBuildOptions = {
  // 让客户端上传更多 bundle sourcemaps，方便定位
  widenClientFileUpload: true,
  // 不把 sourcemap 公开给用户（只上传到 Sentry）
  hideSourceMaps: true,
  // 避免在控制台刷 sentry debug log
  disableLogger: true,
}

export default hasSentryAuth
  ? withSentryConfig(nextConfig, sentryWebpackPluginOptions, sentryBuildOptions)
  : nextConfig
