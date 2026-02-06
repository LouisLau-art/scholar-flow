export type ReviewRecommendation = 'accept' | 'minor_revision' | 'major_revision' | 'reject'

export interface ReviewSubmission {
  comments_for_author: string
  confidential_comments_to_editor: string
  recommendation: ReviewRecommendation
  attachments: string[]
}

export interface WorkspaceData {
  manuscript: {
    id: string
    title: string
    abstract?: string | null
    pdf_url: string
  }
  review_report: {
    id?: string | null
    status: string
    comments_for_author: string
    confidential_comments_to_editor: string
    recommendation?: ReviewRecommendation | null
    attachments: string[]
  }
  permissions: {
    can_submit: boolean
    is_read_only: boolean
  }
}
