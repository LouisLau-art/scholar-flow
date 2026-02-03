'use client'

import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, AlertCircle, FileText, Loader2, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { authService } from '@/services/auth'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import VersionHistory from '@/components/VersionHistory'

interface ReviewFeedback {
  id: string
  reviewer_id: string
  reviewer_name?: string | null
  reviewer_email?: string | null
  status?: string | null
  score?: number | string | null
  comments_for_author?: string | null
  confidential_comments_to_editor?: string | null
  created_at?: string | null
}

interface DecisionPanelProps {
  manuscriptId?: string
  onSubmitted?: () => void
}

export default function DecisionPanel({
  manuscriptId,
  onSubmitted
}: DecisionPanelProps) {
  const [decision, setDecision] = useState<'accept' | 'reject' | 'revision' | null>(null)
  const [revisionType, setRevisionType] = useState<'major' | 'minor' | null>(null)
  const [comment, setComment] = useState('')
  const [apcAmount, setApcAmount] = useState<number>(1500)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitSuccess, setSubmitSuccess] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')

  const [reviews, setReviews] = useState<ReviewFeedback[]>([])
  const [reviewsLoading, setReviewsLoading] = useState(false)
  const [reviewsLoaded, setReviewsLoaded] = useState(false)
  const [reviewsError, setReviewsError] = useState<string | null>(null)

  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfError, setPdfError] = useState<string | null>(null)

  const [roles, setRoles] = useState<string[]>([])
  const [lastRevisionType, setLastRevisionType] = useState<'major' | 'minor' | null>(null)

  const getScoreNumber = (value: unknown): number | null => {
    if (typeof value === 'number') return Number.isFinite(value) ? value : null
    if (typeof value === 'string') {
      const n = Number(value)
      return Number.isFinite(n) ? n : null
    }
    return null
  }

  const isReviewCompleted = (r: ReviewFeedback): boolean => {
    const status = String(r.status || '').toLowerCase()
    if (status === 'completed' || status === 'submitted' || status === 'done') return true
    if (getScoreNumber(r.score) !== null) return true
    if ((r.comments_for_author || '').trim()) return true
    if ((r.confidential_comments_to_editor || '').trim()) return true
    return false
  }

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (!manuscriptId) return
      setReviewsLoading(true)
      setReviewsLoaded(false)
      setReviewsError(null)
      try {
        const token = await authService.getAccessToken()
        if (!token) throw new Error('Please sign in again.')

        const res = await fetch(`/api/v1/manuscripts/${encodeURIComponent(manuscriptId)}/reviews`, {
          headers: { Authorization: `Bearer ${token}` },
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

        const data = (payload?.data || []) as ReviewFeedback[]
        if (cancelled) return
        setReviews(Array.isArray(data) ? data : [])
        setReviewsLoaded(true)
      } catch (e: any) {
        console.error('[DecisionPanel] load reviews failed:', e)
        if (cancelled) return
        setReviews([])
        setReviewsLoaded(true)
        setReviewsError(e?.message || 'Failed to load reviews')
      } finally {
        if (!cancelled) setReviewsLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [manuscriptId])

  useEffect(() => {
    let cancelled = false

    async function loadPdf() {
      if (!manuscriptId) return
      setPdfLoading(true)
      setPdfError(null)
      setPdfUrl(null)
      try {
        const token = await authService.getAccessToken()
        if (!token) throw new Error('Please sign in again.')
        const res = await fetch(`/api/v1/manuscripts/${encodeURIComponent(manuscriptId)}/pdf-signed`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const json = await res.json().catch(() => null)
        const signed = json?.data?.signed_url
        if (!res.ok || !json?.success || !signed) {
          const msg = json?.detail || json?.message || `HTTP ${res.status}`
          throw new Error(msg)
        }
        if (cancelled) return
        setPdfUrl(String(signed))
      } catch (e: any) {
        if (cancelled) return
        setPdfError(e?.message || 'Failed to load PDF preview')
        setPdfUrl(null)
      } finally {
        if (!cancelled) setPdfLoading(false)
      }
    }

    loadPdf()
    return () => {
      cancelled = true
    }
  }, [manuscriptId])

  useEffect(() => {
    let cancelled = false

    async function loadMeta() {
      if (!manuscriptId) return
      try {
        const token = await authService.getAccessToken()
        if (!token) return

        // 1) 当前用户角色（用于 UI 权限控制）
        const pRes = await fetch('/api/v1/user/profile', {
          headers: { Authorization: `Bearer ${token}` },
        })
        const pRaw = await pRes.text().catch(() => '')
        let pJson: any = null
        try {
          pJson = pRaw ? JSON.parse(pRaw) : null
        } catch {
          pJson = null
        }
        const nextRoles = (pJson?.data?.roles || pJson?.roles || []) as string[]
        if (!cancelled) setRoles(Array.isArray(nextRoles) ? nextRoles : [])

        // 2) 最新修订类型（用于“上轮小修后禁用大修”）
        const hRes = await fetch(`/api/v1/manuscripts/${encodeURIComponent(manuscriptId)}/versions`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const hRaw = await hRes.text().catch(() => '')
        let hJson: any = null
        try {
          hJson = hRaw ? JSON.parse(hRaw) : null
        } catch {
          hJson = null
        }
        const revisions = (hJson?.data?.revisions || []) as any[]
        const latest = Array.isArray(revisions)
          ? revisions.reduce((acc: any, cur: any) => {
              if (!acc) return cur
              if ((cur?.round_number ?? 0) > (acc?.round_number ?? 0)) return cur
              return acc
            }, null as any)
          : null
        const t = String(latest?.decision_type || '').toLowerCase()
        if (!cancelled) setLastRevisionType(t === 'minor' || t === 'major' ? (t as any) : null)
      } catch (e) {
        // 不阻塞主流程：失败就不做 UI 限制
        console.warn('[DecisionPanel] load meta failed (ignored):', e)
        if (!cancelled) {
          setRoles([])
          setLastRevisionType(null)
        }
      }
    }

    loadMeta()
    return () => {
      cancelled = true
    }
  }, [manuscriptId])

  const completedCount = useMemo(() => reviews.filter(isReviewCompleted).length, [reviews])
  const canDecide = reviewsLoaded && !reviewsLoading && !reviewsError && completedCount > 0
  const majorLocked = lastRevisionType === 'minor' && !(roles || []).includes('admin')

  useEffect(() => {
    if (majorLocked && revisionType === 'major') {
      setRevisionType('minor')
    }
  }, [majorLocked, revisionType])

  const averageOverallScore = useMemo(() => {
    const scores = reviews
      .map((r) => getScoreNumber(r.score))
      .filter((s): s is number => typeof s === 'number' && Number.isFinite(s))
    if (!scores.length) return 0
    return scores.reduce((sum, s) => sum + s, 0) / scores.length
  }, [reviews])

  const handleSubmit = async () => {
    if (!decision || !manuscriptId) return
    // 中文注释:
    // - accept/reject：避免“盲做决定”，至少需要 1 份已完成审稿意见
    // - revision：允许在 resubmitted 等阶段直接退修（不强制有新审稿意见）
    if (decision !== 'revision' && !canDecide) {
      toast.error('请先加载并查看审稿意见后再做决定。')
      return
    }

    if (decision === 'revision') {
      if (!revisionType) {
        toast.error('请选择修订类型（大修 / 小修）。')
        return
      }
      if (!comment || comment.trim().length < 10) {
        toast.error('请填写更详细的退修说明（至少 10 个字符）。')
        return
      }
    }

    if (decision === 'accept') {
      if (!Number.isFinite(apcAmount) || apcAmount < 0) {
        toast.error('请填写正确的 APC 金额（>= 0）。')
        return
      }
    }

    setIsSubmitting(true)
    try {
      const token = await authService.getAccessToken()
      if (!token) {
        toast.error('Please sign in again.')
        setIsSubmitting(false)
        return
      }

      let endpoint = '/api/v1/editor/decision'
      let body: any = {
        manuscript_id: manuscriptId,
        decision,
        comment
      }

      if (decision === 'accept') {
        body.apc_amount = apcAmount
      }

      if (decision === 'revision') {
        endpoint = '/api/v1/editor/revisions'
        body = {
          manuscript_id: manuscriptId,
          decision_type: revisionType,
          comment
        }
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body)
      })

      const raw = await response.text().catch(() => '')
      let data: any = null
      try {
        data = raw ? JSON.parse(raw) : null
      } catch {
        data = null
      }

      if (response.ok && data.success) {
        setSubmitSuccess(true)
        if (decision === 'revision') {
          setSuccessMessage(`已发起退修（${revisionType === 'major' ? '大修' : '小修'}）。`)
        } else if (decision === 'accept') {
          setSuccessMessage('稿件已录用（进入财务门禁阶段）。')
        } else {
          setSuccessMessage('稿件已拒稿。')
        }
        toast.success('操作已保存。')
        if (onSubmitted) onSubmitted()
      } else {
        const serverMsg =
          data?.detail ||
          data?.message ||
          (typeof raw === 'string' && raw.trim() ? raw.trim() : '') ||
          `HTTP ${response.status}`

        // 更友好的用户提示（保留 console error 方便排查）
        if (typeof serverMsg === 'string' && serverMsg.includes("Cannot request revision for manuscript")) {
          throw new Error('当前稿件状态暂不支持退修操作，请刷新页面后重试。')
        }
        throw new Error(serverMsg || '提交失败')
      }
    } catch (error: any) {
      console.error('Failed to submit decision:', error)
      toast.error(error.message || '提交失败，请稍后重试。')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (submitSuccess) {
    return (
      <Card className="text-center">
        <CardContent className="p-8">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
            <CheckCircle2 className="h-8 w-8 text-emerald-600" />
          </div>
          <h3 className="mb-2 text-xl font-semibold text-foreground">成功</h3>
          <p className="mb-6 text-sm text-muted-foreground">
            {successMessage}
          </p>
          <div className="rounded-lg bg-muted p-4">
            <div className="mb-2 flex items-center justify-center gap-2">
              <div
                className={`h-2 w-2 rounded-full ${
                  decision === "accept" ? "bg-emerald-500" : 
                  decision === "revision" ? "bg-amber-500" : "bg-rose-500"
                }`}
              />
              <span className="text-sm font-medium text-foreground capitalize">
                Decision: {decision === 'revision' ? `Revision (${revisionType})` : decision}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center gap-3">
          <AlertCircle className="h-6 w-6 text-primary" />
          <CardTitle>Final Decision</CardTitle>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Manuscript Preview + Version/Revision Details */}
        {manuscriptId && (
          <div className="space-y-4">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-slate-500" />
                  <h4 className="text-sm font-medium text-foreground">Latest Manuscript PDF</h4>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={!pdfUrl}
                  onClick={() => {
                    if (pdfUrl) window.open(pdfUrl, '_blank')
                  }}
                >
                  Open in New Tab
                </Button>
              </div>

              {pdfError ? (
                <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                  PDF preview unavailable: {pdfError}
                </div>
              ) : null}

              <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 overflow-hidden min-h-[640px] h-[calc(100dvh-360px)]">
                {pdfLoading ? (
                  <div className="h-full flex items-center justify-center text-slate-500 font-medium">
                    <Loader2 className="h-4 w-4 animate-spin mr-2" /> Loading preview…
                  </div>
                ) : pdfUrl ? (
                  <iframe src={pdfUrl} className="w-full h-full border-0" title="PDF Preview" />
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500 font-medium">
                    No PDF available for preview.
                  </div>
                )}
              </div>
              <p className="mt-2 text-xs text-slate-400">Preview links expire in 10 minutes.</p>
            </div>

            <div>
              <h4 className="text-sm font-medium text-foreground mb-2">Revision & Version History</h4>
              <VersionHistory manuscriptId={manuscriptId} />
            </div>
          </div>
        )}

        {/* Review Summary (must show before decision) */}
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between gap-3">
            <h4 className="text-sm font-medium text-foreground">Review Summary</h4>
            {reviewsLoading ? (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <Loader2 className="h-3 w-3 animate-spin" /> Loading…
              </div>
            ) : null}
          </div>

          {reviewsError ? (
            <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              Failed to load reviews: {reviewsError}
            </div>
          ) : reviewsLoaded && reviews.length === 0 ? (
            <div className="mt-3 text-sm text-slate-600">
              No reviews found for this manuscript yet.
            </div>
          ) : reviewsLoaded && completedCount === 0 ? (
            <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Reviews are assigned, but none has been submitted yet. Please wait for at least one completed review before making a decision.
            </div>
          ) : (
            <div className="mt-3 space-y-3">
              {reviews.map((r, idx) => {
                const displayName =
                  r.reviewer_name || r.reviewer_email || r.reviewer_id || `Reviewer ${idx + 1}`
                const scoreNum = getScoreNumber(r.score)
                const completed = isReviewCompleted(r)
                const scoreLabel = scoreNum !== null ? String(scoreNum) : completed ? 'N/A' : 'Pending'
                const confidential = r.confidential_comments_to_editor || ''
                return (
                  <div
                    key={r.id || `${r.reviewer_id}-${idx}`}
                    className="rounded-lg bg-slate-50 border border-slate-200 p-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="text-sm font-semibold text-slate-900">{displayName}</div>
                      <div className="text-xs text-slate-600">
                        Score: <span className="font-semibold text-slate-900">{scoreLabel}</span>
                      </div>
                    </div>
                    <div className="mt-2">
                      <div className="text-xs font-semibold text-slate-700">
                        Confidential Comments to the Editor
                      </div>
                      <div className="mt-1 whitespace-pre-wrap text-sm text-slate-800">
                        {confidential.trim() ? confidential : completed ? '(none)' : '(not submitted yet)'}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="rounded-lg bg-muted p-4">
          <h4 className="mb-2 text-sm font-medium text-foreground">Reviewer Score Summary</h4>
          {reviews.length > 0 ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Average Overall Score:</span>
                <span className="text-lg font-semibold text-primary">
                  {completedCount > 0 ? averageOverallScore.toFixed(1) : 'N/A'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Number of Reviews:</span>
                <span className="text-lg font-semibold text-primary">
                  {reviews.length} (submitted {completedCount})
                </span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No reviewer scores available</p>
          )}
        </div>

        {/* Decision Options */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-foreground">Select Decision</h4>
          {!canDecide && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              录用/拒稿需要至少 1 份已提交审稿意见；如需退修可直接选择 “Request Revision”。
            </div>
          )}
          <RadioGroup
            value={decision ?? ""}
            onValueChange={(value) => {
              // 允许在没有新审稿意见时直接退修（revision）；但 accept/reject 仍要求至少 1 份已提交意见
              if (!canDecide && value !== 'revision') {
                toast.error('当前暂无可用审稿意见，暂不支持直接录用/拒稿；如需退修请选择“Request Revision”。')
                return
              }
              setDecision(value as any)
            }}
            className="grid grid-cols-1 gap-4"
            disabled={isSubmitting}
          >
            {/* Accept */}
            <Label
              htmlFor="decision-accept"
              className={!canDecide ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}
            >
              <div
                className={`flex items-start gap-3 rounded-lg border p-4 transition-colors ${
                  decision === "accept"
                    ? "border-emerald-500 bg-emerald-50 text-emerald-700"
                    : "border-border bg-background text-foreground hover:bg-accent"
                }`}
              >
                <RadioGroupItem id="decision-accept" value="accept" className="mt-1" />
                <div className="space-y-3 w-full">
                  <div className="text-sm font-semibold text-foreground">Accept for Publication</div>
                  <div className="text-xs text-muted-foreground">
                    The manuscript meets all standards.
                  </div>

                  {decision === 'accept' && (
                    <div className="mt-2 rounded-lg bg-white/60 p-3 border border-emerald-100">
                      <Label htmlFor="apc-amount" className="text-xs font-semibold text-slate-700">
                        Confirm APC Amount (USD)
                      </Label>
                      <Input
                        id="apc-amount"
                        type="number"
                        min={0}
                        step={50}
                        value={String(apcAmount)}
                        onChange={(e) => setApcAmount(Number(e.target.value))}
                        className="mt-2"
                      />
                      <p className="mt-2 text-xs text-muted-foreground">
                        Publishing will be blocked until payment is received (Financial Gate).
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </Label>

            {/* Request Revision */}
            <Label htmlFor="decision-revision" className="cursor-pointer">
              <div
                className={`flex items-start gap-3 rounded-lg border p-4 transition-colors ${
                  decision === "revision"
                    ? "border-amber-500 bg-amber-50 text-amber-900"
                    : "border-border bg-background text-foreground hover:bg-accent"
                }`}
              >
                <RadioGroupItem id="decision-revision" value="revision" className="mt-1" />
                <div className="space-y-3 w-full">
                  <div className="space-y-1">
                    <div className="text-sm font-semibold text-foreground flex items-center gap-2">
                      <RefreshCw className="h-4 w-4" />
                      Request Revision
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Require changes from the author before acceptance.
                    </div>
                  </div>
                  
                  {/* Nested Options for Revision Type */}
                  {decision === 'revision' && (
                    <div className="mt-3 pl-2 border-l-2 border-amber-200">
                      <RadioGroup
                        value={revisionType ?? ""}
                        onValueChange={(v) => setRevisionType(v as 'major' | 'minor')}
                        className="flex gap-4"
                      >
                         <div className="flex items-center space-x-2">
                           <RadioGroupItem value="minor" id="r-minor" />
                           <Label htmlFor="r-minor">Minor Revision</Label>
                         </div>
                         <div className="flex items-center space-x-2">
                           <RadioGroupItem value="major" id="r-major" disabled={majorLocked} />
                           <Label
                             htmlFor="r-major"
                             className={majorLocked ? 'opacity-60 cursor-not-allowed' : ''}
                           >
                             Major Revision
                           </Label>
                         </div>
                      </RadioGroup>
                      {majorLocked && (
                        <div className="mt-2 text-xs text-amber-800">
                          上一轮为小修：为避免流程反复，编辑无权升级为大修；如确需大修请用 Admin 账号操作。
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </Label>

            {/* Reject */}
            <Label
              htmlFor="decision-reject"
              className={!canDecide ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}
            >
              <div
                className={`flex items-start gap-3 rounded-lg border p-4 transition-colors ${
                  decision === "reject"
                    ? "border-rose-500 bg-rose-50 text-rose-700"
                    : "border-border bg-background text-foreground hover:bg-accent"
                }`}
              >
                <RadioGroupItem id="decision-reject" value="reject" className="mt-1" />
                <div className="space-y-1">
                  <div className="text-sm font-semibold text-foreground">Reject Manuscript</div>
                  <div className="text-xs text-muted-foreground">
                    The manuscript does not meet quality standards.
                  </div>
                </div>
              </div>
            </Label>
          </RadioGroup>
        </div>

        {/* Comment */}
        {decision && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-foreground">
              {decision === 'revision' ? 'Revision Instructions (Required)' : 'Decision Comment (Optional)'}
            </h4>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={decision === 'revision' ? "Please list the specific changes required..." : "Enter any additional comments..."}
              rows={6}
              className="w-full rounded-md border border-input bg-background p-3 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
            {decision === 'revision' && (
              <p className="text-xs text-muted-foreground text-right">
                {comment.trim().length}/10 characters minimum
              </p>
            )}
          </div>
        )}

        {/* Submit Button */}
        <Button
          onClick={handleSubmit}
          disabled={
            isSubmitting ||
            !decision ||
            (decision !== 'revision' && !canDecide) ||
            (decision === 'revision' && (!revisionType || comment.trim().length < 10))
          }
          className="w-full"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Submitting Decision...
            </>
          ) : (
            "Submit Decision"
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
