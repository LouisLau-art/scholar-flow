import { createServerClient, type CookieOptions } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

function tryParseJson<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

function getUserFromSupabaseSessionCookie(req: NextRequest): { id: string; email?: string } | null {
  // 中文注释:
  // - Supabase auth-helpers 默认使用 `sb-<project-ref>-auth-token` cookie 存储 session（JSON）。
  // - E2E/本地开发时，Supabase Auth 可能不可用或 token 不可验证；此时允许从 cookie 中“降级识别”用户。
  // - 该逻辑只在非生产环境的特定条件下启用（见下方 allowBypass）。
  const candidates = req.cookies.getAll().filter((c) => c.name.startsWith('sb-') && c.name.endsWith('-auth-token'))
  const cookie = candidates[0]
  if (!cookie?.value) return null

  const decoded = tryParseJson<any>(decodeURIComponent(cookie.value)) ?? tryParseJson<any>(cookie.value)
  const user = decoded?.user
  if (!user?.id) return null
  return { id: user.id, email: user.email }
}

function hasSupabaseSessionCookie(req: NextRequest): boolean {
  return req.cookies
    .getAll()
    .some((c) => c.name.startsWith('sb-') && c.name.endsWith('-auth-token') && Boolean(c.value))
}

export async function middleware(req: NextRequest) {
  // 0.5) Reviewer Magic Link（Feature 039）
  // 中文注释:
  // - /review/invite?token=... 是审稿人“免登录”入口。
  // - 这里在 Middleware 里做一次后端校验（签名/过期/撤销），然后写入 httpOnly cookie 作为“访客会话”。
  // - 随后重定向到 /review/invite?assignment_id=...（去掉 token，避免 Referer 泄露）。
  // - Reviewer 明确 Accept 后，前端再跳转到 /reviewer/workspace/[id]。
  if (req.nextUrl.pathname === '/review/invite') {
    const token = req.nextUrl.searchParams.get('token')
    if (token) {
      const allowBypass =
        process.env.NODE_ENV !== 'production' && req.headers.get('x-scholarflow-e2e') === '1'

      // E2E 兜底：避免在 Middleware 里走真实后端请求（Playwright mock 无法拦截服务端 fetch）
      const bypassAssignmentId = req.nextUrl.searchParams.get('assignment_id')

      let assignmentId: string | null = null
      if (allowBypass && bypassAssignmentId) {
        assignmentId = bypassAssignmentId
      } else {
        try {
          const verifyRes = await fetch(`${req.nextUrl.origin}/api/v1/auth/magic-link/verify`, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ token }),
          })
          const json = await verifyRes.json().catch(() => null)
          if (verifyRes.ok && json?.success && json?.data?.assignment_id) {
            assignmentId = String(json.data.assignment_id)
          }
        } catch {
          assignmentId = null
        }
      }

      if (!assignmentId) {
        const url = req.nextUrl.clone()
        url.pathname = '/review/error'
        url.searchParams.set('reason', 'invalid')
        return NextResponse.redirect(url)
      }

      const url = req.nextUrl.clone()
      url.pathname = '/review/invite'
      url.search = `?assignment_id=${encodeURIComponent(assignmentId)}`

      const resp = NextResponse.redirect(url)
      resp.cookies.set({
        name: 'sf_review_magic',
        value: token,
        httpOnly: true,
        sameSite: 'lax',
        secure: process.env.NODE_ENV === 'production',
        path: '/',
        maxAge: 60 * 60 * 24 * 14,
      })
      return resp
    }
    // 无 token 的邀请页（如 assignment_id 模式）不需要走全量鉴权流程，直接放行。
    return NextResponse.next()
  }

  // 0) Favicon 兜底
  // 中文注释:
  // - 某些 Next.js 版本/缓存状态下，/favicon.ico 偶发返回 500（且没有明显错误栈）。
  // - 这里直接把 /favicon.ico rewrite 到我们自定义的 /favicon.svg，避免影响正文流程。
  if (req.nextUrl.pathname === '/favicon.ico') {
    const url = req.nextUrl.clone()
    url.pathname = '/favicon.svg'
    return NextResponse.rewrite(url)
  }

  const protectedPaths = ['/dashboard', '/admin', '/submit', '/editor', '/proofreading', '/finance']
  const isProtected = protectedPaths.some(path =>
    req.nextUrl.pathname.startsWith(path)
  )
  const allowE2EBypass =
    process.env.NODE_ENV !== 'production' && req.headers.get('x-scholarflow-e2e') === '1'
  if (isProtected && !allowE2EBypass && !hasSupabaseSessionCookie(req)) {
    const redirectUrl = req.nextUrl.clone()
    redirectUrl.pathname = '/login'
    redirectUrl.searchParams.set('next', req.nextUrl.pathname)
    return NextResponse.redirect(redirectUrl)
  }

  // 1. 初始化响应
  // 我们必须创建一个初始响应，因为 cookie 操作需要修改这个响应对象
  let res = NextResponse.next({
    request: {
      headers: req.headers,
    },
  })

  // 2. 创建 Supabase Client (SSR 模式)
  // 由于 auth-helpers-nextjs 0.15.0+ 实际上是 @supabase/ssr 的封装
  // 我们需要手动处理 cookie 的 get/set/remove
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return req.cookies.get(name)?.value
        },
        set(name: string, value: string, options: CookieOptions) {
          req.cookies.set({
            name,
            value,
            ...options,
          })
          res = NextResponse.next({
            request: {
              headers: req.headers,
            },
          })
          res.cookies.set({
            name,
            value,
            ...options,
          })
        },
        remove(name: string, options: CookieOptions) {
          req.cookies.set({
            name,
            value: '',
            ...options,
          })
          res = NextResponse.next({
            request: {
              headers: req.headers,
            },
          })
          res.cookies.set({
            name,
            value: '',
            ...options,
          })
        },
      },
    }
  )

  // 3. 检查 Session
  // getUser() 比 getSession() 更安全，因为它会向 Supabase Auth 服务器验证 token
  let user: any = null
  let getUserErrored = false
  try {
    const resp = await supabase.auth.getUser()
    user = resp.data.user
  } catch (e) {
    // 中文注释: 开发/测试环境下，Supabase Auth 不可用时不要直接阻断页面渲染。
    // 生产环境仍保持严格校验（不启用降级）。
    getUserErrored = true
  }

  // 4.5 E2E/开发环境降级：允许通过 header 或 Supabase Auth 不可用时，从 cookie 中识别用户
  const allowBypass =
    process.env.NODE_ENV !== 'production' &&
    (allowE2EBypass || getUserErrored)
  if (isProtected && !user && allowBypass) {
    user = getUserFromSupabaseSessionCookie(req)
  }

  // 5. 执行重定向
  if (isProtected && !user) {
    const redirectUrl = req.nextUrl.clone()
    redirectUrl.pathname = '/login'
    redirectUrl.searchParams.set('next', req.nextUrl.pathname)
    return NextResponse.redirect(redirectUrl)
  }

  // 6. 刷新 Session (重要)
  // middleware 必须返回 res，以便写入刷新后的 cookie (如果有变化)
  return res
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public (public files)
     * - api (API routes - handled separately or let through)
     */
    '/dashboard/:path*',
    '/admin/:path*',
    '/submit/:path*',
    '/editor/:path*',
    '/proofreading/:path*',
    '/finance/:path*',
    '/favicon.ico',
    '/review/invite',
    // 也可以匹配所有，然后在逻辑里排除，但显式匹配受保护路径性能更好
  ],
}
