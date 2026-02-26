import SiteHeader from '@/components/layout/SiteHeader'
import { AEWorkspacePanel } from '@/components/editor/AEWorkspacePanel'

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
