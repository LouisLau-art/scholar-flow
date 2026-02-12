export type FinalDecision = 'accept' | 'reject' | 'major_revision' | 'minor_revision'

export type DecisionAttachment = {
  id: string
  path: string
  name: string
}

export type DecisionReport = {
  id: string
  reviewer_id?: string | null
  reviewer_name?: string | null
  reviewer_email?: string | null
  status?: string | null
  score?: number | null
  comments_for_author?: string | null
  confidential_comments_to_editor?: string | null
  created_at?: string | null
  attachment?: {
    id: string
    path: string
    signed_url?: string | null
  } | null
}

export type DecisionDraft = {
  id: string
  content: string
  decision: FinalDecision
  status: 'draft' | 'final'
  last_updated_at: string
  attachments: DecisionAttachment[]
}

export type DecisionContext = {
  manuscript: {
    id: string
    title: string
    abstract?: string | null
    status?: string | null
    version?: number
    pdf_url?: string | null
  }
  reports: DecisionReport[]
  draft?: DecisionDraft | null
  templates: Array<{ id: string; name: string; content: string }>
  permissions?: {
    can_record_first?: boolean
    can_submit_final?: boolean
    can_submit: boolean
    is_read_only: boolean
  }
}
