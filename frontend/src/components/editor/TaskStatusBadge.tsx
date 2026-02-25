import { Badge } from '@/components/ui/badge'
import type { InternalTaskStatus } from '@/types/internal-collaboration'

function label(status: InternalTaskStatus): string {
  if (status === 'todo') return 'To Do'
  if (status === 'in_progress') return 'In Progress'
  return 'Done'
}

function className(status: InternalTaskStatus): string {
  if (status === 'todo') return 'border-border bg-muted text-muted-foreground'
  if (status === 'in_progress') return 'border-amber-200 bg-amber-50 text-amber-700'
  return 'border-emerald-200 bg-emerald-50 text-emerald-700'
}

export function TaskStatusBadge({ status }: { status: InternalTaskStatus }) {
  return (
    <Badge variant="outline" className={className(status)}>
      {label(status)}
    </Badge>
  )
}
