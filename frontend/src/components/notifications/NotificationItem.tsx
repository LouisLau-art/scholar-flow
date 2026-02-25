'use client'

import { cn } from '@/lib/utils'
import type { Notification } from '@/types'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ChevronRight } from 'lucide-react'
import { resolveNotificationUrl } from '@/lib/notification-url'

type Props = {
  notification: Notification
  onMarkRead: (id: string) => void | Promise<void>
}

export function NotificationItem({ notification, onMarkRead }: Props) {
  const href = resolveNotificationUrl(notification.action_url, '/dashboard/notifications')
  const router = useRouter()

  const createdAt = notification.created_at ? new Date(notification.created_at) : null
  const createdText = createdAt ? createdAt.toLocaleString() : ''

  return (
    <Link
      href={href}
      onClick={(e) => {
        // 中文注释：支持新标签打开（Ctrl/⌘/中键）时不拦截默认行为
        const isModifiedClick =
          e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || (e as any).button === 1
        if (isModifiedClick) return

        e.preventDefault()
        Promise.resolve(onMarkRead(notification.id)).finally(() => {
          router.push(href)
        })
      }}
      className={cn(
        // 中文注释：必须是 block，否则多行内容会出现“边框分段/括号”样式（inline 行盒渲染）。
        'block w-full rounded-lg border border-border bg-card px-3 py-2 hover:bg-muted transition-colors cursor-pointer',
        notification.is_read ? 'opacity-60' : 'opacity-100'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-foreground truncate">
            {notification.title}
          </div>
          <div className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
            {notification.content}
          </div>
        </div>
        <div className="flex items-center gap-2 pt-0.5">
          {!notification.is_read && <span className="inline-flex h-2 w-2 rounded-full bg-primary" />}
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>
      {createdText ? <div className="mt-1 text-[11px] text-muted-foreground">{createdText}</div> : null}
    </Link>
  )
}
