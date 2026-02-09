export type InternalTaskStatus = 'todo' | 'in_progress' | 'done'
export type InternalTaskPriority = 'low' | 'medium' | 'high'

export type InternalUserSummary = {
  id: string
  full_name?: string | null
  email?: string | null
}

export type InternalComment = {
  id: string
  manuscript_id?: string
  content: string
  created_at: string
  user_id?: string
  mention_user_ids?: string[]
  user?: Pick<InternalUserSummary, 'full_name' | 'email'>
}

export type CreateInternalCommentPayload = {
  content: string
  mention_user_ids?: string[]
}

export type InternalTask = {
  id: string
  manuscript_id: string
  title: string
  description?: string | null
  assignee_user_id: string
  status: InternalTaskStatus
  priority: InternalTaskPriority
  due_at: string
  created_by: string
  created_at?: string
  updated_at?: string
  completed_at?: string | null
  is_overdue?: boolean
  can_edit?: boolean
  assignee?: InternalUserSummary | null
  creator?: InternalUserSummary | null
}

export type CreateInternalTaskPayload = {
  title: string
  description?: string
  assignee_user_id: string
  due_at: string
  status?: InternalTaskStatus
  priority?: InternalTaskPriority
}

export type UpdateInternalTaskPayload = {
  title?: string
  description?: string | null
  assignee_user_id?: string
  due_at?: string
  status?: InternalTaskStatus
  priority?: InternalTaskPriority
}

export type InternalTaskActivity = {
  id: string
  task_id: string
  manuscript_id: string
  action: string
  actor_user_id: string
  before_payload?: Record<string, unknown> | null
  after_payload?: Record<string, unknown> | null
  created_at: string
  actor?: InternalUserSummary | null
}
