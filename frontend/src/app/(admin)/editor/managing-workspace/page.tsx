import dynamic from 'next/dynamic'
import { Loader2 } from 'lucide-react'

import SiteHeader from '@/components/layout/SiteHeader'

const ManagingWorkspacePanel = dynamic(
  () =>
    import('@/components/editor/ManagingWorkspacePanel').then(
      (mod) => mod.ManagingWorkspacePanel
    ),
  {
    ssr: false,
    loading: () => (
      <div className="rounded-xl border border-border bg-card p-10 text-sm text-muted-foreground flex items-center justify-center gap-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading managing workspace...
      </div>
    ),
  }
)

export default function ManagingWorkspacePage() {
  return (
    <div className="sf-page-shell">
      <SiteHeader />
      <main className="sf-page-container space-y-6 py-10">
        <ManagingWorkspacePanel />
      </main>
    </div>
  )
}
