'use client'

import Link from 'next/link'
import SiteHeader from '@/components/layout/SiteHeader'
import { ManuscriptsProcessPanel } from '@/components/editor/ManuscriptsProcessPanel'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { ArrowLeft, Table2 } from 'lucide-react'
import { Suspense, useState } from 'react'
import ReviewerAssignModal from '@/components/ReviewerAssignModal'
import { toast } from 'sonner'
import { authService } from '@/services/auth'

export default function ManuscriptsProcessPage() {
  const [refreshKey, setRefreshKey] = useState(0)
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false)
  const [selectedManuscriptId, setSelectedManuscriptId] = useState<string | undefined>()

  const handleAssignReviewer = async (reviewerIds: string[]) => {
    if (!selectedManuscriptId) return false
    const toastId = toast.loading('Assigning reviewers...')
    try {
      const token = await authService.getAccessToken()
      if (!token) throw new Error('Please sign in again.')
      for (const reviewerId of reviewerIds) {
        await fetch('/api/v1/reviews/assign', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ manuscript_id: selectedManuscriptId, reviewer_id: reviewerId }),
        })
      }
      toast.success('Assigned.', { id: toastId })
      setIsAssignModalOpen(false)
      setRefreshKey((k) => k + 1)
      return true
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Assign failed', { id: toastId })
      return false
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <SiteHeader />
      <main className="mx-auto max-w-[1600px] px-4 py-10 sm:px-8 lg:px-10 space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="mt-1 rounded-xl bg-white p-2 shadow-sm ring-1 ring-slate-200">
              <Table2 className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-bold text-slate-900 tracking-tight">Manuscripts Process</h1>
              <p className="mt-1 text-slate-500 font-medium">统一表格视图管理稿件生命周期</p>
            </div>
          </div>
          <Link href="/dashboard?tab=editor" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
            <ArrowLeft className="h-4 w-4" />
            返回编辑台
          </Link>
        </div>

        <Suspense
          fallback={
            <div className="rounded-xl border border-slate-200 bg-white p-10 text-sm text-slate-500">
              Loading…
            </div>
          }
        >
          <ManuscriptsProcessPanel
            refreshKey={refreshKey}
            onAssign={(row) => {
              setSelectedManuscriptId(row.id)
              setIsAssignModalOpen(true)
            }}
            onDecide={(row) => {
              window.location.href = `/editor/decision/${encodeURIComponent(row.id)}`
            }}
          />
        </Suspense>
      </main>

      {isAssignModalOpen && selectedManuscriptId && (
        <ReviewerAssignModal
          isOpen={isAssignModalOpen}
          onClose={() => setIsAssignModalOpen(false)}
          onAssign={handleAssignReviewer}
          manuscriptId={selectedManuscriptId}
        />
      )}
    </div>
  )
}
