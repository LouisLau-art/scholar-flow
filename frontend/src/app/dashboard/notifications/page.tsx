'use client'

import { useEffect, useState } from 'react'
import SiteHeader from '@/components/layout/SiteHeader'
import { Bell, CheckCircle2, Inbox, Loader2, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { authService } from '@/services/auth'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import { resolveNotificationUrl } from '@/lib/notification-url'

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const fetchNotifications = async () => {
    try {
      const token = await authService.getAccessToken()
      const res = await fetch('/api/v1/notifications?limit=100', {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      const result = await res.json()
      if (result.success) {
        setNotifications(result.data || [])
      }
    } catch (err) {
      console.error('Failed to load notifications:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchNotifications()
  }, [])

  const markAsRead = async (id: string) => {
    try {
      const token = await authService.getAccessToken()
      const res = await fetch(`/api/v1/notifications/${id}/read`, {
        method: 'PATCH',
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      if (res.ok) {
        setNotifications((prev) =>
          prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
        )
      }
    } catch (err) {
      console.error('Failed to mark as read:', err)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-muted/30 font-sans">
      <SiteHeader />

      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-12 sm:px-6">
        <div className="mb-8 flex items-center gap-4">
          <Link href="/dashboard" className="rounded-full p-2 transition-colors hover:bg-card">
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </Link>
          <div>
            <h1 className="text-3xl font-serif font-bold tracking-tight text-foreground">Notification Center</h1>
            <p className="mt-1 font-medium text-muted-foreground">Your recent alerts and messages.</p>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-12 w-12 animate-spin text-primary" />
          </div>
        ) : (
          <div className="overflow-hidden rounded-3xl border border-border bg-card shadow-sm">
            {notifications.length === 0 ? (
              <div className="p-20 text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                  <Inbox className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-bold text-foreground">No notifications yet</h3>
                <p className="text-muted-foreground">When you receive updates on your submissions or reviews, they will appear here.</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {notifications.map((n) => {
                  const href = resolveNotificationUrl(n.action_url, '/dashboard/notifications')
                  return (
                    <Link
                      key={n.id}
                      href={href}
                      onClick={() => {
                        if (!n.is_read) markAsRead(n.id)
                      }}
                      className={`flex items-start justify-between p-6 transition-all ${!n.is_read ? 'bg-primary/5' : 'hover:bg-muted/50'}`}
                    >
                      <div className="flex gap-4">
                        <div className={`rounded-2xl p-3 ${!n.is_read ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'}`}>
                          <Bell className="h-6 w-6" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className={`font-bold ${!n.is_read ? 'text-foreground' : 'text-muted-foreground'}`}>
                              {n.title}
                            </p>
                            {!n.is_read && <span className="h-2 w-2 rounded-full bg-primary" />}
                          </div>
                          <p className={`mt-1 text-sm ${!n.is_read ? 'text-foreground' : 'text-muted-foreground'}`}>
                            {n.content}
                          </p>
                          <p className="mt-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                            {new Date(n.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>

                      {!n.is_read && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                            markAsRead(n.id)
                          }}
                          className="text-primary hover:bg-primary/10 hover:text-primary"
                        >
                          <CheckCircle2 className="mr-2 h-4 w-4" />
                          Mark as read
                        </Button>
                      )}
                    </Link>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
