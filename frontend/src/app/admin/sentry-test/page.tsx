'use client'

import * as Sentry from '@sentry/nextjs'
import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'

export default function SentryTestPage() {
  const [loading, setLoading] = useState(false)

  const handleCaptureMessage = () => {
    Sentry.captureMessage('Sentry test message (frontend)')
    toast.success('已发送 Sentry 测试消息（前端）')
  }

  const handleThrowError = () => {
    throw new Error('Sentry test error (frontend)')
  }

  const handleTriggerServerError = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/sentry-test', { method: 'GET' })
      if (!res.ok) {
        toast.success('已触发服务端异常（Next API Route）')
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

