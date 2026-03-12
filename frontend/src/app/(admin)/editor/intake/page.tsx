'use client'

import SiteHeader from '@/components/layout/SiteHeader'
import QueryProvider from '@/components/providers/QueryProvider'
import { ManagingWorkspacePanel } from '@/components/editor/ManagingWorkspacePanel'
import { Info } from 'lucide-react'

export default function MEIntakePage() {
  return (
    <QueryProvider>
      <div className="sf-page-shell">
        <SiteHeader />
        <main className="sf-page-container space-y-6 py-10">
          <div className="flex items-start gap-2 rounded-xl border border-blue-200 bg-blue-50 p-4 text-blue-800">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
            <div className="text-sm">
              提示：原 Intake 队列已合并至统一的 Managing Workspace。此页面作为兼容入口保留，未来将被弃用。
            </div>
          </div>
          <ManagingWorkspacePanel initialBucket="intake" />
        </main>
      </div>
    </QueryProvider>
  )
}
