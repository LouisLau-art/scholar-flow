'use client'

import * as Sentry from '@sentry/nextjs'
import { useEffect } from 'react'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    Sentry.captureException(error)
    void Sentry.flush(2000)
  }, [error])

  return (
    <html>
      <body className="p-6">
        <h2 className="text-lg font-semibold">页面发生错误</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          已记录错误信息。你可以刷新页面或点击下面按钮重试。
        </p>
        <button
          className="mt-4 rounded bg-black px-4 py-2 text-white"
          onClick={() => reset()}
          type="button"
        >
          重试
        </button>
      </body>
    </html>
  )
}

