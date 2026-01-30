'use client'

import { useEffect, useRef, useState } from 'react'
import type { Notification } from '@/types'
import { supabase, subscribeToNotifications } from '@/lib/supabase'
import { BellIcon } from '@/components/icons/BellIcon'
import { NotificationList } from './NotificationList'

type Props = {
  isAuthenticated: boolean
}

export function NotificationBell({ isAuthenticated }: Props) {
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [userId, setUserId] = useState<string | null>(null)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const containerRef = useRef<HTMLDivElement | null>(null)

  const unreadCount = notifications.filter((n) => !n.is_read).length

  const load = async (uid: string) => {
    setIsLoading(true)
    const { data, error } = await supabase
      .from('notifications')
      .select('*')
      .eq('user_id', uid)
      .order('created_at', { ascending: false })
      .limit(20)
    if (!error) setNotifications((data as Notification[]) ?? [])
    setIsLoading(false)
  }

  useEffect(() => {
    let unsubscribe: (() => void) | null = null
    let mounted = true

    const init = async () => {
      if (!isAuthenticated) {
        setIsLoading(false)
        return
      }
      const { data } = await supabase.auth.getSession()
      const uid = data.session?.user?.id ?? null
      if (!mounted) return
      setUserId(uid)
      if (!uid) {
        setIsLoading(false)
        return
      }
      await load(uid)
      unsubscribe = subscribeToNotifications(uid, () => load(uid))
    }

    init()
    return () => {
      mounted = false
      unsubscribe?.()
    }
  }, [isAuthenticated])

  useEffect(() => {
    if (!isOpen) return
    const onClick = (event: MouseEvent) => {
      const target = event.target as Node
      if (containerRef.current && !containerRef.current.contains(target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [isOpen])

  const markRead = async (id: string) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)))
    await supabase.from('notifications').update({ is_read: true }).eq('id', id)
  }

  const markAllRead = async () => {
    if (!userId) return
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
    await supabase
      .from('notifications')
      .update({ is_read: true })
      .eq('user_id', userId)
      .eq('is_read', false)
  }

  if (!isAuthenticated) return null

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="relative text-slate-400 hover:text-white transition-colors"
        aria-label="Notifications"
      >
        <BellIcon className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 inline-flex h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-slate-900" />
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-3 w-[360px] z-50">
          {isLoading ? (
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="text-sm font-semibold text-slate-900">Loading…</div>
              <div className="mt-1 text-xs text-slate-600">Fetching your latest notifications.</div>
            </div>
          ) : (
            <NotificationList
              notifications={notifications.filter((n) => !n.is_read)}
              onMarkRead={markRead}
              onMarkAllRead={markAllRead}
            />
          )}
        </div>
      )}
    </div>
  )
}

