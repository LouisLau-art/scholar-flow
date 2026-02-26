import SiteHeader from '@/components/layout/SiteHeader'
import { ManagingWorkspacePanel } from '@/components/editor/ManagingWorkspacePanel'

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
