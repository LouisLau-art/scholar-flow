'use client'

import { useState, useEffect, useCallback } from 'react'
import { X, Search, Users, Check, UserPlus } from 'lucide-react'
import { InviteReviewerDialog } from '@/components/admin/InviteReviewerDialog'
import { adminUserService } from '@/services/admin/userService'
import { authService } from '@/services/auth'
import { toast } from 'sonner'
import { User } from '@/types/user'
import { analyzeReviewerMatchmaking, ReviewerRecommendation } from '@/services/matchmaking'

interface ReviewerAssignModalProps {
  isOpen: boolean
  onClose: () => void
  onAssign: (reviewerIds: string[]) => void // 统一为多选
  manuscriptId: string
}

export default function ReviewerAssignModal({
  isOpen,
  onClose,
  onAssign,
  manuscriptId
}: ReviewerAssignModalProps) {
  const [reviewers, setReviewers] = useState<User[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedReviewers, setSelectedReviewers] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  
  // AI State
  const [aiLoading, setAiLoading] = useState(false)
  const [aiRecommendations, setAiRecommendations] = useState<ReviewerRecommendation[]>([])
  const [aiMessage, setAiMessage] = useState<string | null>(null)

  // Invite Dialog
  const [isInviteDialogOpen, setIsInviteDialogOpen] = useState(false)

  // 019: Existing Reviewers State
  const [existingReviewers, setExistingReviewers] = useState<any[]>([])
  const [loadingExisting, setLoadingExisting] = useState(false)

  const fetchExistingReviewers = useCallback(async () => {
    if (!manuscriptId) return
    setLoadingExisting(true)
    try {
      const token = await authService.getAccessToken()
      const res = await fetch(`/api/v1/reviews/assignments/${manuscriptId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      const data = await res.json()
      if (data.success) {
        setExistingReviewers(data.data)
      }
    } catch (e) {
      console.error("Failed to load existing reviewers", e)
    } finally {
      setLoadingExisting(false)
    }
  }, [manuscriptId])

  const handleUnassign = async (assignmentId: string) => {
    if (!confirm("Are you sure you want to remove this reviewer?")) return
    try {
      const token = await authService.getAccessToken()
      const res = await fetch(`/api/v1/reviews/assign/${assignmentId}`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      if (res.ok) {
        toast.success("Reviewer removed")
        fetchExistingReviewers()
      } else {
        toast.error("Failed to remove reviewer")
      }
    } catch (e) {
      toast.error("Error removing reviewer")
    }
  }

  const fetchReviewers = useCallback(async () => {
    setIsLoading(true)
    try {
      // 017: 使用 Admin API 获取审稿人列表 (分页, 搜索)
      const response = await adminUserService.getUsers(1, 100, searchTerm, 'reviewer')
      // Filter out already assigned reviewers
      // Ideally backend handles this, but client-side filter is ok for small lists
      // We rely on existingReviewers state which might not be ready yet if fetched in parallel.
      // But let's just show all, and maybe disable selection if already assigned? 
      // Or just filter.
      setReviewers(response.data)
    } catch (error) {
      console.error('Failed to fetch reviewers:', error)
      toast.error('Failed to load reviewers')
    } finally {
      setIsLoading(false)
    }
  }, [searchTerm])

  useEffect(() => {
    if (isOpen) {
      setSearchTerm('')
      setSelectedReviewers([])
      setAiRecommendations([])
      setAiMessage(null)
      fetchReviewers()
      fetchExistingReviewers()
    }
  }, [isOpen, fetchReviewers, fetchExistingReviewers])

  const handleAssign = () => {
    if (selectedReviewers.length > 0) {
      onAssign(selectedReviewers)
      onClose()
      setSelectedReviewers([])
    }
  }

  // HEAD: AI 推荐逻辑
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
    // 选中该推荐人
    toggleReviewer(reviewerId)
  }

  // 017: 邀请外部人员逻辑
  const handleInviteConfirm = async (email: string, fullName: string) => {
    try {
      await adminUserService.inviteReviewer({
        email,
        full_name: fullName,
        manuscript_id: manuscriptId
      })
      toast.success('Reviewer invited successfully!')
      fetchReviewers()
      setIsInviteDialogOpen(false)
    } catch (error) {
      console.error('Invite failed:', error)
      throw error // Let dialog handle error
    }
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
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center" data-testid="reviewer-modal">
        <div
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        />

        <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
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

          <div className="p-6 overflow-y-auto flex-1">
            {/* Existing Reviewers */}
            {existingReviewers.length > 0 && (
              <div className="mb-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
                <h3 className="font-semibold text-slate-900 mb-3">Current Reviewers ({existingReviewers.length})</h3>
                <div className="space-y-2">
                  {existingReviewers.map((r) => (
                    <div key={r.id} className="flex items-center justify-between bg-white p-3 rounded border border-slate-200 shadow-sm">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">
                          {r.reviewer_name?.charAt(0) || '?'}
                        </div>
                        <div>
                          <div className="font-medium text-slate-900 text-sm">{r.reviewer_name}</div>
                          <div className="text-xs text-slate-500">{r.reviewer_email}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                          r.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                        }`}>
                          {r.status}
                        </span>
                        <button
                          onClick={() => handleUnassign(r.id)}
                          className="text-red-600 hover:text-red-800 text-xs font-medium px-2 py-1 rounded hover:bg-red-50 transition-colors"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* AI Analysis Section */}
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
                        className={`ml-3 px-3 py-2 text-sm font-semibold rounded-md transition-colors ${
                          selectedReviewers.includes(rec.reviewer_id)
                           ? 'bg-green-100 text-green-700 hover:bg-green-200'
                           : 'bg-blue-600 text-white hover:bg-blue-700'
                        }`}
                        data-testid={`ai-invite-${rec.reviewer_id}`}
                      >
                        {selectedReviewers.includes(rec.reviewer_id) ? 'Selected' : 'Select'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Manual Search & List */}
            <div className="mb-6 flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search reviewers by name..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  data-testid="reviewer-search"
                />
              </div>
              <button
                onClick={() => setIsInviteDialogOpen(true)}
                className="flex items-center gap-2 px-3 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors text-sm font-medium"
              >
                <UserPlus className="h-4 w-4" />
                Invite New
              </button>
            </div>

            {isLoading ? (
              <div className="flex justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : reviewers.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                No reviewers found. Invite a new one?
              </div>
            ) : (
              <div className="space-y-2">
                {reviewers.map((reviewer) => (
                  <div
                    key={reviewer.id}
                    onClick={() => toggleReviewer(reviewer.id)}
                    className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all border ${
                      selectedReviewers.includes(reviewer.id)
                        ? 'bg-blue-50 border-blue-200 shadow-sm'
                        : 'hover:bg-slate-50 border-transparent hover:border-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`h-10 w-10 rounded-full flex items-center justify-center text-sm font-medium ${
                        selectedReviewers.includes(reviewer.id) ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {reviewer.full_name?.charAt(0) || reviewer.email.charAt(0)}
                      </div>
                      <div>
                        <div className={`font-medium ${selectedReviewers.includes(reviewer.id) ? 'text-blue-900' : 'text-slate-900'}`}>
                          {reviewer.full_name || 'Unnamed'}
                        </div>
                        <div className="text-sm text-slate-500">{reviewer.email}</div>
                      </div>
                    </div>
                    {selectedReviewers.includes(reviewer.id) && (
                      <Check className="h-5 w-5 text-blue-600" />
                    )}
                  </div>
                ))}
              </div>
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

      <InviteReviewerDialog 
        isOpen={isInviteDialogOpen} 
        onClose={() => setIsInviteDialogOpen(false)} 
        onConfirm={handleInviteConfirm}
      />
    </>
  )
}
