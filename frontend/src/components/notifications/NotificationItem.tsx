'use client'

import { cn } from '@/lib/utils'
import type { Notification } from '@/types'

type Props = {
  notification: Notification
  onMarkRead: (id: string) => void
}

export function NotificationItem({ notification, onMarkRead }: Props) {
  return (
    <button
      type="button"
      onClick={() => onMarkRead(notification.id)}
      className={cn(
        'w-full text-left rounded-lg border border-slate-200 bg-white px-3 py-2 hover:bg-slate-50 transition-colors',
        notification.is_read ? 'opacity-60' : 'opacity-100'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-slate-900 truncate">
            {notification.title}
          </div>
          <div className="mt-0.5 text-xs text-slate-600 line-clamp-2">
            {notification.content}
          </div>
        </div>
        {!notification.is_read && (
          <span className="mt-1 inline-flex h-2 w-2 rounded-full bg-red-500" />
        )}
      </div>
      <div className="mt-1 text-[11px] text-slate-500">
        {new Date(notification.created_at).toLocaleString()}
      </div>
    </button>
  )
}

