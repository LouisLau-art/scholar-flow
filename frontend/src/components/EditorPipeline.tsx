'use client'

import { useState, useEffect } from 'react'
import { FileText, Users, CheckCircle2, ArrowRight, Loader2 } from 'lucide-react'
import { authService } from '@/services/auth'

export default function EditorPipeline() {
  const [pipelineData, setPipelineData] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function fetchPipelineData() {
      try {
        const token = await authService.getAccessToken()
        const response = await fetch('/api/v1/editor/pipeline', {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        })
        const data = await response.json()
        if (data.success) {
          setPipelineData(data.data)
        }
      } catch (error) {
        console.error('Failed to fetch pipeline data:', error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchPipelineData()
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-slate-600">Loading pipeline data...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6" data-testid="editor-pipeline">
      <h2 className="text-2xl font-bold text-slate-900">Manuscript Pipeline</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* 待质检 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Pending Quality Check</h3>
            <FileText className="h-5 w-5 text-blue-600" />
          </div>
          <div className="text-3xl font-bold text-blue-600 mb-2">
            {pipelineData?.pending_quality?.length || 0}
          </div>
          <div className="text-sm text-slate-500">
            Manuscripts awaiting review
          </div>
        </div>

        {/* 评审中 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Under Review</h3>
            <Users className="h-5 w-5 text-yellow-600" />
          </div>
          <div className="text-3xl font-bold text-yellow-600 mb-2">
            {pipelineData?.under_review?.length || 0}
          </div>
          <div className="text-sm text-slate-500">
            Manuscripts in peer review
          </div>
        </div>

        {/* 待录用 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Pending Decision</h3>
            <CheckCircle2 className="h-5 w-5 text-purple-600" />
          </div>
          <div className="text-3xl font-bold text-purple-600 mb-2">
            {pipelineData?.pending_decision?.length || 0}
          </div>
          <div className="text-sm text-slate-500">
            Manuscripts awaiting final decision
          </div>
        </div>

        {/* 已发布 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">Published</h3>
            <ArrowRight className="h-5 w-5 text-green-600" />
          </div>
          <div className="text-3xl font-bold text-green-600 mb-2">
            {pipelineData?.published?.length || 0}
          </div>
          <div className="text-sm text-slate-500">
            Manuscripts published this month
          </div>
        </div>
      </div>

      {/* 详细列表 */}
      <div className="bg-white rounded-xl border border-slate-200 p-6" data-testid="editor-pipeline-list">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Recent Activity</h3>
        <div className="space-y-4">
          {(pipelineData?.pending_quality || []).slice(0, 3).map((manuscript: any) => (
            <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
              <div>
                <div className="font-medium text-slate-900">{manuscript.title}</div>
                <div className="text-sm text-slate-500">Submitted: {new Date(manuscript.created_at).toLocaleDateString()}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-yellow-100 text-yellow-800 text-sm font-medium rounded-full">
                  Pending QA
                </span>
              </div>
            </div>
          ))}
          {(pipelineData?.under_review || []).slice(0, 3).map((manuscript: any) => (
            <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
              <div>
                <div className="font-medium text-slate-900">{manuscript.title}</div>
                <div className="text-sm text-slate-500">In review: {manuscript.review_count || 0} reviewers</div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
                  Reviewing
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
