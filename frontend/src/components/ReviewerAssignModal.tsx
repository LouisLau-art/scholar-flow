'use client'

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { X, Search, Users, UserPlus } from 'lucide-react'
import { authService } from '@/services/auth'
import { toast } from 'sonner'
import { User } from '@/types/user'
import { analyzeReviewerMatchmaking, ReviewerRecommendation } from '@/services/matchmaking'
import { EditorApi } from '@/services/editorApi'
import { AddReviewerModal } from '@/components/editor/AddReviewerModal'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { ReviewerCandidateList } from '@/components/editor/reviewer-assign-modal/ReviewerCandidateList'
import { AssignActionBar } from '@/components/editor/reviewer-assign-modal/AssignActionBar'
import { useReviewerPolicy } from '@/components/editor/reviewer-assign-modal/useReviewerPolicy'
import { OwnerBindingPanel } from '@/components/editor/reviewer-assign-modal/OwnerBindingPanel'
import { ExistingReviewersPanel } from '@/components/editor/reviewer-assign-modal/ExistingReviewersPanel'
import { AiRecommendationPanel } from '@/components/editor/reviewer-assign-modal/AiRecommendationPanel'
import type { InvitePolicy, ReviewerWithPolicy } from '@/components/editor/reviewer-assign-modal/types'

type AssignOverride = {
  reviewerId: string
  reason: string
}

type AssignOptions = {
  overrides?: AssignOverride[]
}

type AssignFailure = {
  reviewerId: string
  detail: string
}

type AssignResultPayload = {
  ok?: boolean
  assignedReviewerIds?: string[]
  failed?: AssignFailure[]
  keepOpen?: boolean
}

type AssignResult = boolean | void | AssignResultPayload

type StaffProfile = {
  id: string
  email?: string | null
  full_name?: string | null
  roles?: string[]
}

const REVIEWER_PAGE_SIZE_DEFAULT = 20
const REVIEWER_PAGE_SIZE_SEARCH = 40

async function resolveApiErrorMessage(response: Response, fallback: string): Promise<string> {
  const raw = await response.text().catch(() => '')
  if (!raw) return fallback
  try {
    const parsed = JSON.parse(raw || '{}')
    return parsed?.detail || parsed?.message || fallback
  } catch {
    return raw || fallback
  }
}

interface ReviewerAssignModalProps {
  isOpen: boolean
  onClose: () => void
  onAssign: (reviewerIds: string[], options?: AssignOptions) => Promise<AssignResult> | AssignResult
  manuscriptId: string
  currentOwnerId?: string
  currentOwnerLabel?: string
  canBindOwner?: boolean
  viewerRoles?: string[]
}

