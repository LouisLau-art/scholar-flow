import { cva, type VariantProps } from 'class-variance-authority'
import type { HTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

const inlineNoticeVariants = cva('rounded-md border px-3 py-2', {
  variants: {
    tone: {
      neutral: 'border-border bg-muted/40 text-muted-foreground',
      info: 'border-primary/20 bg-primary/10 text-primary',
      warning: 'border-secondary-foreground/20 bg-secondary text-secondary-foreground',
      danger: 'border-destructive/20 bg-destructive/10 text-destructive',
    },
    size: {
      sm: 'text-xs',
      md: 'text-sm',
    },
  },
  defaultVariants: {
    tone: 'neutral',
    size: 'sm',
  },
})

export type InlineNoticeProps = HTMLAttributes<HTMLDivElement> & VariantProps<typeof inlineNoticeVariants>

export function InlineNotice({ className, tone, size, ...props }: InlineNoticeProps) {
  return <div className={cn(inlineNoticeVariants({ tone, size }), className)} {...props} />
}

