'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { X, Search, Users, Check, UserPlus } from 'lucide-react'
import { authService } from '@/services/auth'
import { toast } from 'sonner'
import { User } from '@/types/user'
import { analyzeReviewerMatchmaking, ReviewerRecommendation } from '@/services/matchmaking'
import { EditorApi } from '@/services/editorApi'
import { AddReviewerModal } from '@/components/editor/AddReviewerModal'

type StaffProfile = {
  id: string
  email?: string | null
  full_name?: string | null
  roles?: string[]
}

interface ReviewerAssignModalProps {
  isOpen: boolean
  onClose: () => void
  onAssign: (reviewerIds: string[]) => Promise<boolean> | boolean | void // 统一为多选；返回 false 表示不要自动关闭
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
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  // AI State
  const [aiLoading, setAiLoading] = useState(false)
  const [aiRecommendations, setAiRecommendations] = useState<ReviewerRecommendation[]>([])
  const [aiMessage, setAiMessage] = useState<string | null>(null)

  // Add to Library Dialog（仅录入，不发邮件）
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)

  // 019: Existing Reviewers State
  const [existingReviewers, setExistingReviewers] = useState<any[]>([])
  const [loadingExisting, setLoadingExisting] = useState(false)
  const [pendingRemove, setPendingRemove] = useState<any | null>(null)
  const [removingId, setRemovingId] = useState<string | null>(null)

  // Feature 023: Internal Owner Binding（KPI 归属人）
  const [internalStaff, setInternalStaff] = useState<StaffProfile[]>([])
  const [ownerId, setOwnerId] = useState<string>('') // '' 表示未绑定
  const [ownerSearch, setOwnerSearch] = useState('')
  const [loadingOwner, setLoadingOwner] = useState(false)
  const [savingOwner, setSavingOwner] = useState(false)

  const fetchOwner = useCallback(async () => {
    if (!manuscriptId) return
    setLoadingOwner(true)
    try {
      const res = await fetch(`/api/v1/manuscripts/articles/${manuscriptId}`)
      const payload = await res.json().catch(() => null)
      const ms = payload?.data || {}
      const raw = ms?.owner_id || ms?.kpi_owner_id || ''
      setOwnerId(typeof raw === 'string' ? raw : raw ? String(raw) : '')
    } catch (e) {
      console.error('Failed to load manuscript owner', e)
      setOwnerId('')
    } finally {
      setLoadingOwner(false)
    }
  }, [manuscriptId])

  const fetchInternalStaff = useCallback(async () => {
    try {
      const token = await authService.getAccessToken()
      if (!token) return
      const res = await fetch('/api/v1/editor/internal-staff', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const payload = await res.json().catch(() => null)
      if (!res.ok || !payload?.success) {
        setInternalStaff([])
        return
      }
      setInternalStaff(payload.data || [])
    } catch (e) {
      console.error('Failed to load internal staff', e)
      setInternalStaff([])
    }
  }, [])

  const fetchExistingReviewers = useCallback(async () => {
    if (!manuscriptId) return
    setLoadingExisting(true)
    try {
      const token = await authService.getAccessToken()
      const res = await fetch(`/api/v1/reviews/assignments/${manuscriptId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      const data = await res.json().catch(() => null)
      if (!res.ok || !data?.success) {
        toast.error(data?.detail || data?.message || 'Failed to load current reviewers')
        setExistingReviewers([])
        return
      }
      setExistingReviewers(data.data || [])
    } catch (e) {
      console.error("Failed to load existing reviewers", e)
      toast.error('Failed to load current reviewers')
    } finally {
      setLoadingExisting(false)
    }
  }, [manuscriptId])

  const handleUnassign = async (assignmentId: string) => {
    try {
      setRemovingId(assignmentId)
      const token = await authService.getAccessToken()
      const res = await fetch(`/api/v1/reviews/assign/${assignmentId}`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      if (res.ok) {
        toast.success("Reviewer removed")
        fetchExistingReviewers()
      } else {
        const text = await res.text().catch(() => '')
        let detail = ''
        try {
          const j = JSON.parse(text || '{}')
          detail = j?.detail || j?.message || ''
        } catch {
          detail = text
        }
        toast.error(detail || "Failed to remove reviewer")
      }
    } catch (e) {
      toast.error("Error removing reviewer")
    } finally {
      setRemovingId(null)
    }
  }

  const fetchReviewers = useCallback(async () => {
    setIsLoading(true)
    try {
      const payload = await EditorApi.searchReviewerLibrary(searchTerm, 120)
      if (!payload?.success) throw new Error(payload?.detail || payload?.message || 'Failed to load reviewer library')
      setReviewers((payload.data || []) as User[])
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
      setPendingRemove(null)
      setOwnerSearch('')
      fetchReviewers()
      fetchExistingReviewers()
      fetchOwner()
      fetchInternalStaff()
    }
  }, [isOpen, fetchReviewers, fetchExistingReviewers, fetchOwner, fetchInternalStaff])

  const handleAssign = async () => {
    if (selectedReviewers.length > 0) {
      if (!ownerId) {
        toast.error('请先绑定 Internal Owner（用于 KPI 归属），再分配审稿人。')
        return
      }
      setIsSubmitting(true)
      try {
        const ret = await Promise.resolve(onAssign(selectedReviewers) as any)
        await fetchExistingReviewers()
        setSelectedReviewers([])
        if (ret !== false) {
          onClose()
        }
      } finally {
        setIsSubmitting(false)
      }
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

  // Feature 030: “添加审稿人”与“指派审稿人”解耦：这里仅允许从 Reviewer Library 选取并指派。

  // Derived state for quick lookup
  const assignedIds = useMemo(
    () =>
      (existingReviewers || [])
        .map((r) => String(r?.reviewer_id || '').trim())
        .filter(Boolean),
    [existingReviewers]
  )

  const pinnedAssignedUsers: User[] = useMemo(
    () =>
      (existingReviewers || [])
        .map((r) => ({
          id: String(r?.reviewer_id || '').trim(),
          email: String(r?.reviewer_email || '').trim(),
          full_name: (r?.reviewer_name ? String(r.reviewer_name) : null) as any,
          roles: ['reviewer'] as any,
          created_at: '',
          is_verified: true,
        }))
        .filter((u) => u.id && u.email),
    [existingReviewers]
  )

  const toggleReviewer = (reviewerId: string) => {
    // Prevent toggling if already assigned (though UI should disable it)
    if (assignedIds.includes(reviewerId)) return

    setSelectedReviewers((prev) =>
      prev.includes(reviewerId)
        ? prev.filter((id) => id !== reviewerId)
        : [...prev, reviewerId]
    )
  }

  const orderedReviewers: User[] = useMemo(() => {
    const assignedSet = new Set(assignedIds)
    const reviewerById = new Map(reviewers.map((r) => [r.id, r]))
    const mergedList: User[] = [
      // 置顶：已分配的审稿人（即便不在 reviewer pool 里也要显示）
      ...pinnedAssignedUsers.map((u) => reviewerById.get(u.id) || u),
      // 其余候选（去重）
      ...reviewers.filter((r) => !assignedSet.has(r.id)),
    ]

    // 重要：避免在 onSelect/checked 改变时重排（列表不跳动）。
    // - 已分配的审稿人固定置顶
    // - 其余候选保持后端返回顺序
    return mergedList
  }, [assignedIds, pinnedAssignedUsers, reviewers])

  if (!isOpen) return null

  const currentOwnerLabel = (() => {
    if (!ownerId) return 'Unassigned'
    const u = internalStaff.find((x) => x.id === ownerId)
    return u ? (u.full_name || u.email || u.id || 'Unassigned') : ownerId
  })()

  const qOwner = ownerSearch.trim().toLowerCase()
  const filteredInternalStaff: StaffProfile[] = (qOwner
    ? internalStaff.filter((u) => {
        const name = (u.full_name || '').toLowerCase()
        const email = (u.email || '').toLowerCase()
        return name.includes(qOwner) || email.includes(qOwner)
      })
    : internalStaff
  )
    .slice()
    .sort((a, b) => {
      // 置顶：当前已选 owner
      const aPinned = ownerId && a.id === ownerId
      const bPinned = ownerId && b.id === ownerId
      if (aPinned !== bPinned) return aPinned ? -1 : 1
      const aName = (a.full_name || a.email || '').toLowerCase()
      const bName = (b.full_name || b.email || '').toLowerCase()
      return aName.localeCompare(bName)
    })

  const handleOwnerChange = async (nextOwnerId: string) => {
    if (!manuscriptId) return
    const prev = ownerId
    setOwnerId(nextOwnerId)
    setSavingOwner(true)
    const toastId = toast.loading('Updating owner...')
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error('Please sign in again.', { id: toastId })
        setOwnerId(prev)
        return
      }
      const res = await fetch(`/api/v1/manuscripts/${manuscriptId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ owner_id: nextOwnerId ? nextOwnerId : null }),
      })
      const raw = await res.text().catch(() => '')
      let payload: any = null
      try {
        payload = raw ? JSON.parse(raw) : null
      } catch {
        payload = null
      }
      if (!res.ok || payload?.success === false) {
        const msg =
          payload?.detail ||
          payload?.message ||
          (typeof raw === 'string' && raw.trim() ? raw.trim() : '') ||
          `HTTP ${res.status}`
        throw new Error(msg)
      }
      toast.success('Owner updated', { id: toastId })
    } catch (e: any) {
      console.error('Failed to update owner', e)
      toast.error(e?.message || 'Failed to update owner', { id: toastId })
      setOwnerId(prev)
    } finally {
      setSavingOwner(false)
    }
  }

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
            {/* Feature 023: Owner Binding（KPI 归属人） */}
            <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="font-semibold text-slate-900">Internal Owner / Invited By</div>
                  <div className="text-xs text-slate-500 mt-1">
                    在初审阶段绑定负责人（仅 editor/admin），修改后自动保存并提示。
                  </div>
                </div>
                <div className="text-xs text-slate-500">
                  {savingOwner ? 'Saving…' : loadingOwner ? 'Loading…' : ''}
                </div>
              </div>

              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="Search internal staff..."
                  value={ownerSearch}
                  onChange={(e) => setOwnerSearch(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                />
                <select
                  value={ownerId}
                  onChange={(e) => handleOwnerChange(e.target.value)}
                  disabled={savingOwner || loadingOwner}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm disabled:bg-slate-50"
                  data-testid="owner-select"
                >
                  <option value="">Unassigned</option>
                  {filteredInternalStaff.map((u) => (
                    <option key={u.id} value={u.id}>
                      {(u.full_name || u.email || u.id) as string}
                    </option>
                  ))}
                </select>
              </div>

              <div className="mt-2 text-xs text-slate-600">
                Current: <span className="font-medium text-slate-900">{currentOwnerLabel}</span>
              </div>
              {!ownerId && (
                <div className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
                  未绑定 Owner：后端会拒绝分配审稿人（KPI 必须先绑定）。
                </div>
              )}
            </div>

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
                          onClick={() => setPendingRemove(r)}
                          className="text-red-600 hover:text-red-800 text-xs font-medium px-2 py-1 rounded hover:bg-red-50 transition-colors"
                          data-testid={`reviewer-remove-${r.id}`}
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
                onClick={() => setIsAddDialogOpen(true)}
                className="flex items-center gap-2 px-3 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors text-sm font-medium"
              >
                <UserPlus className="h-4 w-4" />
                Add to Library
              </button>
            </div>

            {isLoading ? (
              <div className="flex justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : orderedReviewers.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                No reviewers found. Add one to the library?
              </div>
            ) : (
              <div className="space-y-2" data-testid="reviewer-list">
                {orderedReviewers.map((reviewer) => {
                  const isAssigned = assignedIds.includes(reviewer.id)
                  const isSelected = selectedReviewers.includes(reviewer.id)
                  const showAsSelected = isAssigned || isSelected
                  
                  return (
                  <div
                    key={reviewer.id}
                    data-testid={`reviewer-row-${reviewer.id}`}
                    onClick={() => !isAssigned && toggleReviewer(reviewer.id)}
                    className={`flex items-center justify-between p-3 rounded-lg transition-all border ${
                      isAssigned 
                        ? 'bg-blue-50 border-blue-200 shadow-sm cursor-not-allowed'
                        : isSelected
                          ? 'bg-blue-50 border-blue-200 shadow-sm cursor-pointer'
                          : 'hover:bg-slate-50 border-transparent hover:border-slate-200 cursor-pointer'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`h-10 w-10 rounded-full flex items-center justify-center text-sm font-medium ${
                        showAsSelected ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {reviewer.full_name?.charAt(0) || reviewer.email.charAt(0)}
                      </div>
                      <div>
                        <div className={`font-medium ${showAsSelected ? 'text-blue-900' : 'text-slate-900'}`}>
                          {reviewer.full_name || 'Unnamed'}
                        </div>
                        <div className="text-sm text-slate-500">{reviewer.email}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {isAssigned && (
                        <span className="text-xs font-semibold bg-slate-200 text-slate-700 px-2 py-1 rounded">
                          Assigned
                        </span>
                      )}
                      {showAsSelected && <Check className="h-5 w-5 text-blue-600" />}
                    </div>
                  </div>
                  )
                })}
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
              disabled={selectedReviewers.length === 0 || isSubmitting}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
              data-testid="reviewer-assign"
            >
               {isSubmitting ? 'Assigning...' : `Assign ${selectedReviewers.length || ''} Reviewer${selectedReviewers.length === 1 ? '' : 's'}`}
            </button>
          </div>
        </div>
      </div>

      {/* 自定义确认弹窗：替代浏览器 confirm() */}
      {pendingRemove && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center" data-testid="unassign-confirm">
          <div className="absolute inset-0 bg-black/40" onClick={() => setPendingRemove(null)} />
          <div className="relative w-full max-w-md rounded-xl bg-white shadow-2xl border border-slate-200 p-6">
            <div className="text-base font-semibold text-slate-900">Remove reviewer?</div>
            <div className="mt-2 text-sm text-slate-600">
              This will remove the reviewer from the current manuscript.
            </div>
            <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div className="text-sm font-medium text-slate-900">{pendingRemove.reviewer_name || 'Unknown'}</div>
              <div className="text-xs text-slate-600">{pendingRemove.reviewer_email || ''}</div>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setPendingRemove(null)}
                className="px-4 py-2 text-slate-700 rounded-lg hover:bg-slate-100 transition-colors"
                data-testid="unassign-cancel"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  const id = String(pendingRemove.id)
                  setPendingRemove(null)
                  await handleUnassign(id)
                }}
                disabled={removingId === String(pendingRemove.id)}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
                data-testid="unassign-confirm-remove"
              >
                {removingId === String(pendingRemove.id) ? 'Removing...' : 'Remove'}
              </button>
            </div>
          </div>
        </div>
      )}

      <AddReviewerModal
        open={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
        mode="create"
        onSaved={() => fetchReviewers()}
      />
    </>
  )
}
