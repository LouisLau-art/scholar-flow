'use client'

import * as Sentry from '@sentry/nextjs'
import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'

export default function SentryTestPage() {
  const [loading, setLoading] = useState(false)
  const [lastEventId, setLastEventId] = useState<string | null>(null)
  const [lastServerEventId, setLastServerEventId] = useState<string | null>(null)

  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN
  const dsnConfigured = !!dsn
  const dsnSummary = (() => {
    if (!dsn) return null
    try {
      const url = new URL(dsn)
      const host = url.host
      const projectId = url.pathname.replace(/^\//, '') || null
      return { host, projectId }
    } catch {
      return null
    }
  })()

  const handleCaptureMessage = async () => {
    const eventId = Sentry.captureMessage('Sentry test message (frontend)')
    setLastEventId(eventId || null)
    await Sentry.flush(2000)
    toast.success(`已发送 Sentry 测试消息（前端）${eventId ? `，EventId=${eventId}` : ''}`)
  }

  const handleThrowError = async () => {
    const eventId = Sentry.captureException(new Error('Sentry test error (frontend)'))
    setLastEventId(eventId || null)
    await Sentry.flush(2000)
    toast.success(`已发送 Sentry 测试异常（前端）${eventId ? `，EventId=${eventId}` : ''}`)
  }

  const handleTriggerServerError = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/sentry-test', { method: 'GET' })
      const payload = await res.json().catch(() => null)
      if (!res.ok) {
        const eventId = payload?.eventId ? String(payload.eventId) : null
        setLastServerEventId(eventId)
        toast.success(
          `已触发服务端异常（Next API Route）${eventId ? `，EventId=${eventId}` : ''}`,
        )
        return
      }
      toast.message('服务端返回了 200（不符合预期）')
    } catch (e) {
      toast.success('已触发服务端异常（Next API Route）')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <h1 className="text-2xl font-semibold">Sentry 测试页</h1>
      <p className="text-sm text-muted-foreground">
        用于 UAT 验证：前端异常、服务端异常、Replay/Tracing 是否正常上报。
      </p>
      <p className="text-xs text-muted-foreground">
        DSN: {dsnConfigured ? 'configured' : 'missing（请在 Vercel 配 NEXT_PUBLIC_SENTRY_DSN）'}
      </p>
      {dsnSummary ? (
        <p className="text-xs text-muted-foreground">
          DSN Host: {dsnSummary.host} / Project: {dsnSummary.projectId}
        </p>
      ) : null}
      {lastEventId ? (
        <p className="text-xs text-muted-foreground">Last client EventId: {lastEventId}</p>
      ) : null}
      {lastServerEventId ? (
        <p className="text-xs text-muted-foreground">Last server EventId: {lastServerEventId}</p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button onClick={handleCaptureMessage} variant="secondary">
          发送测试消息（前端）
        </Button>
        <Button onClick={handleTriggerServerError} variant="secondary" disabled={loading}>
          {loading ? '触发中...' : '触发服务端异常（Next）'}
        </Button>
        <Button onClick={handleThrowError} variant="destructive">
          直接抛异常（前端）
        </Button>
      </div>
    </div>
  )
}
