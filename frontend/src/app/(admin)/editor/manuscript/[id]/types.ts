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
  round_number?: number | null
  added_on?: string | null
  invited_at?: string | null
  opened_at?: string | null
  accepted_at?: string | null
  declined_at?: string | null
  last_reminded_at?: string | null
  due_at?: string | null
  report_status?: string | null
  report_score?: number | null
  report_submitted_at?: string | null
}
