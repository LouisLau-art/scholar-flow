import { cva, type VariantProps } from 'class-variance-authority'
import type { HTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

const statusPillVariants = cva('inline-flex items-center rounded-full px-3 py-1 text-sm font-medium', {
  variants: {
    tone: {
      neutral: 'bg-muted text-muted-foreground',
      primary: 'bg-primary/10 text-primary',
      secondary: 'bg-secondary text-secondary-foreground',
      destructive: 'bg-destructive/10 text-destructive',
    },
  },
  defaultVariants: {
    tone: 'neutral',
  },
})

export type StatusPillProps = HTMLAttributes<HTMLSpanElement> & VariantProps<typeof statusPillVariants>

export function StatusPill({ className, tone, ...props }: StatusPillProps) {
  return <span className={cn(statusPillVariants({ tone }), className)} {...props} />
}

