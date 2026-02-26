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
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
      },
    ],
    formats: ['image/avif', 'image/webp'],
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
  // 中文注释:
  // - 使用 Sentry 官方 tunnelRoute：会自动把浏览器端上报改为同源路径
  // - 将路径从 `/monitoring` 调整为更中性的内部路径，降低被广告/隐私插件误拦截概率
  tunnelRoute: '/api/_sf_events',
  // 让客户端上传更多 bundle sourcemaps，方便定位
  widenClientFileUpload: true,
  // 不把 sourcemap 公开给用户（只上传到 Sentry）
  hideSourceMaps: true,
  webpack: {
    treeshake: {
      // 避免在控制台刷 sentry debug log（替代已弃用 disableLogger）
      removeDebugLogging: true,
    },
  },
}

export default withSentryConfig(nextConfig, sentryBuildOptions)
