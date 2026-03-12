import { RotateCcw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface ManagingWorkspaceQuickActionsProps {
  manuscript: any
  bucket: string
  onOpenAssignModal: (id: string, mode: 'pass_and_assign' | 'bind_only') => void
  onOpenReturnModal: (target: { id: string; title: string }) => void
}

export function ManagingWorkspaceQuickActions({
  manuscript,
  bucket,
  onOpenAssignModal,
  onOpenReturnModal,
}: ManagingWorkspaceQuickActionsProps) {
  if (bucket === 'awaiting_author') {
    const hasAE = Boolean(manuscript.assistant_editor_id || manuscript.assistant_editor?.id)
    const reason = manuscript.intake_return_reason || manuscript.waiting_resubmit_reason || manuscript.status_transition_logs?.[0]?.payload?.reason
    
    return (
      <div className="space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => onOpenAssignModal(manuscript.id, 'bind_only')}>
            {hasAE ? '改派 AE' : '分配 AE'}
          </Button>
        </div>
        {reason ? (
          <div className="sf-max-w-280 truncate text-xs text-muted-foreground" title={reason}>
            退回原因: {reason}
          </div>
        ) : null}
      </div>
    )
  }

  if (bucket === 'intake') {
    if (manuscript.intake_actionable === false) {
      return (
        <div className="space-y-1">
          <Badge variant="outline" className="border-border/80 bg-muted text-muted-foreground">
            当前不可操作
          </Badge>
        </div>
      )
    }

    return (
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" onClick={() => onOpenAssignModal(manuscript.id, 'pass_and_assign')}>
          通过并分配 AE
        </Button>
        <Button size="sm" variant="destructive" onClick={() => onOpenReturnModal({ id: manuscript.id, title: manuscript.title })}>
          <RotateCcw className="h-4 w-4" />
          技术退回
        </Button>
      </div>
    )
  }

  return null
}
