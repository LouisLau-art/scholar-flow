import { User } from '@/types/user'

export type InvitePolicyHit = {
  code: 'cooldown' | 'conflict' | 'overdue_risk' | string
  label?: string
  severity?: 'error' | 'warning' | 'info' | string
  blocking?: boolean
  detail?: string
}

export type InvitePolicy = {
  can_assign?: boolean
  allow_override?: boolean
  cooldown_active?: boolean
  conflict?: boolean
  overdue_risk?: boolean
  overdue_open_count?: number
  cooldown_until?: string
  hits?: InvitePolicyHit[]
}

export type ReviewerWithPolicy = User & {
  invite_policy?: InvitePolicy
}
