import dynamic from 'next/dynamic'
import { Loader2 } from 'lucide-react'

import SiteHeader from '@/components/layout/SiteHeader'

const AEWorkspacePanel = dynamic(
  () => import('@/components/editor/AEWorkspacePanel').then((mod) => mod.AEWorkspacePanel),
  {
    ssr: false,
    loading: () => (
      <div className="rounded-xl border border-border bg-card p-10 text-sm text-muted-foreground flex items-center justify-center gap-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading workspace...
      </div>
    ),
  }
)

export default function AEWorkspacePage() {
  return (
    <div className="sf-page-shell">
      <SiteHeader />
      <main className="sf-page-container space-y-6 py-10">
        <AEWorkspacePanel />
      </main>
    </div>
  )
}
