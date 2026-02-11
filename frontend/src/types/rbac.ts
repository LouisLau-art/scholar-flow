export type EditorAction =
  | '*'
  | 'process:view'
  | 'manuscript:view_detail'
  | 'manuscript:bind_owner'
  | 'invoice:update_info'
  | 'invoice:override_apc'
  | 'decision:record_first'
  | 'decision:submit_final'
  | 'precheck:technical_check'
  | 'review:assign'
  | 'review:view_assignments'
  | 'review:unassign'
  | 'reviewer:view_assignment'
  | 'reviewer:submit_report'
  | 'author:submit'
  | 'author:view_own_manuscript'

export type JournalScopeContext = {
  enforcement_enabled: boolean
  allowed_journal_ids: string[]
  is_admin: boolean
}

export type EditorRbacContext = {
  user_id: string
  roles: string[]
  normalized_roles: string[]
  allowed_actions: EditorAction[]
  journal_scope: JournalScopeContext
}
