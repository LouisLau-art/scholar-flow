import type { AcademicDecision, TechnicalDecision } from '@/types/precheck'
import type {
  FinanceSortBy,
  FinanceSortOrder,
  FinanceStatusFilter,
} from '@/types/finance'
import type { EditorRbacContext } from '@/types/rbac'
import type { ReviewEmailTemplateOption } from '@/types/email-template'

export type ManuscriptsProcessFilters = {
  q?: string
  journalId?: string
  manuscriptId?: string
  statuses?: string[]
  ownerId?: string
  editorId?: string
  overdueOnly?: boolean
}

export type FinanceInvoiceFilters = {
  status?: FinanceStatusFilter
  q?: string
  page?: number
  pageSize?: number
  sortBy?: FinanceSortBy
  sortOrder?: FinanceSortOrder
}

export type EditorRbacContextResponse = {
  success: boolean
  data?: EditorRbacContext
  detail?: string
  message?: string
}

export type DecisionSubmissionPayload = {
  content: string
  decision:
    | 'accept'
    | 'reject'
    | 'major_revision'
    | 'minor_revision'
    | 'add_reviewer'
    | 'accept_after_minor_revision'
    | 'reject_resubmit'
    | 'reject_decline'
  is_final: boolean
  decision_stage?: 'first' | 'final'
  attachment_paths: string[]
  last_updated_at: string | null
}

export type ReviewStageExitPendingResolutionPayload = {
  assignment_id: string
  action: 'cancel' | 'wait'
  reason?: string
}

export type ReviewStageExitPayload = {
  target_stage: 'first' | 'final' | 'major_revision' | 'minor_revision'
  requested_outcome?:
    | 'accept'
    | 'accept_after_minor_revision'
    | 'major_revision'
    | 'reject_resubmit'
    | 'reject_decline'
  recipient_emails?: string[]
  note?: string
  accepted_pending_resolutions?: ReviewStageExitPendingResolutionPayload[]
}

export type ProductionCycleCreatePayload = {
  layout_editor_id: string
  collaborator_editor_ids?: string[]
  proofreader_author_id: string
  proof_due_at: string
}

export type ProductionCycleEditorsUpdatePayload = {
  layout_editor_id?: string
  collaborator_editor_ids?: string[] | null
}

export type AssignAEPayload = {
  ae_id: string
  owner_id?: string
  start_external_review?: boolean
  bind_owner_if_empty?: boolean
  idempotency_key?: string
}

export type SubmitIntakeRevisionPayload = {
  comment: string
  idempotency_key?: string
}

export type SubmitTechnicalCheckPayload = {
  decision: TechnicalDecision
  comment?: string
  academic_editor_id?: string
  idempotency_key?: string
}

export type RevertTechnicalCheckPayload = {
  reason: string
  source?: string
  idempotency_key?: string
}

export type SubmitAcademicCheckPayload = {
  decision: AcademicDecision
  comment?: string
  idempotency_key?: string
}

export type CachedGetOptions = {
  ttlMs?: number
  force?: boolean
}

export type ReviewerLibrarySearchOptions = {
  ttlMs?: number
  force?: boolean
  disableCache?: boolean
  roleScopeKey?: string
  page?: number
}

export type WorkspaceFetchOptions = CachedGetOptions & {
  signal?: AbortSignal
}

export type IntakeQueueFetchOptions = CachedGetOptions & {
  signal?: AbortSignal
}

export type ProcessFetchOptions = CachedGetOptions & {
  signal?: AbortSignal
}

export type ManuscriptDetailGetOptions = CachedGetOptions & {
  skipCards?: boolean
  includeHeavy?: boolean
}

export type ReviewEmailTemplateListResponse = {
  success: boolean
  data?: ReviewEmailTemplateOption[]
  detail?: string
  message?: string
}

export type AuthorEmailPreviewData = {
  subject: string
  html: string
  recipient_email: string
  resolved_recipients?: {
    to: string[]
    cc: string[]
    bcc: string[]
    reply_to: string[]
  }
}

export type TechnicalRevisionEmailPayload = {
  editor_message: string
  subject_override?: string
  html_override?: string
}

export type RevisionRequestEmailPayload = {
  decision_type: 'major' | 'minor'
  editor_message: string
  subject_override?: string
  html_override?: string
}

export type ProofreadingEmailPayload = {
  editor_message: string
  subject_override?: string
  html_override?: string
}

export type ManualEmailSendPayload = {
  recipient_email?: string
  subject_override?: string
  body_html_override?: string
  cc_emails?: string[]
  reply_to_emails?: string[]
}

export type MarkExternalSentPayload = {
  note?: string
}
