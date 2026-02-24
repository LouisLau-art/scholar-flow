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
