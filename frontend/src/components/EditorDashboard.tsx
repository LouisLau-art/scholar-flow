'use client'

import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import EditorPipeline from '@/components/EditorPipeline'
import ReviewerAssignModal from '@/components/ReviewerAssignModal'
import DecisionPanel from '@/components/DecisionPanel'

export default function EditorDashboard() {
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false)
  const [selectedManuscriptId, setSelectedManuscriptId] = useState<string | undefined>()

  const handleAssignReviewer = (reviewerId: string) => {
    console.log('Assigning reviewer', reviewerId, 'to manuscript', selectedManuscriptId)
    // TODO: Call API to assign reviewer
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-serif font-bold text-slate-900">Editor Command Center</h1>
          <p className="text-slate-600 mt-2">
            Manage manuscript pipeline, assign reviewers, and make final decisions
          </p>
        </div>

        <Tabs defaultValue="pipeline" className="space-y-6">
          <TabsList className="bg-white border border-slate-200 p-1 rounded-lg">
            <TabsTrigger value="pipeline" data-testid="editor-tab-pipeline">Pipeline</TabsTrigger>
            <TabsTrigger value="reviewers" data-testid="editor-tab-reviewers">Reviewers</TabsTrigger>
            <TabsTrigger value="decisions" data-testid="editor-tab-decisions">Decisions</TabsTrigger>
          </TabsList>

          <TabsContent value="pipeline" className="space-y-6">
            <EditorPipeline />
          </TabsContent>

          <TabsContent value="reviewers" className="space-y-6">
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h2 className="text-xl font-bold text-slate-900 mb-4">Reviewer Management</h2>
              <p className="text-slate-600 mb-6">
                Browse and manage your pool of expert reviewers. Click on a reviewer to view details or assign them to manuscripts.
              </p>
              <button
                onClick={() => {
                  setSelectedManuscriptId('test-manuscript-id')
                  setIsAssignModalOpen(true)
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                data-testid="editor-open-assign"
              >
                Open Assign Modal (Demo)
              </button>
            </div>
          </TabsContent>

          <TabsContent value="decisions" className="space-y-6">
            <DecisionPanel
              manuscriptId="test-manuscript-id"
              reviewerScores={[
                {
                  reviewer_id: 'reviewer-1',
                  name: 'Dr. Jane Smith',
                  overall_score: 8.5,
                  technical_score: 9,
                  clarity_score: 8,
                  originality_score: 8,
                  comments: 'Excellent methodology and clear presentation'
                },
                {
                  reviewer_id: 'reviewer-2',
                  name: 'Prof. John Doe',
                  overall_score: 7.5,
                  technical_score: 8,
                  clarity_score: 7,
                  originality_score: 8,
                  comments: 'Good research but needs more discussion'
                }
              ]}
            />
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
