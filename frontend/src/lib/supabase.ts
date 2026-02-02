import { createBrowserClient } from '@supabase/auth-helpers-nextjs'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

// === 全局 Supabase 客户端 (Next.js SSR 兼容版) ===
// 中文注释:
// 1. 使用 createBrowserClient (替代旧版 createClientComponentClient)
// 2. 它会自动处理 Cookie 存储，确保与 Middleware 同步
// 3. 需要显式传入 URL 和 Key
export const supabase = createBrowserClient(supabaseUrl, supabaseAnonKey)

// === Realtime 订阅工具（Feature 011）===
// 中文注释:
// 1) 显性封装：组件只需要传 userId 与回调，不直接拼接 channel 细节。
// 2) 默认监听 notifications 表的 INSERT，用于铃铛红点即时更新。
export function subscribeToNotifications(
  userId: string,
  onInsert: () => void
): () => void {
  const channel = supabase
    .channel(`notifications:${userId}`)
    .on(
      'postgres_changes',
      {
        event: 'INSERT',
        schema: 'public',
        table: 'notifications',
        filter: `user_id=eq.${userId}`,
      },
      () => onInsert()
    )
    .subscribe()

  return () => {
    supabase.removeChannel(channel)
  }
}
