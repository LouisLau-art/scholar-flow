'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ExternalLink, FileText } from 'lucide-react'

export type FileCardItem = {
  id: string
  label: string
  href?: string | null
  meta?: string | null
}

export function FileSectionCard({
  title,
  description,
  items,
  emptyText,
  action,
}: {
  title: string
  description?: string
  items: FileCardItem[]
  emptyText?: string
  action?: React.ReactNode
}) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-3 border-b border-border/60 flex-row items-start justify-between gap-3">
        <div className="space-y-1">
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            {title}
          </CardTitle>
          {description ? <p className="text-xs text-muted-foreground">{description}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </CardHeader>
      <CardContent className="pt-4">
        {items.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-card p-3 text-sm text-muted-foreground">
            {emptyText || 'Not uploaded.'}
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card px-3 py-2"
              >
                <div className="min-w-0">
                  <div className="text-sm text-foreground truncate">{item.label}</div>
                  {item.meta ? <div className="text-xs text-muted-foreground truncate">{item.meta}</div> : null}
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-2"
                  disabled={!item.href}
                  onClick={() => {
                    if (!item.href) return
                    window.open(item.href, '_blank', 'noopener,noreferrer')
                  }}
                >
                  <ExternalLink className="h-4 w-4" />
                  Open
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
