'use client'

import { useEffect, useState } from 'react'
import SiteHeader from '@/components/layout/SiteHeader'
import { Bell, CheckCircle2, Inbox, Loader2, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { authService } from '@/services/auth'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'

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
        setNotifications(prev => 
          prev.map(n => n.id === id ? { ...n, is_read: true } : n)
        )
      }
    } catch (err) {
      console.error('Failed to mark as read:', err)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <SiteHeader />

      <main className="flex-1 mx-auto max-w-4xl w-full px-4 py-12 sm:px-6">
        <div className="flex items-center gap-4 mb-8">
          <Link href="/dashboard" className="p-2 hover:bg-white rounded-full transition-colors">
            <ArrowLeft className="h-5 w-5 text-slate-500" />
          </Link>
          <div>
            <h1 className="text-3xl font-serif font-bold text-slate-900 tracking-tight">Notification Center</h1>
            <p className="mt-1 text-slate-500 font-medium">Your recent alerts and messages.</p>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
          </div>
        ) : (
          <div className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
            {notifications.length === 0 ? (
              <div className="p-20 text-center">
                <div className="bg-slate-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Inbox className="h-8 w-8 text-slate-300" />
                </div>
                <h3 className="text-lg font-bold text-slate-900">No notifications yet</h3>
                <p className="text-slate-500">When you receive updates on your submissions or reviews, they will appear here.</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {notifications.map((n) => (
                  <div 
                    key={n.id} 
                    className={`p-6 flex items-start justify-between transition-all ${!n.is_read ? 'bg-blue-50/30' : 'hover:bg-slate-50'}`}
                  >
                    <div className="flex gap-4">
                      <div className={`p-3 rounded-2xl ${!n.is_read ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-400'}`}>
                        <Bell className="h-6 w-6" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className={`font-bold ${!n.is_read ? 'text-slate-900' : 'text-slate-600'}`}>
                            {n.title}
                          </p>
                          {!n.is_read && (
                            <span className="w-2 h-2 rounded-full bg-blue-600" />
                          )}
                        </div>
                        <p className={`mt-1 text-sm ${!n.is_read ? 'text-slate-700' : 'text-slate-500'}`}>
                          {n.content}
                        </p>
                        <p className="mt-2 text-xs text-slate-400 font-medium uppercase tracking-wider">
                          {new Date(n.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    
                    {!n.is_read && (
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => markAsRead(n.id)}
                        className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                      >
                        <CheckCircle2 className="h-4 w-4 mr-2" />
                        Mark as read
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
