'use client'

import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import EditorPipeline from '@/components/EditorPipeline'
import ReviewerAssignModal from '@/components/ReviewerAssignModal'
import DecisionPanel from '@/components/DecisionPanel'
import CmsManagementPanel from '@/components/cms/CmsManagementPanel'
import { toast } from 'sonner'
import { authService } from '@/services/auth'
import Link from 'next/link'
import { BarChart3 } from 'lucide-react'

export default function EditorDashboard() {
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false)
  const [selectedManuscriptId, setSelectedManuscriptId] = useState<string | undefined>()
  const [selectedManuscriptTitle, setSelectedManuscriptTitle] = useState<string | undefined>()
  const [activeTab, setActiveTab] = useState<'pipeline' | 'reviewers' | 'decisions' | 'website'>('pipeline')
  const [pipelineRefresh, setPipelineRefresh] = useState(0)

  const handleAssignReviewer = async (reviewerIds: string[]) => {
    if (!selectedManuscriptId) {
      toast.error('Please select a manuscript first.')
      return
    }
    const toastId = toast.loading(`Assigning ${reviewerIds.length} reviewer${reviewerIds.length === 1 ? '' : 's'}...`)
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error('Please sign in again.', { id: toastId })
        return
      }
      let failures = 0
      for (const reviewerId of reviewerIds) {
        const response = await fetch('/api/v1/reviews/assign', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            manuscript_id: selectedManuscriptId,
            reviewer_id: reviewerId,
          }),
        })
        const data = await response.json()
        if (!data?.success) {
          failures += 1
        }
      }
      if (failures === 0) {
        toast.success('Reviewer assignment complete.', { id: toastId })
      } else {
        toast.error(`Assigned with ${failures} failure(s).`, { id: toastId })
      }
      setIsAssignModalOpen(false)
      setActiveTab('pipeline')
      setPipelineRefresh((prev) => prev + 1)
    } catch (error) {
      toast.error('Assign failed. Please try again.', { id: toastId })
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-serif font-bold text-slate-900">Editor Command Center</h1>
            <p className="text-slate-600 mt-2">
              Manage manuscript pipeline, assign reviewers, and make final decisions
            </p>
          </div>
          <Link
            href="/editor/analytics"
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <BarChart3 className="h-4 w-4" />
            Analytics Dashboard
          </Link>
        </div>

          <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as typeof activeTab)} className="space-y-6">
          <TabsList className="border border-border bg-background p-1">
            <TabsTrigger value="pipeline" data-testid="editor-tab-pipeline">Pipeline</TabsTrigger>
            <TabsTrigger value="reviewers" data-testid="editor-tab-reviewers">Reviewers</TabsTrigger>
            <TabsTrigger value="decisions" data-testid="editor-tab-decisions">Decisions</TabsTrigger>
            <TabsTrigger value="website" data-testid="editor-tab-website">Website</TabsTrigger>
          </TabsList>

          <TabsContent value="pipeline" className="space-y-6">
            <EditorPipeline
              onAssign={(manuscript) => {
                setSelectedManuscriptId(manuscript.id)
                setSelectedManuscriptTitle(manuscript.title)
                setIsAssignModalOpen(true)
                setActiveTab('reviewers')
              }}
              onDecide={(manuscript) => {
                setSelectedManuscriptId(manuscript.id)
                setSelectedManuscriptTitle(manuscript.title)
                setActiveTab('decisions')
              }}
              refreshKey={pipelineRefresh}
            />
          </TabsContent>

          <TabsContent value="reviewers" className="space-y-6">
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h2 className="text-xl font-bold text-slate-900 mb-4">Reviewer Management</h2>
              <p className="text-slate-600 mb-6">
                Browse and manage your pool of expert reviewers. Click on a reviewer to view details or assign them to manuscripts.
              </p>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600 mb-6">
                {selectedManuscriptId ? (
                  <>Selected manuscript: <span className="font-semibold text-slate-900">{selectedManuscriptTitle}</span></>
                ) : (
                  <>No manuscript selected. Go to the <span className="font-semibold text-slate-900">Pipeline</span> tab and click “Assign Reviewers”.</>
                )}
              </div>
              <Button
                onClick={() => {
                  setIsAssignModalOpen(true)
                }}
                disabled={!selectedManuscriptId}
                data-testid="editor-open-assign"
              >
                Assign Reviewers
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="decisions" className="space-y-6">
            {selectedManuscriptId ? (
              <DecisionPanel
                manuscriptId={selectedManuscriptId}
                reviewerScores={[]}
                onSubmitted={() => {
                  setPipelineRefresh((prev) => prev + 1)
                  setActiveTab('pipeline')
                }}
              />
            ) : (
              <div className="bg-white rounded-xl border border-slate-200 p-8 text-slate-600">
                No manuscript selected. Go to the <span className="font-semibold text-slate-900">Pipeline</span> tab and click “Make Decision”.
              </div>
            )}
          </TabsContent>

          <TabsContent value="website" className="space-y-6">
            <CmsManagementPanel />
          </TabsContent>
        </Tabs>

        {/* Assign Modal */}
        {isAssignModalOpen && selectedManuscriptId && (
          <ReviewerAssignModal
            isOpen={isAssignModalOpen}
            onClose={() => setIsAssignModalOpen(false)}
            onAssign={handleAssignReviewer}
            manuscriptId={selectedManuscriptId}
          />
        )}
      </div>
    </div>
  )
}
