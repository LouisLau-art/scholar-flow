'use client'

import { useState, useEffect, useRef } from 'react'
import { FileText, Users, CheckCircle2, ArrowRight, Loader2 } from 'lucide-react'
import { authService } from '@/services/auth'
import { Button } from '@/components/ui/button'

type Manuscript = {
  id: string
  title: string
  status?: string
  created_at?: string
  review_count?: number
}

type PipelineStage = 'pending_quality' | 'under_review' | 'pending_decision' | 'published'

interface EditorPipelineProps {
  onAssign?: (manuscript: Manuscript) => void
  onDecide?: (manuscript: Manuscript) => void
  refreshKey?: number
}

export default function EditorPipeline({ onAssign, onDecide, refreshKey }: EditorPipelineProps) {
  const [pipelineData, setPipelineData] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState<PipelineStage | null>(null)
  const listRef = useRef<HTMLDivElement | null>(null)

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
  }, [refreshKey])

  const handleFilterClick = (stage: PipelineStage) => {
    setActiveFilter(stage)
    requestAnimationFrame(() => {
      listRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }

  const clearFilter = () => {
    setActiveFilter(null)
  }

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
        <button
          type="button"
          onClick={() => handleFilterClick('pending_quality')}
          className={`text-left bg-white rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'pending_quality'
              ? 'border-blue-400 bg-blue-50'
              : 'border-slate-200 hover:border-blue-200 hover:bg-blue-50/50'
          }`}
        >
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
        </button>

        {/* 评审中 */}
        <button
          type="button"
          onClick={() => handleFilterClick('under_review')}
          className={`text-left bg-white rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'under_review'
              ? 'border-amber-400 bg-amber-50'
              : 'border-slate-200 hover:border-amber-200 hover:bg-amber-50/50'
          }`}
        >
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
        </button>

        {/* 待录用 */}
        <button
          type="button"
          onClick={() => handleFilterClick('pending_decision')}
          className={`text-left bg-white rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'pending_decision'
              ? 'border-purple-400 bg-purple-50'
              : 'border-slate-200 hover:border-purple-200 hover:bg-purple-50/50'
          }`}
        >
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
        </button>

        {/* 已发布 */}
        <button
          type="button"
          onClick={() => handleFilterClick('published')}
          className={`text-left bg-white rounded-xl border p-6 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            activeFilter === 'published'
              ? 'border-emerald-400 bg-emerald-50'
              : 'border-slate-200 hover:border-emerald-200 hover:bg-emerald-50/50'
          }`}
        >
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
        </button>
      </div>

      {/* 详细列表 */}
      <div ref={listRef} className="bg-white rounded-xl border border-slate-200 p-6" data-testid="editor-pipeline-list">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h3 className="text-lg font-semibold text-slate-900">Recent Activity</h3>
          {activeFilter && (
            <Button variant="ghost" size="sm" onClick={clearFilter}>
              Clear Filter
            </Button>
          )}
        </div>
        <div className="space-y-4">
          {activeFilter === 'pending_quality' && (pipelineData?.pending_quality || []).length === 0 && (
            <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center text-slate-500">
              No manuscripts in Pending Quality Check.
            </div>
          )}
          {activeFilter === 'under_review' && (pipelineData?.under_review || []).length === 0 && (
            <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center text-slate-500">
              No manuscripts currently under review.
            </div>
          )}
          {activeFilter === 'pending_decision' && (pipelineData?.pending_decision || []).length === 0 && (
            <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center text-slate-500">
              No manuscripts awaiting final decision.
            </div>
          )}
          {activeFilter === 'published' && (pipelineData?.published || []).length === 0 && (
            <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center text-slate-500">
              No manuscripts published yet.
            </div>
          )}

          {!activeFilter && (pipelineData?.pending_quality || []).slice(0, 3).map((manuscript: any) => (
            <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
              <div>
                <div className="font-medium text-slate-900">{manuscript.title}</div>
                <div className="text-sm text-slate-500">
                  Submitted: {manuscript.created_at ? new Date(manuscript.created_at).toLocaleDateString() : '—'}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-yellow-100 text-yellow-800 text-sm font-medium rounded-full">
                  Pending QA
                </span>
                <Button size="sm" onClick={() => onAssign?.(manuscript)}>
                  Assign Reviewers
                </Button>
              </div>
            </div>
          ))}

          {!activeFilter && (pipelineData?.under_review || []).slice(0, 3).map((manuscript: any) => (
            <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
              <div>
                <div className="font-medium text-slate-900">{manuscript.title}</div>
                <div className="text-sm text-slate-500">In review: {manuscript.review_count || 0} reviewers</div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
                  Reviewing
                </span>
                <Button variant="outline" size="sm" onClick={() => onDecide?.(manuscript)}>
                  View Decision
                </Button>
              </div>
            </div>
          ))}
          {!activeFilter && (pipelineData?.pending_decision || []).slice(0, 3).map((manuscript: any) => (
            <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
              <div>
                <div className="font-medium text-slate-900">{manuscript.title}</div>
                <div className="text-sm text-slate-500">Awaiting final decision</div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-purple-100 text-purple-800 text-sm font-medium rounded-full">
                  Pending Decision
                </span>
                <Button size="sm" onClick={() => onDecide?.(manuscript)}>
                  Make Decision
                </Button>
              </div>
            </div>
          ))}

          {activeFilter === 'under_review' && (pipelineData?.under_review || []).map((manuscript: any) => (
            <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
              <div>
                <div className="font-medium text-slate-900">{manuscript.title}</div>
                <div className="text-sm text-slate-500">In review: {manuscript.review_count || 0} reviewers</div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
                  Reviewing
                </span>
                <Button variant="outline" size="sm" onClick={() => onDecide?.(manuscript)}>
                  View Decision
                </Button>
              </div>
            </div>
          ))}

          {activeFilter === 'pending_decision' && (pipelineData?.pending_decision || []).map((manuscript: any) => (
            <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
              <div>
                <div className="font-medium text-slate-900">{manuscript.title}</div>
                <div className="text-sm text-slate-500">Awaiting final decision</div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-purple-100 text-purple-800 text-sm font-medium rounded-full">
                  Pending Decision
                </span>
                <Button size="sm" onClick={() => onDecide?.(manuscript)}>
                  Make Decision
                </Button>
              </div>
            </div>
          ))}

          {activeFilter === 'pending_quality' && (pipelineData?.pending_quality || []).map((manuscript: any) => (
            <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
              <div>
                <div className="font-medium text-slate-900">{manuscript.title}</div>
                <div className="text-sm text-slate-500">
                  Submitted: {manuscript.created_at ? new Date(manuscript.created_at).toLocaleDateString() : '—'}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-yellow-100 text-yellow-800 text-sm font-medium rounded-full">
                  Pending QA
                </span>
                <Button size="sm" onClick={() => onAssign?.(manuscript)}>
                  Assign Reviewers
                </Button>
              </div>
            </div>
          ))}

          {activeFilter === 'published' && (pipelineData?.published || []).map((manuscript: any) => (
            <div key={manuscript.id} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg hover:bg-slate-50">
              <div>
                <div className="font-medium text-slate-900">{manuscript.title}</div>
                <div className="text-sm text-slate-500">Published</div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-emerald-100 text-emerald-800 text-sm font-medium rounded-full">
                  Published
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