export default function ReviewerAssignModal({
  isOpen,
  onClose,
  onAssign,
  manuscriptId,
  viewerRoles,
}: ReviewerAssignModalProps) {
  const [reviewers, setReviewers] = useState<ReviewerWithPolicy[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedReviewers, setSelectedReviewers] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingMoreReviewers, setIsLoadingMoreReviewers] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [reviewerPage, setReviewerPage] = useState(1)
  const [hasMoreReviewers, setHasMoreReviewers] = useState(false)
  const [policyMeta, setPolicyMeta] = useState<{ cooldown_days?: number; override_roles?: string[] }>({})
  const [myRoles, setMyRoles] = useState<string[]>([])
  const [overrideReasons, setOverrideReasons] = useState<Record<string, string>>({})
  
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
  const reviewerSearchRequestSeq = useRef(0)
  const normalizedViewerRoles = useMemo(
    () =>
      (viewerRoles || [])
        .map((role) => String(role).trim().toLowerCase())
        .filter(Boolean)
        .sort(),
    [viewerRoles]
  )
  const reviewerSearchScopeKey = useMemo(
    () => (normalizedViewerRoles.length ? normalizedViewerRoles.join(',') : myRoles.slice().sort().join(',')),
    [myRoles, normalizedViewerRoles]
  )

  const fetchOwner = useCallback(async () => {
    if (!manuscriptId) return
    setLoadingOwner(true)
    try {
      // 中文注释：不能使用公开 articles 接口读取 owner（未发表稿件会 404）。
      // 统一走 editor 私有详情接口，确保 Assign Reviewer 弹窗能读到已绑定 owner。
      const payload = await EditorApi.getManuscriptDetail(manuscriptId, { skipCards: true })
      const ms = payload?.data || {}
      const raw = ms?.owner_id || ms?.owner?.id || ms?.kpi_owner_id || ''
      setOwnerId(typeof raw === 'string' ? raw : raw ? String(raw) : '')
    } catch (e) {
      console.error('Failed to load manuscript owner', e)
      // 保持现有值，避免临时请求失败把已选 owner 清空。
    } finally {
      setLoadingOwner(false)
    }
  }, [manuscriptId])

  const fetchInternalStaff = useCallback(async () => {
    try {
      const payload = await EditorApi.listInternalStaff('', undefined, { ttlMs: 60_000 })
      if (!payload?.success) {
        setInternalStaff([])
        return
      }
      setInternalStaff(payload.data || [])
    } catch (e) {
      console.error('Failed to load internal staff', e)
      setInternalStaff([])
    }
  }, [])

  const fetchMyRoles = useCallback(async () => {
    if (normalizedViewerRoles.length) {
      setMyRoles(normalizedViewerRoles)
      return
    }
    try {
      const profile = await authService.getUserProfile()
      const roles = Array.isArray(profile?.roles) ? profile.roles.map((r: any) => String(r).toLowerCase()) : []
      setMyRoles(roles)
    } catch {
      setMyRoles([])
    }
  }, [normalizedViewerRoles])

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
        void fetchExistingReviewers()
      } else {
        const detail = await resolveApiErrorMessage(res, "Failed to remove reviewer")
        toast.error(detail || "Failed to remove reviewer")
      }
    } catch (e) {
      toast.error("Error removing reviewer")
    } finally {
      setRemovingId(null)
    }
  }

  const fetchReviewers = useCallback(async (query: string = '', options?: { append?: boolean; page?: number }) => {
    const requestSeq = reviewerSearchRequestSeq.current + 1
    reviewerSearchRequestSeq.current = requestSeq
    const trimmedQuery = query.trim()
    const nextPage = Math.max(1, Number(options?.page || 1))
    const append = Boolean(options?.append && nextPage > 1)
    const pageSize = trimmedQuery ? REVIEWER_PAGE_SIZE_SEARCH : REVIEWER_PAGE_SIZE_DEFAULT
    if (append) {
      setIsLoadingMoreReviewers(true)
    } else {
      setIsLoading(true)
    }
    try {
      const payload = await EditorApi.searchReviewerLibrary(trimmedQuery, pageSize, manuscriptId, {
        roleScopeKey: reviewerSearchScopeKey,
        page: nextPage,
      })
      if (requestSeq !== reviewerSearchRequestSeq.current) return
      if (!payload?.success) throw new Error(payload?.detail || payload?.message || 'Failed to load reviewer library')
      const incoming = (payload.data || []) as ReviewerWithPolicy[]
      if (append) {
        setReviewers((prev) => {
          const merged = new Map(prev.map((item) => [String(item.id), item]))
          for (const item of incoming) merged.set(String(item.id), item)
          return Array.from(merged.values())
        })
      } else {
        setReviewers(incoming)
      }
      const pagination = payload?.pagination || {}
      const hasMore =
        typeof pagination?.has_more === 'boolean'
          ? Boolean(pagination.has_more)
          : incoming.length >= pageSize
      setReviewerPage(nextPage)
      setHasMoreReviewers(hasMore)
      setPolicyMeta(payload?.policy || {})
    } catch (error) {
      if (requestSeq !== reviewerSearchRequestSeq.current) return
      console.error('Failed to fetch reviewers:', error)
      toast.error('Failed to load reviewers')
    } finally {
      if (requestSeq !== reviewerSearchRequestSeq.current) return
      if (append) {
        setIsLoadingMoreReviewers(false)
      } else {
        setIsLoading(false)
      }
    }
  }, [manuscriptId, reviewerSearchScopeKey])

  useEffect(() => {
    if (!normalizedViewerRoles.length) return
    setMyRoles(normalizedViewerRoles)
  }, [normalizedViewerRoles])

  useEffect(() => {
    if (!isOpen) return
    setSearchTerm('')
    setSelectedReviewers([])
    setOverrideReasons({})
    setAiRecommendations([])
    setAiMessage(null)
    setPendingRemove(null)
    setOwnerSearch('')
    setPolicyMeta({})
    setReviewers([])
    setReviewerPage(1)
    setHasMoreReviewers(false)
    setIsLoadingMoreReviewers(false)
    fetchExistingReviewers()
    fetchOwner()
    fetchInternalStaff()
    fetchMyRoles()
  }, [isOpen, manuscriptId, fetchExistingReviewers, fetchOwner, fetchInternalStaff, fetchMyRoles])

  useEffect(() => {
    if (!isOpen) return
    const timer = window.setTimeout(() => {
      void fetchReviewers(searchTerm.trim(), { page: 1 })
    }, 250)
    return () => window.clearTimeout(timer)
  }, [isOpen, manuscriptId, searchTerm, fetchReviewers])

  const canCurrentUserOverrideCooldown = useMemo(() => {
    const allowRoles = (policyMeta.override_roles || ['admin', 'managing_editor']).map((r) => String(r).toLowerCase())
    if (!allowRoles.length) return false
    return myRoles.some((role) => allowRoles.includes(role))
  }, [myRoles, policyMeta.override_roles])
  const canAddReviewerToLibrary = useMemo(
    () => myRoles.includes('admin') || myRoles.includes('managing_editor'),
    [myRoles]
  )

  const policyByReviewerId = useMemo(() => {
    const index: Record<string, InvitePolicy> = {}
    for (const reviewer of reviewers) {
      if (!reviewer?.id) continue
      index[String(reviewer.id)] = reviewer.invite_policy || {}
    }
    return index
  }, [reviewers])

  const selectedOverrideReviewers = useMemo(
    () =>
      selectedReviewers.filter((rid) => {
        const policy = policyByReviewerId[rid] || {}
        return Boolean(policy.cooldown_active && policy.allow_override)
      }),
    [selectedReviewers, policyByReviewerId]
  )

  const handleAssign = async () => {
    if (selectedReviewers.length > 0) {
      if (!ownerId) {
        toast.message('未绑定 Owner：将由后端自动绑定为当前操作人。')
      }
      if (selectedOverrideReviewers.length > 0) {
        if (!canCurrentUserOverrideCooldown) {
          toast.error('当前账号没有 cooldown override 权限。')
          return
        }
        const missingReason = selectedOverrideReviewers.find((rid) => !String(overrideReasons[rid] || '').trim())
        if (missingReason) {
          toast.error('请填写 cooldown override 原因后再提交。')
          return
        }
      }
      setIsSubmitting(true)
      try {
        const overrides: AssignOverride[] = selectedOverrideReviewers.map((rid) => ({
          reviewerId: rid,
          reason: String(overrideReasons[rid] || '').trim(),
        }))
        const ret = await Promise.resolve(
          (overrides.length > 0 ? onAssign(selectedReviewers, { overrides }) : onAssign(selectedReviewers)) as any
        )
        const payload = ret && typeof ret === 'object' ? (ret as AssignResultPayload) : null
        const assignedReviewerIds = payload
          ? (payload.assignedReviewerIds || []).map((id) => String(id)).filter(Boolean)
          : ret === false
            ? []
            : [...selectedReviewers]
        const assignedSet = new Set(assignedReviewerIds)
        const shouldClose =
          payload
            ? payload.keepOpen === true
              ? false
              : payload.keepOpen === false
                ? true
                : (payload.ok ?? !((payload.failed || []).length > 0))
            : ret !== false

        if (assignedSet.size > 0) {
          await fetchExistingReviewers()
          setSelectedReviewers((prev) => prev.filter((id) => !assignedSet.has(id)))
          setOverrideReasons((prev) =>
            Object.fromEntries(Object.entries(prev).filter(([rid]) => !assignedSet.has(String(rid))))
          )
        }

        if (shouldClose) onClose()
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
    if (isReviewerBlocked(reviewerId)) {
      toast.error('This reviewer is blocked by current invite policy.')
      return
    }
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

  const { isReviewerBlocked, reviewerNeedsOverride, getPolicyBadgeClass } = useReviewerPolicy({
    policyByReviewerId,
    assignedIds,
  })

  const toggleReviewer = (reviewerId: string) => {
    if (assignedIds.includes(reviewerId)) return
    if (isReviewerBlocked(reviewerId)) return

    setSelectedReviewers((prev) => {
      const selected = prev.includes(reviewerId)
      if (selected) {
        return prev.filter((id) => id !== reviewerId)
      }
      return [...prev, reviewerId]
    })
  }

  const orderedReviewers: ReviewerWithPolicy[] = useMemo(() => {
    const assignedSet = new Set(assignedIds)
    const reviewerById = new Map(reviewers.map((r) => [r.id, r]))
    const mergedList: ReviewerWithPolicy[] = [
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
    if (!nextOwnerId || nextOwnerId === '__unassigned') return
    if (nextOwnerId === ownerId) return
    const prev = ownerId
    setOwnerId(nextOwnerId)
    setSavingOwner(true)
    const toastId = toast.loading('Updating owner...')
    try {
      // 统一走 editor bind-owner 接口，避免通用 manuscripts PATCH 的权限/语义漂移。
      const res = await EditorApi.bindOwner(manuscriptId, nextOwnerId)
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || 'Failed to update owner')
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
      <Dialog open={isOpen} onOpenChange={(open) => (!open ? onClose() : undefined)}>
        <DialogContent
          className="max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-xl bg-card p-0 shadow-2xl flex flex-col"
          showCloseButton={false}
          data-testid="reviewer-modal"
        >
          <DialogHeader className="sr-only">
            <DialogTitle>Assign Reviewer</DialogTitle>
            <DialogDescription>
              Search reviewer library, review policy hints, and assign reviewers for this manuscript.
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center justify-between p-6 border-b border-border">
            <div className="flex items-center gap-3">
              <Users className="h-6 w-6 text-primary" />
              <h2 className="text-xl font-bold text-foreground">Assign Reviewer</h2>
            </div>
            <DialogClose asChild>
              <Button
                type="button"
                aria-label="Close reviewer assignment dialog"
                variant="ghost"
                size="icon"
                className="text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
              >
                <X className="h-6 w-6" />
              </Button>
            </DialogClose>
          </div>

          <div className="p-6 overflow-y-auto flex-1">
            <OwnerBindingPanel
              loadingOwner={loadingOwner}
              savingOwner={savingOwner}
              ownerId={ownerId}
              ownerSearch={ownerSearch}
              filteredInternalStaff={filteredInternalStaff}
              currentOwnerLabel={currentOwnerLabel}
              onOwnerSearchChange={setOwnerSearch}
              onOwnerChange={handleOwnerChange}
            />

            <ExistingReviewersPanel
              existingReviewers={existingReviewers}
              onRequestRemove={(reviewer) => setPendingRemove(reviewer)}
            />

            <AiRecommendationPanel
              manuscriptId={manuscriptId}
              aiLoading={aiLoading}
              aiMessage={aiMessage}
              aiRecommendations={aiRecommendations}
              selectedReviewers={selectedReviewers}
              onAnalyze={handleAiAnalyze}
              onInvite={handleInviteFromAi}
              isReviewerBlocked={isReviewerBlocked}
            />

            {/* Manual Search & List */}
            <div className="mb-6 flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <label htmlFor="reviewer-library-search" className="sr-only">
                  Search reviewers by name
                </label>
                <Input
                  id="reviewer-library-search"
                  type="text"
                  placeholder="Search reviewers by name..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary/30"
                  data-testid="reviewer-search"
                />
              </div>
              {canAddReviewerToLibrary ? (
                <Button
                  onClick={() => setIsAddDialogOpen(true)}
                  type="button"
                  variant="secondary"
                  className="flex items-center gap-2 px-3 py-2 text-sm font-medium"
                >
                  <UserPlus className="h-4 w-4" />
                  Add to Library
                </Button>
              ) : null}
            </div>

            <div className="mb-3 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
              Invite policy: cooldown {policyMeta.cooldown_days || 30} days (same journal) is blocked by default, conflict-of-interest is hard block, overdue risk is warning-only.
            </div>

            <ReviewerCandidateList
              isLoading={isLoading}
              orderedReviewers={orderedReviewers}
              assignedIds={assignedIds}
              selectedReviewers={selectedReviewers}
              policyByReviewerId={policyByReviewerId}
              canCurrentUserOverrideCooldown={canCurrentUserOverrideCooldown}
              hasMoreReviewers={hasMoreReviewers}
              isLoadingMoreReviewers={isLoadingMoreReviewers}
              reviewerPage={reviewerPage}
              searchTerm={searchTerm}
              onToggleReviewer={toggleReviewer}
              onLoadMore={(nextPage, query) => void fetchReviewers(query.trim(), { append: true, page: nextPage })}
              isReviewerBlocked={isReviewerBlocked}
              reviewerNeedsOverride={reviewerNeedsOverride}
              getPolicyBadgeClass={getPolicyBadgeClass}
            />

            {selectedOverrideReviewers.length > 0 && (
              <div className="mt-4 rounded-lg border border-secondary-foreground/20 bg-secondary p-3">
                <div className="text-sm font-semibold text-secondary-foreground">Cooldown override required</div>
                <div className="mt-1 text-xs text-secondary-foreground">
                  你已选择 {selectedOverrideReviewers.length} 位命中 cooldown 的审稿人。提交前请填写 override 原因（将写入审计日志）。
                </div>
                <div className="mt-3 space-y-2">
                  {selectedOverrideReviewers.map((rid) => (
                    <div key={`override-${rid}`}>
                      <label className="mb-1 block text-xs font-medium text-foreground" htmlFor={`override-reason-${rid}`}>
                        Reviewer {rid}
                      </label>
                      <Input
                        id={`override-reason-${rid}`}
                        type="text"
                        value={overrideReasons[rid] || ''}
                        onChange={(e) =>
                          setOverrideReasons((prev) => ({
                            ...prev,
                            [rid]: e.target.value,
                          }))
                        }
                        placeholder="Why is cooldown override justified?"
                        className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                        data-testid={`override-reason-${rid}`}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <AssignActionBar
            selectedCount={selectedReviewers.length}
            overrideCount={selectedOverrideReviewers.length}
            isSubmitting={isSubmitting}
            onCancel={onClose}
            onAssign={handleAssign}
          />
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(pendingRemove)} onOpenChange={(open) => (!open ? setPendingRemove(null) : undefined)}>
        <DialogContent className="max-w-md" data-testid="unassign-confirm">
          <DialogHeader>
            <DialogTitle>Remove reviewer?</DialogTitle>
            <DialogDescription>
              This will remove the reviewer from the current manuscript.
            </DialogDescription>
          </DialogHeader>
          {pendingRemove ? (
            <>
              <div className="rounded-lg border border-border bg-muted/40 p-3">
                <div className="text-sm font-medium text-foreground">{pendingRemove.reviewer_name || 'Unknown'}</div>
                <div className="text-xs text-muted-foreground">{pendingRemove.reviewer_email || ''}</div>
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  onClick={() => setPendingRemove(null)}
                  variant="ghost"
                  className="px-4 py-2"
                  data-testid="unassign-cancel"
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  onClick={async () => {
                    if (!pendingRemove) return
                    const assignmentId = String(pendingRemove.id)
                    setPendingRemove(null)
                    await handleUnassign(assignmentId)
                  }}
                  disabled={removingId === String(pendingRemove.id)}
                  variant="destructive"
                  className="px-4 py-2 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-colors"
                  data-testid="unassign-confirm-remove"
                >
                  {removingId === String(pendingRemove.id) ? 'Removing…' : 'Remove'}
                </Button>
              </div>
            </>
          ) : null}
        </DialogContent>
      </Dialog>

      <AddReviewerModal
        open={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
        mode="create"
        onSaved={() => void fetchReviewers(searchTerm.trim(), { page: 1 })}
      />
    </>
  )
}
