export type ReviewRecommendation = 'accept' | 'minor_revision' | 'major_revision' | 'reject'

export interface ReviewSubmission {
  comments_for_author: string
  confidential_comments_to_editor: string
  recommendation?: ReviewRecommendation
  attachments: string[]
}

export interface WorkspaceAttachment {
  path: string
  filename: string
  signed_url?: string | null
}

export interface WorkspaceTimelineEvent {
  id: string
  timestamp: string
  actor: 'reviewer' | 'editor' | 'author' | 'system'
  channel: 'public' | 'private' | 'system'
  title: string
  message?: string | null
}

export interface WorkspaceData {
  manuscript: {
    id: string
    title: string
    abstract?: string | null
    pdf_url: string
    dataset_url?: string | null
    source_code_url?: string | null
    cover_letter_url?: string | null
  }
  assignment: {
    id: string
    status: string
    due_at?: string | null
    invited_at?: string | null
    opened_at?: string | null
    accepted_at?: string | null
    submitted_at?: string | null
    decline_reason?: string | null
  }
  review_report: {
    id?: string | null
    status: string
    comments_for_author: string
    confidential_comments_to_editor: string
    recommendation?: ReviewRecommendation | null
    attachments: WorkspaceAttachment[]
    submitted_at?: string | null
  }
  permissions: {
    can_submit: boolean
    is_read_only: boolean
  }
  timeline: WorkspaceTimelineEvent[]
}
