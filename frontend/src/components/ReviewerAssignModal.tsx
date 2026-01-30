'use client'

import { useState, useEffect } from 'react'
import { X, Search, Users, Check } from 'lucide-react'
import { authService } from '@/services/auth'
import { toast } from 'sonner'
import { analyzeReviewerMatchmaking, ReviewerRecommendation } from '@/services/matchmaking'

interface Reviewer {
  id: string
  name: string
  email: string
  affiliation: string
  expertise: string[]
  review_count: number
}

interface ReviewerAssignModalProps {
  isOpen: boolean
  onClose: () => void
  onAssign: (reviewerIds: string[]) => void
  manuscriptId?: string
}

export default function ReviewerAssignModal({
  isOpen,
  onClose,
  onAssign,
  manuscriptId
}: ReviewerAssignModalProps) {
  const [reviewers, setReviewers] = useState<Reviewer[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedReviewers, setSelectedReviewers] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiRecommendations, setAiRecommendations] = useState<ReviewerRecommendation[]>([])
  const [aiMessage, setAiMessage] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      setSearchTerm('')
      setSelectedReviewers([])
      setAiRecommendations([])
      setAiMessage(null)
      fetchReviewers()
    }
  }, [isOpen])

  async function fetchReviewers() {
    setIsLoading(true)
    try {
      const token = await authService.getAccessToken()
      const response = await fetch('/api/v1/editor/available-reviewers', {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      if (!response.ok) {
        throw new Error(`Failed with status ${response.status}`)
      }
      const data = await response.json()
      if (data.success) {
        setReviewers(data.data)
      } else {
        setReviewers([])
        toast.error(data?.detail || data?.message || 'Failed to load reviewers.')
      }
    } catch (error) {
      console.error('Failed to fetch reviewers:', error)
      setReviewers([])
      toast.error('Failed to load reviewers.')
    } finally {
      setIsLoading(false)
    }
  }

  const filteredReviewers = reviewers.filter(reviewer =>
    reviewer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    reviewer.affiliation.toLowerCase().includes(searchTerm.toLowerCase()) ||
    reviewer.expertise.some(exp => exp.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  const handleAssign = () => {
    if (selectedReviewers.length > 0) {
      onAssign(selectedReviewers)
      onClose()
      setSelectedReviewers([])
    }
  }

  const handleAiAnalyze = async () => {
    if (!manuscriptId) {
      toast.error('Please select a manuscript first.')
      return
    }
    setAiLoading(true)
    setAiMessage(null)
    try {
      const result = await analyzeReviewerMatchmaking(manuscriptId)
      setAiRecommendations(result.recommendations || [])
      if (result.insufficient_data) {
        setAiMessage(result.message || 'Insufficient reviewer data.')
      } else if ((result.recommendations || []).length === 0) {
        setAiMessage('No highly matching reviewers found. Try manual search.')
      }
    } catch (error) {
      console.error('AI analysis failed:', error)
      setAiRecommendations([])
      setAiMessage('Analysis unavailable. Please try again later.')
    } finally {
      setAiLoading(false)
    }
  }

  const handleInviteFromAi = (reviewerId: string) => {
    onAssign([reviewerId])
    onClose()
    setSelectedReviewers([])
  }

  const toggleReviewer = (reviewerId: string) => {
    setSelectedReviewers((prev) =>
      prev.includes(reviewerId)
        ? prev.filter((id) => id !== reviewerId)
        : [...prev, reviewerId]
    )
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" data-testid="reviewer-modal">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <Users className="h-6 w-6 text-blue-600" />
            <h2 className="text-xl font-bold text-slate-900">Assign Reviewer</h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="font-semibold text-slate-900">AI Recommendations</div>
              <button
                type="button"
                onClick={handleAiAnalyze}
                disabled={aiLoading || !manuscriptId}
                className="px-3 py-2 text-sm font-semibold rounded-md bg-slate-900 text-white hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
                data-testid="ai-analyze"
              >
                {aiLoading ? 'Analyzing...' : 'AI Analysis'}
              </button>
            </div>

            {aiLoading && (
              <div className="mt-3 flex items-center text-sm text-slate-600">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span className="ml-2">Running local embedding match...</span>
              </div>
            )}

            {!aiLoading && aiMessage && (
              <div className="mt-3 text-sm text-slate-600" data-testid="ai-message">
                {aiMessage}
              </div>
            )}

            {!aiLoading && aiRecommendations.length > 0 && (
              <div className="mt-4 space-y-2" data-testid="ai-recommendations">
                {aiRecommendations.map((rec) => (
                  <div key={rec.reviewer_id} className="flex items-center justify-between rounded-md border border-slate-200 p-3 hover:bg-slate-50">
                    <div className="min-w-0">
                      <div className="font-medium text-slate-900 truncate">{rec.name || rec.email}</div>
                      <div className="text-xs text-slate-500 truncate">{rec.email}</div>
                      <div className="text-xs text-slate-400 mt-1">
                        Match Score: {(rec.match_score * 100).toFixed(1)}%
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleInviteFromAi(rec.reviewer_id)}
                      className="ml-3 px-3 py-2 text-sm font-semibold rounded-md bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                      data-testid={`ai-invite-${rec.reviewer_id}`}
                    >
                      Invite
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search reviewers by name, affiliation, or expertise..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                data-testid="reviewer-search"
              />
            </div>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-slate-600">Loading reviewers...</span>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between text-xs text-slate-500 mb-3">
                <span>Select 2-3 reviewers for this manuscript.</span>
                <span>{selectedReviewers.length} selected</span>
              </div>
              <div className="space-y-3">
                {filteredReviewers.map(reviewer => (
                  <div
                    key={reviewer.id}
                    className={`p-4 border rounded-lg cursor-pointer transition-all ${
                      selectedReviewers.includes(reviewer.id)
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                    onClick={() => toggleReviewer(reviewer.id)}
                    data-testid={`reviewer-item-${reviewer.id}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-medium text-slate-900">
                          {reviewer.name}
                        </div>
                        <div className="text-sm text-slate-500 mt-1">
                          {reviewer.affiliation}
                        </div>
                        {reviewer.expertise.length > 0 && (
                          <div className="flex flex-wrap gap-2 mt-2">
                            {reviewer.expertise.slice(0, 3).map(exp => (
                              <span
                                key={exp}
                                className="px-2 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded"
                              >
                                {exp}
                              </span>
                            ))}
                            {reviewer.expertise.length > 3 && (
                              <span className="text-xs text-slate-400">+{reviewer.expertise.length - 3}</span>
                            )}
                          </div>
                        )}
                      </div>
                      {selectedReviewers.includes(reviewer.id) && (
                        <Check className="h-5 w-5 text-blue-600" />
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-3 text-xs text-slate-400">
                      <span>Reviews: {reviewer.review_count}</span>
                    </div>
                  </div>
                ))}

                {filteredReviewers.length === 0 && (
                  <div className="text-center py-8 text-slate-500">
                    No reviewers found matching "{searchTerm}"
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <div className="flex items-center justify-between p-6 border-t border-slate-200 bg-slate-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-600 hover:text-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleAssign}
            disabled={selectedReviewers.length === 0}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
            data-testid="reviewer-assign"
          >
            Assign {selectedReviewers.length || ''} Reviewer{selectedReviewers.length === 1 ? '' : 's'}
          </button>
        </div>
      </div>
    </div>
  )
}
