'use client'

import type { Notification } from '@/types'
import { NotificationItem } from './NotificationItem'

type Props = {
  notifications: Notification[]
  onMarkRead: (id: string) => void
  onMarkAllRead: () => void
}

export function NotificationList({ notifications, onMarkRead, onMarkAllRead }: Props) {
  if (notifications.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="text-sm font-semibold text-slate-900">No notifications yet</div>
        <div className="mt-1 text-xs text-slate-600">
          When something important happens, it will appear here in real time.
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-2">
      <div className="flex items-center justify-between px-2 py-2">
        <div className="text-sm font-bold text-slate-900">Notifications</div>
        <button
          type="button"
          onClick={onMarkAllRead}
          className="text-xs font-semibold text-blue-600 hover:underline"
        >
          Mark all as read
        </button>
      </div>
      <div className="space-y-2 px-2 pb-2">
        {notifications.slice(0, 5).map((n) => (
          <NotificationItem key={n.id} notification={n} onMarkRead={onMarkRead} />
        ))}
      </div>
    </div>
  )
}

