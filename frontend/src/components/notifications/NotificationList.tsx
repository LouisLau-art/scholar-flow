'use client'

import type { Notification } from '@/types'
import { NotificationItem } from './NotificationItem'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'

type Props = {
  notifications: Notification[]
  onMarkRead: (id: string) => void | Promise<void>
  onMarkAllRead: () => void | Promise<void>
}

export function NotificationList({ notifications, onMarkRead, onMarkAllRead }: Props) {
  if (notifications.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="text-sm font-semibold text-foreground">No new notifications</div>
        <div className="mt-1 text-xs text-muted-foreground">
          When something important happens, it will appear here in real time.
        </div>
        <div className="mt-4 pt-3 border-t border-border/60">
          <Link 
            href="/dashboard/notifications" 
            className="text-xs font-bold text-primary hover:underline flex items-center gap-1"
          >
            View all notifications <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-border bg-card p-2">
      <div className="flex items-center justify-between px-2 py-2">
        <div className="text-sm font-bold text-foreground">Recent Updates</div>
        <button
          type="button"
          onClick={() => void onMarkAllRead()}
          className="text-xs font-semibold text-primary hover:underline"
        >
          Mark all read
        </button>
      </div>
      <div className="space-y-2 px-2 pb-2">
        {notifications.slice(0, 5).map((n) => (
          <NotificationItem key={n.id} notification={n} onMarkRead={onMarkRead} />
        ))}
      </div>
      <div className="mt-2 pt-2 border-t border-border/60 px-2 pb-1">
        <Link 
          href="/dashboard/notifications" 
          className="text-xs font-bold text-primary hover:underline flex items-center gap-1"
        >
          View all history <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
  )
}
