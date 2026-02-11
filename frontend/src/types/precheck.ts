export type PrecheckStage = 'intake' | 'technical' | 'academic'
export type PrecheckRole = 'managing_editor' | 'assistant_editor' | 'editor_in_chief'
export type TechnicalDecision = 'pass' | 'academic' | 'revision'
export type AcademicDecision = 'review' | 'decision_phase'

export type UserSummary = {
  id: string
  full_name?: string | null
  email?: string | null
}

export type PrecheckQueueItem = {
  id: string
  title?: string | null
  status?: string | null
  pre_check_status?: PrecheckStage | string | null
  assistant_editor_id?: string | null
  current_role?: PrecheckRole | string | null
  current_assignee?: UserSummary | null
  assigned_at?: string | null
  technical_completed_at?: string | null
  academic_completed_at?: string | null
  updated_at?: string | null
}

export type PrecheckActionAck = {
  message: string
  data?: Record<string, any>
}

export type PrecheckTimelineEvent = {
  id: string
  manuscript_id: string
  from_status?: string | null
  to_status?: string | null
  comment?: string | null
  changed_by?: string | null
  created_at?: string | null
  payload?: Record<string, any> | null
}
