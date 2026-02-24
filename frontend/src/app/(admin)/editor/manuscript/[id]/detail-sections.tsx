import { format } from 'date-fns'
import { AlertTriangle, ArrowRight, Calendar, DollarSign, Loader2, User } from 'lucide-react'
import type { RefObject } from 'react'

import { BindingAssistantEditorDropdown } from '@/components/editor/BindingAssistantEditorDropdown'
import { BindingOwnerDropdown } from '@/components/editor/BindingOwnerDropdown'
import { ProductionStatusCard } from '@/components/editor/ProductionStatusCard'
import { ReviewerAssignmentSearch } from '@/components/editor/ReviewerAssignmentSearch'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getStatusColor, getStatusLabel } from '@/lib/statusStyles'

import type { AuthorResponseHistoryItem, ManuscriptDetail } from './helpers'
import type { ReviewerFeedbackItem } from './types'

type DetailTopHeaderProps = {
  journalTitle?: string | null
  manuscriptTitle?: string | null
  status: string
  updatedAt?: string | null
  onBack: () => void
  onBackToList: () => void
}

export function DetailTopHeader({
  journalTitle,
  manuscriptTitle,
  status,
  updatedAt,
  onBack,
  onBackToList,
}: DetailTopHeaderProps) {
  return (
    <header className="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-10 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
      <div className="flex items-center gap-3 overflow-hidden">
        <span className="bg-blue-600 text-white px-2 py-1 rounded text-xs font-bold whitespace-nowrap">
          {journalTitle?.substring(0, 4).toUpperCase() || 'MS'}
        </span>
        <h1 className="font-bold text-slate-900 truncate max-w-xl text-lg" title={manuscriptTitle || ''}>
          {manuscriptTitle || 'Untitled Manuscript'}
        </h1>
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(status)}`}>
          {getStatusLabel(status)}
        </span>
      </div>
      <div className="flex flex-col items-start gap-2 sm:items-end">
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" className="gap-1.5" onClick={onBack}>
            <ArrowRight className="h-4 w-4 rotate-180" />
            返回上一页
          </Button>
          <Button variant="secondary" size="sm" className="gap-1.5" onClick={onBackToList}>
            回到列表
          </Button>
        </div>
        <div className="text-xs text-slate-500 flex items-center gap-2 whitespace-nowrap">
          <Calendar className="h-3 w-3" />
          Updated:{' '}
          <span className="font-mono font-medium text-slate-700">
            {updatedAt ? format(new Date(updatedAt), 'yyyy-MM-dd HH:mm') : '-'}
          </span>
        </div>
      </div>
    </header>
  )
}

type MetadataStaffCardProps = {
  manuscriptId: string
  displayAuthors: string
  affiliation: string
  submittedAt?: string | null
  owner: ManuscriptDetail['owner']
  canBindOwner: boolean
  onOwnerBound: () => void
  currentAeId: string
  currentAeName: string
  canAssignAE: boolean
  onAeAssigned: () => void
  canUpdateInvoiceInfo: boolean
  invoiceStatus?: string | null
  invoiceAmount?: number | string | null
  apcAmount: string
  onOpenInvoice: () => void
}

export function MetadataStaffCard({
  manuscriptId,
  displayAuthors,
  affiliation,
  submittedAt,
  owner,
  canBindOwner,
  onOwnerBound,
  currentAeId,
  currentAeName,
  canAssignAE,
  onAeAssigned,
  canUpdateInvoiceInfo,
  invoiceStatus,
  invoiceAmount,
  apcAmount,
  onOpenInvoice,
}: MetadataStaffCardProps) {
  return (
    <Card className="shadow-sm">
      <CardHeader className="py-4 border-b bg-slate-50/30">
        <CardTitle className="text-sm font-bold uppercase tracking-wide flex items-center gap-2 text-slate-700">
          <User className="h-4 w-4" /> Metadata & Staff
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-6">
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Authors</div>
            <div className="font-medium text-slate-900 text-sm">{displayAuthors}</div>
            <div className="text-xs text-slate-500 mt-1">{affiliation || 'No affiliation'}</div>
          </div>
          <div className="text-right">
            <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Submitted</div>
            <div className="font-medium text-slate-900 text-sm">
              {submittedAt ? format(new Date(submittedAt), 'yyyy-MM-dd') : '-'}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-lg border border-slate-100">
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Owner (Sales)</div>
            <div className="mb-2 min-h-6 text-sm font-medium text-slate-900">
              {owner ? owner.full_name || owner.email : <span className="italic text-slate-400">Unassigned</span>}
            </div>
            <BindingOwnerDropdown
              manuscriptId={manuscriptId}
              currentOwner={owner as any}
              onBound={onOwnerBound}
              disabled={!canBindOwner}
            />
          </div>

          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Assistant Editor</div>
            <div className="mb-2 min-h-6 text-sm font-medium text-slate-900">
              {currentAeId ? currentAeName || currentAeId : <span className="italic text-slate-400">Unassigned</span>}
            </div>
            {canAssignAE ? (
              <BindingAssistantEditorDropdown
                manuscriptId={manuscriptId}
                currentAssistantEditor={
                  currentAeId
                    ? {
                        id: currentAeId,
                        full_name: currentAeName || undefined,
                      }
                    : null
                }
                onAssigned={onAeAssigned}
                disabled={!canAssignAE}
              />
            ) : (
              <div className="flex items-center gap-2 h-9">
                {currentAeId ? (
                  <>
                    <div className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-bold">
                      {(currentAeName || 'E').substring(0, 1).toUpperCase()}
                    </div>
                    <span className="text-sm font-medium truncate">{currentAeName || currentAeId}</span>
                  </>
                ) : (
                  <span className="text-sm text-slate-400 italic">Unassigned</span>
                )}
              </div>
            )}
          </div>

          <div
            className={`p-1 rounded -m-1 transition ${
              canUpdateInvoiceInfo ? 'cursor-pointer hover:bg-slate-100' : 'cursor-not-allowed opacity-70'
            }`}
            onClick={onOpenInvoice}
          >
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
              APC Status <DollarSign className="h-3 w-3" />
            </div>
            <div className="flex items-center gap-2 h-9">
              {invoiceStatus === 'paid' ? (
                <span className="text-sm font-bold text-green-600 flex items-center gap-1">
                  PAID <span className="text-xs font-normal text-slate-500">(${invoiceAmount ?? 0})</span>
                </span>
              ) : (
                <span className="text-sm font-bold text-orange-600 flex items-center gap-1">
                  {invoiceStatus ? String(invoiceStatus).toUpperCase() : 'PENDING'}
                  <span className="text-xs font-normal text-slate-500">(${apcAmount || '0'})</span>
                </span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

type AuthorResubmissionHistoryCardProps = {
  authorResponseHistory: AuthorResponseHistoryItem[]
}

export function AuthorResubmissionHistoryCard({
  authorResponseHistory,
}: AuthorResubmissionHistoryCardProps) {
  return (
    <Card className="shadow-sm">
      <CardHeader className="py-4 border-b bg-slate-50/30">
        <CardTitle className="text-sm font-bold uppercase tracking-wide text-slate-700">
          Author Resubmission History
        </CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        {authorResponseHistory.length > 0 ? (
          <div className="space-y-3">
            {authorResponseHistory.map((item, idx) => (
              <div key={item.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
                  <div>
                    {item.submittedAt
                      ? `Submitted at ${format(new Date(item.submittedAt), 'yyyy-MM-dd HH:mm')}`
                      : 'Submitted time unavailable'}
                    {typeof item.round === 'number' ? ` · Round ${item.round}` : ''}
                  </div>
                  {idx === 0 ? <Badge variant="secondary">Latest</Badge> : null}
                </div>
                <div className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-800">{item.text}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-slate-500">No author resubmission comment yet.</div>
        )}
      </CardContent>
    </Card>
  )
}

type LatestAuthorResubmissionCardProps = {
  latestAuthorResponse: AuthorResponseHistoryItem | null
  historyCount: number
}

export function LatestAuthorResubmissionCard({
  latestAuthorResponse,
  historyCount,
}: LatestAuthorResubmissionCardProps) {
  return (
    <Card className="shadow-sm border-slate-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Latest Author Resubmission Comment</CardTitle>
      </CardHeader>
      <CardContent>
        {latestAuthorResponse ? (
          <div className="space-y-2">
            <div className="text-xs text-slate-500">
              {latestAuthorResponse.submittedAt
                ? `Submitted at ${format(new Date(latestAuthorResponse.submittedAt), 'yyyy-MM-dd HH:mm')}`
                : 'Submitted time unavailable'}
              {typeof latestAuthorResponse.round === 'number' ? ` · Round ${latestAuthorResponse.round}` : ''}
              {historyCount > 0 ? ` · Total ${historyCount}` : ''}
            </div>
            <div className="max-h-44 overflow-auto rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-800 whitespace-pre-wrap">
              {latestAuthorResponse.text}
            </div>
            {historyCount > 1 ? (
              <div className="text-xs text-slate-500">
                Complete timeline is shown in the left card:{' '}
                <span className="font-medium text-slate-700">Author Resubmission History</span>.
              </div>
            ) : null}
          </div>
        ) : (
          <div className="text-sm text-slate-500">No author resubmission comment yet.</div>
        )}
      </CardContent>
    </Card>
  )
}

type ReviewerFeedbackSummaryCardProps = {
  reviewCardRef: RefObject<HTMLDivElement>
  reviewsActivated: boolean
  reviewsLoading: boolean
  reviewsError: string | null
  reviewReports: ReviewerFeedbackItem[]
  onRetry: () => void
}

export function ReviewerFeedbackSummaryCard({
  reviewCardRef,
  reviewsActivated,
  reviewsLoading,
  reviewsError,
  reviewReports,
  onRetry,
}: ReviewerFeedbackSummaryCardProps) {
  return (
    <Card ref={reviewCardRef} className="shadow-sm border-slate-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          Reviewer Feedback Summary
          {!reviewsActivated ? <span className="text-xs font-normal text-slate-500">Deferred</span> : null}
          {reviewsActivated && reviewsLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-500" /> : null}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {!reviewsActivated ? (
          <div className="text-sm text-slate-500">Reviewer feedback will load when this card enters the viewport.</div>
        ) : reviewsLoading ? (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading reviewer feedback...
          </div>
        ) : reviewsError ? (
          <div className="space-y-2">
            <div className="text-sm text-rose-600">{reviewsError}</div>
            <Button size="sm" variant="outline" onClick={onRetry}>
              Retry
            </Button>
          </div>
        ) : reviewReports.length === 0 ? (
          <div className="text-sm text-slate-500">No reviewer feedback submitted yet.</div>
        ) : (
          reviewReports.map((report) => {
            const publicComment = String(report.comments_for_author || report.content || '').trim()
            const confidentialComment = String(report.confidential_comments_to_editor || '').trim()
            return (
              <div key={report.id} className="rounded-md border border-slate-200 bg-slate-50 p-3 space-y-2">
                <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
                  <div className="font-medium text-slate-700">
                    {report.reviewer_name || report.reviewer_email || report.reviewer_id || 'Reviewer'}
                  </div>
                  <div className="flex items-center gap-2">
                    {typeof report.score === 'number' ? <Badge variant="outline">Score {report.score}</Badge> : null}
                    {report.status ? <Badge variant="secondary">{String(report.status)}</Badge> : null}
                  </div>
                </div>
                <div className="text-xs text-slate-500">
                  {report.created_at
                    ? format(new Date(report.created_at), 'yyyy-MM-dd HH:mm')
                    : 'Submitted time unavailable'}
                </div>
                <div className="space-y-1">
                  <div className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Comments for Author</div>
                  <div className="whitespace-pre-wrap text-sm leading-6 text-slate-800">{publicComment || '—'}</div>
                </div>
                {confidentialComment ? (
                  <div className="space-y-1 rounded-md border border-amber-200 bg-amber-50 px-2.5 py-2">
                    <div className="text-[11px] font-semibold text-amber-700 uppercase tracking-wide">
                      Confidential to Editor
                    </div>
                    <div className="whitespace-pre-wrap text-sm leading-6 text-amber-900">{confidentialComment}</div>
                  </div>
                ) : null}
              </div>
            )
          })
        )}
      </CardContent>
    </Card>
  )
}

type EditorialActionsCardProps = {
  manuscriptId: string
  isPostAcceptance: boolean
  canAssignReviewersStage: boolean
  canOpenDecisionWorkspaceStage: boolean
  canManageReviewers: boolean
  viewerRoles: string[]
  canRecordFirstDecision: boolean
  canSubmitFinalDecision: boolean
  canOpenProductionWorkspace: boolean
  statusLower: string
  finalPdfPath?: string | null
  invoice?: ManuscriptDetail['invoice']
  showDirectStatusTransitions: boolean
  canManualStatusTransition: boolean
  nextStatuses: string[]
  transitioning: string | null
  currentAeId: string
  onReviewerChanged: () => void
  onOpenDecisionWorkspace: () => void
  onOpenProductionWorkspace: () => void
  onProductionStatusChange: (next: string) => void
  onReload: () => void
  onOpenTransitionDialog: (nextStatus: string) => void
  getTransitionActionLabel: (nextStatus: string) => string
}

export function EditorialActionsCard({
  manuscriptId,
  isPostAcceptance,
  canAssignReviewersStage,
  canOpenDecisionWorkspaceStage,
  canManageReviewers,
  viewerRoles,
  canRecordFirstDecision,
  canSubmitFinalDecision,
  canOpenProductionWorkspace,
  statusLower,
  finalPdfPath,
  invoice,
  showDirectStatusTransitions,
  canManualStatusTransition,
  nextStatuses,
  transitioning,
  currentAeId,
  onReviewerChanged,
  onOpenDecisionWorkspace,
  onOpenProductionWorkspace,
  onProductionStatusChange,
  onReload,
  onOpenTransitionDialog,
  getTransitionActionLabel,
}: EditorialActionsCardProps) {
  return (
    <Card className="border-t-4 border-t-purple-500 shadow-sm">
      <CardHeader>
        <CardTitle className="text-lg">Editorial Actions</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!isPostAcceptance && canAssignReviewersStage && (
          <div className="pt-2 pb-4 border-b border-slate-100">
            <div className="text-xs font-semibold text-slate-500 mb-2">ASSIGN REVIEWERS</div>
            <ReviewerAssignmentSearch
              manuscriptId={manuscriptId}
              onChanged={onReviewerChanged}
              disabled={!canManageReviewers}
              viewerRoles={viewerRoles}
            />
          </div>
        )}
        {!isPostAcceptance && !canAssignReviewersStage && (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
            当前阶段不开放审稿人分配。请先按流程推进到 `under_review / resubmitted`。
          </div>
        )}

        {!isPostAcceptance && canOpenDecisionWorkspaceStage && (
          <Button
            className="w-full justify-between"
            variant="secondary"
            disabled={!(canRecordFirstDecision || canSubmitFinalDecision)}
            onClick={onOpenDecisionWorkspace}
          >
            Open Decision Workspace
            <ArrowRight className="h-4 w-4" />
          </Button>
        )}
        {!isPostAcceptance && !canOpenDecisionWorkspaceStage && (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
            Decision Workspace 仅在 `under_review / resubmitted / decision / decision_done` 阶段开放。
          </div>
        )}

        {isPostAcceptance ? (
          <div className="space-y-3">
            {canOpenProductionWorkspace ? (
              <>
                <Button className="w-full justify-between" variant="secondary" onClick={onOpenProductionWorkspace}>
                  Open Production Workspace
                  <ArrowRight className="h-4 w-4" />
                </Button>
                <ProductionStatusCard
                  manuscriptId={manuscriptId}
                  status={statusLower || 'approved'}
                  finalPdfPath={finalPdfPath}
                  invoice={invoice}
                  onStatusChange={onProductionStatusChange}
                  onReload={onReload}
                />
              </>
            ) : (
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                稿件进入录用后由 Managing Editor / Production Editor 继续处理。
              </div>
            )}
          </div>
        ) : showDirectStatusTransitions ? (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-slate-500 mb-2">CHANGE STATUS</div>
            {!canManualStatusTransition ? (
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                当前账号无手动状态流转权限（仅 Managing Editor/Admin 可用）。
              </div>
            ) : nextStatuses.length === 0 ? (
              <div className="text-sm text-slate-400 italic">No next status available.</div>
            ) : (
              nextStatuses.map((nextStatus) => {
                const next = String(nextStatus || '').toLowerCase().trim()
                const requireAeFirst = statusLower === 'pre_check' && next === 'under_review' && !currentAeId
                return (
                  <Button
                    key={nextStatus}
                    className="w-full justify-between"
                    variant="outline"
                    disabled={transitioning === nextStatus || requireAeFirst}
                    onClick={() => onOpenTransitionDialog(nextStatus)}
                  >
                    <span>
                      {requireAeFirst
                        ? 'Move to Under Review (Assign AE first)'
                        : getTransitionActionLabel(nextStatus)}
                    </span>
                    {transitioning === nextStatus ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <ArrowRight className="h-4 w-4 opacity-50" />
                    )}
                  </Button>
                )
              })
            )}
          </div>
        ) : (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
            当前状态为流程终态，已关闭手动状态流转。
          </div>
        )}
      </CardContent>
    </Card>
  )
}

type NextActionCardProps = {
  nextAction: {
    phase: string
    title: string
    description: string
    blockers: string[]
  }
}

export function NextActionCard({ nextAction }: NextActionCardProps) {
  return (
    <Card className="shadow-sm border-slate-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center justify-between">
          <span>Next Action</span>
          <Badge variant="secondary">{nextAction.phase}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-sm font-semibold text-slate-900">{nextAction.title}</div>
        <div className="text-sm text-slate-600">{nextAction.description}</div>
        {nextAction.blockers.length > 0 && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 space-y-1">
            <div className="text-xs font-semibold text-rose-700 flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5" />
              Blocking Conditions
            </div>
            {nextAction.blockers.map((item) => (
              <div key={item} className="text-xs text-rose-700">
                - {item}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

type TaskSlaSummaryCardProps = {
  cardsSectionRef: RefObject<HTMLDivElement>
  cardsActivated: boolean
  cardsLoading: boolean
  cardsError: string | null
  taskSummary: ManuscriptDetail['task_summary']
  onRetry: () => void
}

export function TaskSlaSummaryCard({
  cardsSectionRef,
  cardsActivated,
  cardsLoading,
  cardsError,
  taskSummary,
  onRetry,
}: TaskSlaSummaryCardProps) {
  return (
    <Card ref={cardsSectionRef} className="shadow-sm">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          Task SLA Summary
          {!cardsActivated ? <span className="text-xs font-normal text-slate-500">Deferred</span> : null}
          {cardsLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-500" /> : null}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {cardsError ? (
          <div className="space-y-2">
            <div className="text-sm text-rose-600">{cardsError}</div>
            <Button size="sm" variant="outline" onClick={onRetry} data-testid="cards-context-retry">
              Retry
            </Button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <span className="text-slate-600">Open Tasks</span>
              <span className="font-medium text-slate-900">{taskSummary?.open_tasks_count ?? 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-600">Overdue Tasks</span>
              <span className={`font-medium ${taskSummary?.is_overdue ? 'text-rose-700' : 'text-slate-900'}`}>
                {taskSummary?.overdue_tasks_count ?? 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-600">Nearest Due</span>
              <span className="font-medium text-slate-900">
                {taskSummary?.nearest_due_at ? format(new Date(taskSummary.nearest_due_at), 'yyyy-MM-dd HH:mm') : '—'}
              </span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

type PrecheckRoleQueueCardProps = {
  cardsActivated: boolean
  cardsLoading: boolean
  cardsError: string | null
  isPrecheckActive: boolean
  roleQueue: ManuscriptDetail['role_queue']
  roleQueueAssigneeText: string
  statusLower: string
  onRetry: () => void
}

export function PrecheckRoleQueueCard({
  cardsActivated,
  cardsLoading,
  cardsError,
  isPrecheckActive,
  roleQueue,
  roleQueueAssigneeText,
  statusLower,
  onRetry,
}: PrecheckRoleQueueCardProps) {
  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          Pre-check Role Queue
          {!cardsActivated ? <span className="text-xs font-normal text-slate-500">Deferred</span> : null}
          {cardsLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-500" /> : null}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {cardsError ? (
          <div className="space-y-2">
            <div className="text-sm text-rose-600">{cardsError}</div>
            <Button size="sm" variant="outline" onClick={onRetry} data-testid="precheck-cards-context-retry">
              Retry
            </Button>
          </div>
        ) : isPrecheckActive ? (
          <>
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-medium text-slate-700">Current Role:</span>{' '}
                <span className="text-slate-900">{(roleQueue?.current_role || '—').replaceAll('_', ' ')}</span>
              </div>
              <div>
                <span className="font-medium text-slate-700">Current Assignee:</span>{' '}
                <span className="text-slate-900">{roleQueueAssigneeText}</span>
              </div>
              <div>
                <span className="font-medium text-slate-700">Assigned At:</span>{' '}
                <span className="text-slate-900">
                  {roleQueue?.assigned_at ? format(new Date(roleQueue.assigned_at), 'yyyy-MM-dd HH:mm') : '—'}
                </span>
              </div>
              <div>
                <span className="font-medium text-slate-700">Technical Completed:</span>{' '}
                <span className="text-slate-900">
                  {roleQueue?.technical_completed_at
                    ? format(new Date(roleQueue.technical_completed_at), 'yyyy-MM-dd HH:mm')
                    : '—'}
                </span>
              </div>
              <div>
                <span className="font-medium text-slate-700">Academic Completed:</span>{' '}
                <span className="text-slate-900">
                  {roleQueue?.academic_completed_at
                    ? format(new Date(roleQueue.academic_completed_at), 'yyyy-MM-dd HH:mm')
                    : '—'}
                </span>
              </div>
            </div>
            <div className="mt-3 text-xs text-slate-500">Detailed role actions are merged into the Activity Timeline below.</div>
          </>
        ) : (
          <div className="space-y-2 text-sm">
            <div className="font-medium text-slate-900">Pre-check completed</div>
            <div className="text-slate-700">
              Last assignee: <span className="font-medium text-slate-900">{roleQueueAssigneeText}</span>
            </div>
            <div className="text-slate-700">
              Technical completed:{' '}
              <span className="font-medium text-slate-900">
                {roleQueue?.technical_completed_at ? format(new Date(roleQueue.technical_completed_at), 'yyyy-MM-dd HH:mm') : '—'}
              </span>
            </div>
            <div className="text-slate-700">
              Academic completed:{' '}
              <span className="font-medium text-slate-900">
                {roleQueue?.academic_completed_at ? format(new Date(roleQueue.academic_completed_at), 'yyyy-MM-dd HH:mm') : '—'}
              </span>
            </div>
            <div className="pt-1 text-xs text-slate-500">
              Current manuscript status is <span className="font-medium">{statusLower || '—'}</span>. Full pre-check actions are in Activity Timeline.
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
