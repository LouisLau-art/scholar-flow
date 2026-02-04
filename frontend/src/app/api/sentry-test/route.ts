import * as Sentry from '@sentry/nextjs'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function GET() {
  // 中文注释:
  // - 用于验证 Sentry 是否能捕获 Next.js 服务端（API Route）异常
  // - 不能直接 throw：Next build 阶段可能会执行 route 预渲染/检查，导致构建失败
  const err = new Error('Sentry test error (next api route)')
  Sentry.captureException(err)
  await Sentry.flush(1500)

  return Response.json(
    { ok: false, error: 'Triggered server error for Sentry test.' },
    { status: 500 },
  )
}
