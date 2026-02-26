import { Badge } from '@/components/ui/badge'
import { cva } from 'class-variance-authority'
import type { InternalTaskStatus } from '@/types/internal-collaboration'

function label(status: InternalTaskStatus): string {
  if (status === 'todo') return 'To Do'
  if (status === 'in_progress') return 'In Progress'
  return 'Done'
}

const taskStatusBadgeVariants = cva('border', {
  variants: {
    status: {
      todo: 'border-border bg-muted text-muted-foreground',
      in_progress: 'border-secondary-foreground/20 bg-secondary text-secondary-foreground',
      done: 'border-primary/30 bg-primary/10 text-primary',
    },
  },
  defaultVariants: {
    status: 'todo',
  },
})

export function TaskStatusBadge({ status }: { status: InternalTaskStatus }) {
  return (
    <Badge variant="outline" className={taskStatusBadgeVariants({ status })}>
      {label(status)}
    </Badge>
  )
}
