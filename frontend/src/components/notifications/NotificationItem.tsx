'use client'

import { cn } from '@/lib/utils'
import type { Notification } from '@/types'
import Link from 'next/link'

type Props = {
  notification: Notification
  onMarkRead: (id: string) => void
}

export function NotificationItem({ notification, onMarkRead }: Props) {
  const href = notification.action_url || '/dashboard/notifications'
  return (
    <Link
      href={href}
      onClick={() => onMarkRead(notification.id)}
      className={cn(
        'w-full text-left rounded-lg border border-border bg-card px-3 py-2 hover:bg-muted transition-colors',
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
        {!notification.is_read && (
          <span className="mt-1 inline-flex h-2 w-2 rounded-full bg-primary" />
        )}
      </div>
      <div className="mt-1 text-[11px] text-muted-foreground">
        {new Date(notification.created_at).toLocaleString()}
      </div>
    </Link>
  )
}
