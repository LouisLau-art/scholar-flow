import dynamic from 'next/dynamic'
import { Loader2 } from 'lucide-react'

import SiteHeader from '@/components/layout/SiteHeader'

const AnalyticsDashboardClient = dynamic(
  () =>
    import('@/components/analytics/AnalyticsDashboardClient').then(
      (mod) => mod.AnalyticsDashboardClient
    ),
  {
    ssr: false,
    loading: () => (
      <div className="rounded-xl border border-border bg-card p-10 text-sm text-muted-foreground flex items-center justify-center gap-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading analytics workspace...
      </div>
    ),
  }
)

export default function AnalyticsDashboardPage() {
  return (
    <div className="min-h-screen bg-muted/40 flex flex-col font-sans">
      <SiteHeader />
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-10 sm:px-6 lg:px-8">
        <AnalyticsDashboardClient />
      </main>
    </div>
  )
}
