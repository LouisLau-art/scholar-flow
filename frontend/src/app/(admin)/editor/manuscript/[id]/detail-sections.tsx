import { AlertTriangle, ArrowRight, Calendar, DollarSign, History, Loader2, Mail, User } from 'lucide-react'
import type { RefObject } from 'react'

import { BindingAssistantEditorDropdown } from '@/components/editor/BindingAssistantEditorDropdown'
import { BindingOwnerDropdown } from '@/components/editor/BindingOwnerDropdown'
import { ProductionStatusCard } from '@/components/editor/ProductionStatusCard'
import { ReviewerAssignmentSearch } from '@/components/editor/ReviewerAssignmentSearch'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatDateLocal, formatDateTimeLocal } from '@/lib/date-display'
import { getStatusColor, getStatusLabel } from '@/lib/statusStyles'
import type { ReviewEmailTemplateOption } from '@/types/email-template'

import {
  formatReviewerAuditVia,
  formatReviewerDeclineReason,
  formatReviewerEmailEventLabel,
  resolveReviewerInviteSummaryState,
  type AuthorResponseHistoryItem,
  type ManuscriptDetail,
} from './helpers'
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
    <header className="bg-card border-b border-border px-6 py-4 sticky top-0 z-10 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
      <div className="flex items-center gap-3 overflow-hidden">
        <span className="bg-primary text-white px-2 py-1 rounded text-xs font-bold whitespace-nowrap">
          {journalTitle?.substring(0, 4).toUpperCase() || 'MS'}
        </span>
        <h1 className="font-bold text-foreground truncate max-w-xl text-lg" title={manuscriptTitle || ''}>
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
        <div className="text-xs text-muted-foreground flex items-center gap-2 whitespace-nowrap">
          <Calendar className="h-3 w-3" />
          Updated:{' '}
          <span className="font-mono font-medium text-foreground">
            {updatedAt ? formatDateTimeLocal(updatedAt) : '-'}
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
      <CardHeader className="py-4 border-b bg-muted/30">
        <CardTitle className="text-sm font-bold uppercase tracking-wide flex items-center gap-2 text-foreground">
          <User className="h-4 w-4" /> Metadata & Staff
        </CardTitle>
      </CardHeader>
      <CardContent className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-6">
          <div>
            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Authors</div>
            <div className="font-medium text-foreground text-sm">{displayAuthors}</div>
            <div className="text-xs text-muted-foreground mt-1">{affiliation || 'No affiliation'}</div>
          </div>
          <div className="text-right">
            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Submitted</div>
            <div className="font-medium text-foreground text-sm">
              {submittedAt ? formatDateLocal(submittedAt) : '-'}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-muted/40 p-4 rounded-lg border border-border/60">
          <div>
            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Owner (Sales)</div>
            <div className="mb-2 min-h-6 text-sm font-medium text-foreground">
              {owner ? owner.full_name || owner.email : <span className="italic text-muted-foreground">Unassigned</span>}
            </div>
            <BindingOwnerDropdown
              manuscriptId={manuscriptId}
              currentOwner={owner as any}
              onBound={onOwnerBound}
              disabled={!canBindOwner}
            />
          </div>

          <div>
            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Assistant Editor</div>
            <div className="mb-2 min-h-6 text-sm font-medium text-foreground">
              {currentAeId ? currentAeName || currentAeId : <span className="italic text-muted-foreground">Unassigned</span>}
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
                    <div className="w-6 h-6 bg-primary/10 text-primary rounded-full flex items-center justify-center text-xs font-bold">
                      {(currentAeName || 'E').substring(0, 1).toUpperCase()}
                    </div>
                    <span className="text-sm font-medium truncate">{currentAeName || currentAeId}</span>
                  </>
                ) : (
                  <span className="text-sm text-muted-foreground italic">Unassigned</span>
                )}
              </div>
            )}
          </div>

          <div
            className={`p-1 rounded -m-1 transition ${
              canUpdateInvoiceInfo ? 'cursor-pointer hover:bg-muted' : 'cursor-not-allowed opacity-70'
            }`}
            onClick={onOpenInvoice}
          >
            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1 flex items-center gap-1">
              APC Status <DollarSign className="h-3 w-3" />
            </div>
            <div className="flex items-center gap-2 h-9">
              {invoiceStatus === 'paid' ? (
                <span className="text-sm font-bold text-primary flex items-center gap-1">
                  PAID <span className="text-xs font-normal text-muted-foreground">(${invoiceAmount ?? 0})</span>
                </span>
              ) : (
                <span className="text-sm font-bold text-secondary-foreground flex items-center gap-1">
                  {invoiceStatus ? String(invoiceStatus).toUpperCase() : 'PENDING'}
                  <span className="text-xs font-normal text-muted-foreground">(${apcAmount || '0'})</span>
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
      <CardHeader className="py-4 border-b bg-muted/30">
        <CardTitle className="text-sm font-bold uppercase tracking-wide text-foreground">
          Author Resubmission History
        </CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        {authorResponseHistory.length > 0 ? (
          <div className="space-y-3">
            {authorResponseHistory.map((item, idx) => (
              <div key={item.id} className="rounded-md border border-border bg-muted/40 p-3">
                <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                  <div>
                    {item.submittedAt
                      ? `Submitted at ${formatDateTimeLocal(item.submittedAt)}`
                      : 'Submitted time unavailable'}
                    {typeof item.round === 'number' ? ` · Round ${item.round}` : ''}
                  </div>
                  {idx === 0 ? <Badge variant="secondary">Latest</Badge> : null}
                </div>
                <div className="mt-2 whitespace-pre-wrap text-sm leading-6 text-foreground">{item.text}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-muted-foreground">No author resubmission comment yet.</div>
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
    <Card className="shadow-sm border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Latest Author Resubmission Comment</CardTitle>
      </CardHeader>
      <CardContent>
        {latestAuthorResponse ? (
          <div className="space-y-2">
            <div className="text-xs text-muted-foreground">
              {latestAuthorResponse.submittedAt
                ? `Submitted at ${formatDateTimeLocal(latestAuthorResponse.submittedAt)}`
                : 'Submitted time unavailable'}
              {typeof latestAuthorResponse.round === 'number' ? ` · Round ${latestAuthorResponse.round}` : ''}
              {historyCount > 0 ? ` · Total ${historyCount}` : ''}
            </div>
            <div className="max-h-44 overflow-auto rounded-md border border-border bg-muted/40 px-3 py-2 text-sm leading-6 text-foreground whitespace-pre-wrap">
              {latestAuthorResponse.text}
            </div>
            {historyCount > 1 ? (
              <div className="text-xs text-muted-foreground">
                Complete timeline is shown in the left card:{' '}
                <span className="font-medium text-foreground">Author Resubmission History</span>.
              </div>
            ) : null}
          </div>
        ) : (
          <div className="text-sm text-muted-foreground">No author resubmission comment yet.</div>
        )}
      </CardContent>
    </Card>
  )
}

type ReviewerInviteSummaryCardProps = {
  reviewerInvites: ManuscriptDetail['reviewer_invites']
  deferredLoaded?: boolean
  deferredLoading?: boolean
  loadError?: string | null
  onRetry?: () => void
  canManageReviewerOutreach?: boolean
  sendingAssignmentId?: string | null
  emailTemplateOptions?: ReviewEmailTemplateOption[]
  selectedTemplateByAssignment?: Record<string, string>
  onTemplateChange?: (args: { assignmentId: string; templateKey: string }) => void
  onSendTemplateEmail?: (args: {
    assignmentId: string
    reviewerId: string
    templateKey: string
  }) => void
  onOpenHistory?: (args: { reviewerId: string; reviewerLabel: string }) => void
}

type ReviewerInviteRow = NonNullable<ManuscriptDetail['reviewer_invites']>[number]

const REVIEWER_STATE_LABELS = {
  selected: 'Selected',
  invited: 'Invited',
  opened: 'Opened',
  accepted: 'Accepted',
  submitted: 'Submitted',
  declined: 'Declined',
} as const

function resolveInviteStateMeta(invite: ReviewerInviteRow | null | undefined) {
  const state = resolveReviewerInviteSummaryState(invite)
  const stateAt =
    state === 'invited'
      ? invite?.invited_at || invite?.opened_at || null
      : state === 'opened'
        ? invite?.opened_at || invite?.invited_at || null
        : state === 'accepted'
          ? invite?.accepted_at || null
          : state === 'submitted'
            ? invite?.accepted_at || invite?.submitted_at || null
            : state === 'declined'
              ? invite?.declined_at || null
              : null

  return {
    state,
    label: REVIEWER_STATE_LABELS[state],
    stateAt,
    className:
      state === 'declined'
        ? 'font-medium text-destructive'
        : state === 'selected'
          ? 'font-medium text-muted-foreground'
          : 'font-medium text-foreground',
  }
}

function resolveReviewProgressMeta(invite: ReviewerInviteRow | null | undefined) {
  const state = resolveReviewerInviteSummaryState(invite)
  if (state === 'submitted') {
    return {
      label: 'Submitted',
      at: invite?.submitted_at || null,
      className: 'font-medium text-foreground',
    }
  }
  if (state === 'accepted') {
    return {
      label: 'Not started',
      at: invite?.accepted_at || null,
      className: 'font-medium text-muted-foreground',
    }
  }
  if (state === 'declined') {
    return {
      label: 'Declined',
      at: invite?.declined_at || null,
      className: 'font-medium text-destructive',
    }
  }
  return {
    label: 'Pending response',
    at: invite?.opened_at || invite?.invited_at || null,
    className: 'font-medium text-muted-foreground',
  }
}

function resolveDeliveryMeta(invite: ReviewerInviteRow | null | undefined): {
  label: string
  at: string | null
  className: string
  error: string | null
} {
  const status = String(invite?.latest_email_status || '').trim().toLowerCase()
  const at = invite?.latest_email_at || null
  const error = String(invite?.latest_email_error || '').trim() || null

  if (status === 'failed') {
    return {
      label: 'failed',
      at,
      className: 'font-medium text-destructive',
      error,
    }
  }

  if (status === 'sent') {
    return {
      label: 'sent',
      at,
      className: 'font-medium text-primary',
      error: null,
    }
  }

  if (status === 'queued') {
    return {
      label: 'queued',
      at,
      className: 'font-medium text-muted-foreground',
      error: null,
    }
  }

  if (status === 'pending_retry') {
    return {
      label: 'pending_retry',
      at,
      className: 'font-medium text-amber-600',
      error,
    }
  }

  return {
    label: '—',
    at: null,
    className: 'font-medium text-muted-foreground',
    error: null,
  }
}

function formatAuditActorLine(args: {
  label: 'Selected' | 'Invited'
  actorName?: string | null
  actorEmail?: string | null
  via?: string | null
}) {
  const actorLabel = String(args.actorName || '').trim() || String(args.actorEmail || '').trim()
  const viaLabel = formatReviewerAuditVia(args.via)
  if (actorLabel && viaLabel) return `${args.label} by ${actorLabel} via ${viaLabel}`
  if (actorLabel) return `${args.label} by ${actorLabel}`
  if (viaLabel) return `${args.label} via ${viaLabel}`
  return null
}

export function ReviewerManagementCard({
  reviewerInvites,
  deferredLoaded = true,
  deferredLoading = false,
  loadError = null,
  onRetry,
  canManageReviewerOutreach = false,
  sendingAssignmentId = null,
  emailTemplateOptions = [],
  selectedTemplateByAssignment = {},
  onTemplateChange,
  onSendTemplateEmail,
  onOpenHistory,
}: ReviewerInviteSummaryCardProps) {
  const rows = Array.isArray(reviewerInvites) ? reviewerInvites : []
  const hasTemplateOptions = emailTemplateOptions.length > 0

  return (
    <Card className="shadow-sm border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Reviewer Management</CardTitle>
      </CardHeader>
      <CardContent>
        {loadError ? (
          <div className="space-y-2">
            <div className="text-sm text-destructive">{loadError}</div>
            {onRetry ? <Button size="sm" variant="outline" onClick={onRetry} data-testid="reviewer-management-retry">Retry</Button> : null}
          </div>
        ) : !deferredLoaded ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {deferredLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Reviewer management loading...
          </div>
        ) : rows.length === 0 ? (
          <div className="text-sm text-muted-foreground">No reviewers selected yet.</div>
        ) : (
          <div className="overflow-hidden rounded-md border border-border/70">
            <Table className="min-w-[980px]">
              <TableHeader>
                <TableRow className="bg-muted/30 hover:bg-muted/30">
                  <TableHead>Reviewer</TableHead>
                  <TableHead>Invite Status</TableHead>
                  <TableHead>Review Status</TableHead>
                  <TableHead>Timeline</TableHead>
                  <TableHead className="w-[320px]">Outreach</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((invite, idx) => {
                  const assignmentId = String(invite?.id || '').trim()
                  const reviewerId = String(invite?.reviewer_id || '').trim()
                  const reviewerLabel =
                    String(invite?.reviewer_name || '').trim() ||
                    String(invite?.reviewer_email || '').trim() ||
                    `Reviewer ${idx + 1}`
                  const inviteMeta = resolveInviteStateMeta(invite)
                  const reviewMeta = resolveReviewProgressMeta(invite)
                  const invitedText = invite?.invited_at ? formatDateTimeLocal(invite.invited_at) : '—'
                  const openedText = invite?.opened_at ? formatDateTimeLocal(invite.opened_at) : '—'
                  const remindedText = invite?.last_reminded_at ? formatDateTimeLocal(invite.last_reminded_at) : '—'
                  const deliveryMeta = resolveDeliveryMeta(invite)
                  const selectedAudit = formatAuditActorLine({
                    label: 'Selected',
                    actorName: invite?.added_by_name,
                    actorEmail: invite?.added_by_email,
                    via: invite?.added_via,
                  })
                  const invitedAudit = formatAuditActorLine({
                    label: 'Invited',
                    actorName: invite?.invited_by_name,
                    actorEmail: invite?.invited_by_email,
                    via: invite?.invited_via,
                  })
                  const roundNumber =
                    typeof invite?.round_number === 'number'
                      ? invite.round_number
                      : invite?.round_number != null
                        ? Number(invite.round_number)
                        : null

                  return (
                    <TableRow key={String(invite?.id || `row-${idx}`)} className="align-top">
                      <TableCell className="align-top">
                        <div className="space-y-1">
                          <div className="font-medium text-foreground">{reviewerLabel}</div>
                          <div className="text-xs text-muted-foreground">{invite?.reviewer_email || 'No email available'}</div>
                          {Number.isFinite(roundNumber as number) ? (
                            <Badge variant="outline" className="mt-1">
                              Round {roundNumber}
                            </Badge>
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell className="align-top">
                        <div className={inviteMeta.className}>
                          {inviteMeta.label}
                          {inviteMeta.stateAt ? ` · ${formatDateLocal(inviteMeta.stateAt)}` : ''}
                        </div>
                        {invite?.due_at ? (
                          <div className="mt-1 text-xs text-muted-foreground">Due {formatDateLocal(invite.due_at)}</div>
                        ) : null}
                        {inviteMeta.state === 'declined' && (invite?.decline_reason || invite?.decline_note) ? (
                          <div className="mt-1 text-xs text-muted-foreground">
                            {formatReviewerDeclineReason(invite?.decline_reason) || 'Declined'}
                            {invite?.decline_note ? ` · ${invite.decline_note}` : ''}
                          </div>
                        ) : null}
                      </TableCell>
                      <TableCell className="align-top">
                        <div className={reviewMeta.className}>
                          {reviewMeta.label}
                          {reviewMeta.at ? ` · ${formatDateLocal(reviewMeta.at)}` : ''}
                        </div>
                        {invite?.submitted_at ? (
                          <div className="mt-1 text-xs text-muted-foreground">
                            Report submitted {formatDateTimeLocal(invite.submitted_at)}
                          </div>
                        ) : null}
                      </TableCell>
                      <TableCell className="align-top">
                        <div className="space-y-1 text-xs text-muted-foreground">
                          <div className={deliveryMeta.className}>
                            Delivery: {deliveryMeta.label}
                            {deliveryMeta.at ? ` · ${formatDateTimeLocal(deliveryMeta.at)}` : ''}
                          </div>
                          <div>Invited: {invitedText}</div>
                          <div>Opened: {openedText}</div>
                          <div>Reminded: {remindedText}</div>
                          {selectedAudit ? <div>{selectedAudit}</div> : null}
                          {invitedAudit ? <div>{invitedAudit}</div> : null}
                          {Array.isArray(invite?.email_events) && invite.email_events.length > 0 ? (
                            <div className="pt-1 space-y-1 border-t border-border/60">
                              {invite.email_events.slice(0, 2).map((event, eventIdx) => {
                                const eventLabel = formatReviewerEmailEventLabel(event)
                                const eventAt = event?.created_at ? formatDateTimeLocal(event.created_at) : '—'
                                return (
                                  <div key={`${assignmentId || idx}-event-${eventIdx}`}>
                                    {eventLabel} · {eventAt}
                                  </div>
                                )
                              })}
                            </div>
                          ) : null}
                          {deliveryMeta.error ? <div className="text-destructive">Error: {deliveryMeta.error}</div> : null}
                        </div>
                      </TableCell>
                      <TableCell className="align-top">
                        {canManageReviewerOutreach && assignmentId ? (
                          <div className="flex flex-col gap-2">
                            {hasTemplateOptions ? (
                              <Select
                                value={
                                  selectedTemplateByAssignment[assignmentId] ||
                                  emailTemplateOptions[0]?.template_key ||
                                  '__empty'
                                }
                                onValueChange={(value) => {
                                  if (!value || value === '__empty') return
                                  onTemplateChange?.({ assignmentId, templateKey: value })
                                }}
                              >
                                <SelectTrigger className="h-8 w-full text-xs">
                                  <SelectValue placeholder="Select email template" />
                                </SelectTrigger>
                                <SelectContent>
                                  {emailTemplateOptions.map((template) => (
                                    <SelectItem key={template.template_key} value={template.template_key} className="text-xs">
                                      {template.display_name}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            ) : (
                              <div className="text-xs text-muted-foreground">No active email templates.</div>
                            )}
                            <div className="flex flex-wrap gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-8 px-2.5 text-xs"
                                disabled={
                                  !reviewerId ||
                                  sendingAssignmentId === assignmentId ||
                                  !(
                                    selectedTemplateByAssignment[assignmentId] ||
                                    emailTemplateOptions[0]?.template_key
                                  )
                                }
                                onClick={() =>
                                  onSendTemplateEmail?.({
                                    assignmentId,
                                    reviewerId,
                                    templateKey:
                                      selectedTemplateByAssignment[assignmentId] ||
                                      emailTemplateOptions[0]?.template_key ||
                                      '',
                                  })
                                }
                                data-testid={`reviewer-send-template-${assignmentId}`}
                              >
                                {sendingAssignmentId === assignmentId ? (
                                  <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                                ) : (
                                  <Mail className="mr-1 h-3.5 w-3.5" />
                                )}
                                Send Email
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-8 px-2.5 text-xs"
                                disabled={!reviewerId}
                                onClick={() => onOpenHistory?.({ reviewerId, reviewerLabel })}
                                data-testid={`reviewer-history-${assignmentId}`}
                              >
                                <History className="mr-1 h-3.5 w-3.5" />
                                History
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <div className="text-xs text-muted-foreground">View only</div>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function ReviewerInviteSummaryCard({
  reviewerInvites,
  deferredLoaded = true,
  deferredLoading = false,
  loadError = null,
  onRetry,
}: ReviewerInviteSummaryCardProps) {
  const rows = Array.isArray(reviewerInvites) ? reviewerInvites : []
  const counts = rows.reduce(
    (acc, invite) => {
      const state = resolveReviewerInviteSummaryState(invite)
      acc[state] += 1
      return acc
    },
    {
      selected: 0,
      invited: 0,
      opened: 0,
      accepted: 0,
      submitted: 0,
      declined: 0,
    } satisfies Record<keyof typeof REVIEWER_STATE_LABELS, number>
  )

  return (
    <Card className="shadow-sm border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Review Summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loadError ? (
          <div className="space-y-2">
            <div className="text-sm text-destructive">{loadError}</div>
            {onRetry ? <Button size="sm" variant="outline" onClick={onRetry} data-testid="reviewer-summary-retry">Retry</Button> : null}
          </div>
        ) : !deferredLoaded ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {deferredLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Reviewer summary loading...
          </div>
        ) : rows.length === 0 ? (
          <div className="text-sm text-muted-foreground">No reviewers assigned yet.</div>
        ) : (
          <>
            <div className="text-xs text-muted-foreground">{rows.length} total reviewer records</div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {Object.entries(REVIEWER_STATE_LABELS).map(([state, label]) => (
                <div key={state} className="rounded-md border border-border bg-muted/30 px-3 py-2">
                  <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
                  <div className="mt-1 text-lg font-semibold text-foreground">
                    {counts[state as keyof typeof counts]}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

type ReviewerFeedbackSummaryCardProps = {
  canViewReviewerFeedback: boolean
  reviewCardRef: RefObject<HTMLDivElement | null>
  reviewsActivated: boolean
  reviewsLoading: boolean
  reviewsError: string | null
  reviewReports: ReviewerFeedbackItem[]
  onRetry: () => void
}

export function ReviewerFeedbackSummaryCard({
  canViewReviewerFeedback,
  reviewCardRef,
  reviewsActivated,
  reviewsLoading,
  reviewsError,
  reviewReports,
  onRetry,
}: ReviewerFeedbackSummaryCardProps) {
  return (
    <Card ref={reviewCardRef} className="shadow-sm border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          Reviewer Feedback Summary
          {!reviewsActivated ? <span className="text-xs font-normal text-muted-foreground">Deferred</span> : null}
          {reviewsActivated && reviewsLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" /> : null}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {!canViewReviewerFeedback ? (
          <div className="text-sm text-muted-foreground">You do not have permission to view reviewer feedback summary.</div>
        ) : !reviewsActivated ? (
          <div className="text-sm text-muted-foreground">Reviewer feedback will load when this card enters the viewport.</div>
        ) : reviewsLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading reviewer feedback…
          </div>
        ) : reviewsError ? (
          <div className="space-y-2">
            <div className="text-sm text-destructive">{reviewsError}</div>
            <Button size="sm" variant="outline" onClick={onRetry}>
              Retry
            </Button>
          </div>
        ) : reviewReports.length === 0 ? (
          <div className="text-sm text-muted-foreground">No reviewer feedback submitted yet.</div>
        ) : (
          reviewReports.map((report) => {
            const publicComment = String(report.comments_for_author || report.content || '').trim()
            const confidentialComment = String(report.confidential_comments_to_editor || '').trim()
            return (
              <div key={report.id} className="rounded-md border border-border bg-muted/40 p-3 space-y-2">
                <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                  <div className="font-medium text-foreground">
                    {report.reviewer_name || report.reviewer_email || report.reviewer_id || 'Reviewer'}
                  </div>
                  <div className="flex items-center gap-2">
                    {typeof report.score === 'number' ? <Badge variant="outline">Score {report.score}</Badge> : null}
                    {report.status ? <Badge variant="secondary">{String(report.status)}</Badge> : null}
                  </div>
                </div>
                <div className="text-xs text-muted-foreground">
                  {report.created_at ? formatDateTimeLocal(report.created_at) : 'Submitted time unavailable'}
                </div>
                <div className="space-y-1">
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Comments for Author</div>
                  <div className="whitespace-pre-wrap text-sm leading-6 text-foreground">{publicComment || '—'}</div>
                </div>
                {confidentialComment ? (
                  <div className="space-y-1 rounded-md border border-secondary-foreground/20 bg-secondary px-2.5 py-2">
                    <div className="text-[11px] font-semibold text-secondary-foreground uppercase tracking-wide">
                      Confidential to Editor
                    </div>
                    <div className="whitespace-pre-wrap text-sm leading-6 text-foreground">{confidentialComment}</div>
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
          <div className="pt-2 pb-4 border-b border-border/60">
            <div className="text-xs font-semibold text-muted-foreground mb-2">ASSIGN REVIEWERS</div>
            <ReviewerAssignmentSearch
              manuscriptId={manuscriptId}
              onChanged={onReviewerChanged}
              disabled={!canManageReviewers}
              viewerRoles={viewerRoles}
            />
          </div>
        )}
        {!isPostAcceptance && !canAssignReviewersStage && (
          <div className="rounded-md border border-border bg-muted/40 p-3 text-xs text-muted-foreground">
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
          <div className="rounded-md border border-border bg-muted/40 p-3 text-xs text-muted-foreground">
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
              <div className="rounded-md border border-border bg-muted/40 p-3 text-xs text-muted-foreground">
                稿件进入录用后由 Managing Editor / Production Editor 继续处理。
              </div>
            )}
          </div>
        ) : showDirectStatusTransitions ? (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-muted-foreground mb-2">CHANGE STATUS</div>
            {!canManualStatusTransition ? (
              <div className="rounded-md border border-border bg-muted/40 p-3 text-xs text-muted-foreground">
                当前账号无手动状态流转权限（仅 Managing Editor/Admin 可用）。
              </div>
            ) : nextStatuses.length === 0 ? (
              <div className="text-sm text-muted-foreground italic">No next status available.</div>
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
          <div className="rounded-md border border-border bg-muted/40 p-3 text-xs text-muted-foreground">
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
    <Card className="shadow-sm border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center justify-between">
          <span>Next Action</span>
          <Badge variant="secondary">{nextAction.phase}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-sm font-semibold text-foreground">{nextAction.title}</div>
        <div className="text-sm text-muted-foreground">{nextAction.description}</div>
        {nextAction.blockers.length > 0 && (
          <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 space-y-1">
            <div className="text-xs font-semibold text-destructive flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5" />
              Blocking Conditions
            </div>
            {nextAction.blockers.map((item) => (
              <div key={item} className="text-xs text-destructive">
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
  cardsSectionRef: RefObject<HTMLDivElement | null>
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
          {!cardsActivated ? <span className="text-xs font-normal text-muted-foreground">Deferred</span> : null}
          {cardsLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" /> : null}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {cardsError ? (
          <div className="space-y-2">
            <div className="text-sm text-destructive">{cardsError}</div>
            <Button size="sm" variant="outline" onClick={onRetry} data-testid="cards-context-retry">
              Retry
            </Button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Open Tasks</span>
              <span className="font-medium text-foreground">{taskSummary?.open_tasks_count ?? 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Overdue Tasks</span>
              <span className={`font-medium ${taskSummary?.is_overdue ? 'text-destructive' : 'text-foreground'}`}>
                {taskSummary?.overdue_tasks_count ?? 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Nearest Due</span>
              <span className="font-medium text-foreground">
                {taskSummary?.nearest_due_at ? formatDateTimeLocal(taskSummary.nearest_due_at) : '—'}
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
          {!cardsActivated ? <span className="text-xs font-normal text-muted-foreground">Deferred</span> : null}
          {cardsLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" /> : null}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {cardsError ? (
          <div className="space-y-2">
            <div className="text-sm text-destructive">{cardsError}</div>
            <Button size="sm" variant="outline" onClick={onRetry} data-testid="precheck-cards-context-retry">
              Retry
            </Button>
          </div>
        ) : isPrecheckActive ? (
          <>
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-medium text-foreground">Current Role:</span>{' '}
                <span className="text-foreground">{(roleQueue?.current_role || '—').replaceAll('_', ' ')}</span>
              </div>
              <div>
                <span className="font-medium text-foreground">Current Assignee:</span>{' '}
                <span className="text-foreground">{roleQueueAssigneeText}</span>
              </div>
              <div>
                <span className="font-medium text-foreground">Assigned At:</span>{' '}
                <span className="text-foreground">
                  {roleQueue?.assigned_at ? formatDateTimeLocal(roleQueue.assigned_at) : '—'}
                </span>
              </div>
              <div>
                <span className="font-medium text-foreground">Technical Completed:</span>{' '}
                <span className="text-foreground">
                  {roleQueue?.technical_completed_at ? formatDateTimeLocal(roleQueue.technical_completed_at) : '—'}
                </span>
              </div>
              <div>
                <span className="font-medium text-foreground">Academic Completed:</span>{' '}
                <span className="text-foreground">
                  {roleQueue?.academic_completed_at ? formatDateTimeLocal(roleQueue.academic_completed_at) : '—'}
                </span>
              </div>
            </div>
            <div className="mt-3 text-xs text-muted-foreground">Detailed role actions are merged into the Activity Timeline below.</div>
          </>
        ) : (
          <div className="space-y-2 text-sm">
            <div className="font-medium text-foreground">Pre-check completed</div>
            <div className="text-foreground">
              Last assignee: <span className="font-medium text-foreground">{roleQueueAssigneeText}</span>
            </div>
            <div className="text-foreground">
              Technical completed:{' '}
              <span className="font-medium text-foreground">
                {roleQueue?.technical_completed_at ? formatDateTimeLocal(roleQueue.technical_completed_at) : '—'}
              </span>
            </div>
            <div className="text-foreground">
              Academic completed:{' '}
              <span className="font-medium text-foreground">
                {roleQueue?.academic_completed_at ? formatDateTimeLocal(roleQueue.academic_completed_at) : '—'}
              </span>
            </div>
            <div className="pt-1 text-xs text-muted-foreground">
              Current manuscript status is <span className="font-medium">{statusLower || '—'}</span>. Full pre-check actions are in Activity Timeline.
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
