export type ProductionCycleStatus =
  | 'draft'
  | 'awaiting_author'
  | 'author_confirmed'
  | 'author_corrections_submitted'
  | 'in_layout_revision'
  | 'approved_for_publish'
  | 'cancelled'

export type ProofreadingDecision = 'confirm_clean' | 'submit_corrections'

export type ProductionCorrectionItem = {
  id?: string
  line_ref?: string | null
  original_text?: string | null
  suggested_text: string
  reason?: string | null
  sort_order?: number
}

export type ProductionProofreadingResponse = {
  id?: string
  cycle_id?: string
  manuscript_id?: string
  author_id?: string
  decision: ProofreadingDecision
  summary?: string | null
  submitted_at?: string
  is_late?: boolean
  corrections?: ProductionCorrectionItem[]
}

export type ProductionCycle = {
  id: string
  manuscript_id: string
  cycle_no: number
  status: ProductionCycleStatus
  layout_editor_id: string
  collaborator_editor_ids?: string[]
  proofreader_author_id: string
  galley_bucket?: string | null
  galley_path?: string | null
  galley_signed_url?: string | null
  version_note?: string | null
  proof_due_at?: string | null
  approved_by?: string | null
  approved_at?: string | null
  created_at?: string | null
  updated_at?: string | null
  latest_response?: ProductionProofreadingResponse | null
}

export type ProductionWorkspaceContext = {
  manuscript: {
    id: string
    title: string
    status?: string | null
    author_id?: string | null
    editor_id?: string | null
    owner_id?: string | null
    pdf_url?: string | null
  }
  active_cycle?: ProductionCycle | null
  cycle_history: ProductionCycle[]
  permissions?: {
    can_create_cycle: boolean
    can_manage_editors?: boolean
    can_upload_galley: boolean
    can_approve: boolean
  }
}

export type ProofreadingContext = {
  manuscript: {
    id: string
    title: string
    status?: string | null
  }
  cycle: ProductionCycle
  can_submit: boolean
  is_read_only: boolean
}
