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

export async function middleware(req: NextRequest) {
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

  // 4. 定义受保护路径
  const protectedPaths = ['/dashboard', '/admin', '/submit', '/editor']
  const isProtected = protectedPaths.some(path => 
    req.nextUrl.pathname.startsWith(path)
  )

  // 4.5 E2E/开发环境降级：允许通过 header 或 Supabase Auth 不可用时，从 cookie 中识别用户
  const allowBypass =
    process.env.NODE_ENV !== 'production' &&
    (req.headers.get('x-scholarflow-e2e') === '1' || getUserErrored)
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
    // 也可以匹配所有，然后在逻辑里排除，但显式匹配受保护路径性能更好
  ],
}
