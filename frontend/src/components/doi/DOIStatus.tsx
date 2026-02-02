import { Badge } from '@/components/ui/badge'
import { AlertCircle, CheckCircle2, Clock, Loader2 } from 'lucide-react'

interface DOIStatusProps {
  status: 'pending' | 'processing' | 'completed' | 'failed'
  className?: string
}

export function DOIStatus({ status, className }: DOIStatusProps) {
  const config = {
    pending: { label: 'Pending', icon: Clock, variant: 'secondary' as const, iconClass: '' },
    processing: { label: 'Processing', icon: Loader2, variant: 'default' as const, iconClass: 'animate-spin' },
    completed: { label: 'Completed', icon: CheckCircle2, variant: 'secondary' as const, iconClass: '' }, 
    failed: { label: 'Failed', icon: AlertCircle, variant: 'destructive' as const, iconClass: '' },
  }

  const { label, icon: Icon, variant, iconClass } = config[status] || config.pending

  return (
    <Badge variant={variant as any} className={className}>
      <Icon className={`mr-1 h-3 w-3 ${iconClass || ''}`} />
      {label}
    </Badge>
  )
}
