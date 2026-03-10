export type ReviewerFeedbackItem = {
  id: string
  reviewer_id?: string | null
  reviewer_name?: string | null
  reviewer_email?: string | null
  status?: string | null
  score?: number | null
  comments_for_author?: string | null
  content?: string | null
  confidential_comments_to_editor?: string | null
  attachment_path?: string | null
  created_at?: string | null
}

export type ReviewerHistoryItem = {
  assignment_id?: string | null
  reviewer_id?: string | null
  manuscript_id?: string | null
  manuscript_title?: string | null
  manuscript_status?: string | null
  assignment_status?: string | null
  assignment_state?: string | null
  round_number?: number | null
  added_on?: string | null
  added_by?: {
    id?: string | null
    full_name?: string | null
    email?: string | null
  } | null
  added_via?: string | null
  invited_by?: {
    id?: string | null
    full_name?: string | null
    email?: string | null
  } | null
  invited_via?: string | null
  invited_at?: string | null
  opened_at?: string | null
  accepted_at?: string | null
  declined_at?: string | null
  decline_reason?: string | null
  decline_note?: string | null
  cancelled_at?: string | null
  cancelled_by?: {
    id?: string | null
    full_name?: string | null
    email?: string | null
  } | null
  cancel_reason?: string | null
  cancel_via?: string | null
  last_reminded_at?: string | null
  due_at?: string | null
  report_status?: string | null
  report_score?: number | null
  report_submitted_at?: string | null
  latest_email_status?: string | null
  latest_email_at?: string | null
  latest_email_error?: string | null
  email_events?: ReviewerEmailEvent[] | null
}

export type ReviewerEmailEvent = {
  assignment_id?: string | null
  manuscript_id?: string | null
  status?: string | null
  event_type?: string | null
  template_name?: string | null
  created_at?: string | null
  error_message?: string | null
  provider_id?: string | null
  idempotency_key?: string | null
}

export type ReviewEmailTemplateOption = {
  template_key: string
  display_name: string
  description?: string | null
  scene: string
  event_type: 'none' | 'invitation' | 'reminder'
}
