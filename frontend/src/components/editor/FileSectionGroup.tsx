'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, ExternalLink } from 'lucide-react'

export type FileLinkItem = {
  id: string
  label: string
  href?: string | null
  meta?: string | null
}

export type FileSection = {
  title: string
  items: FileLinkItem[]
  emptyText?: string
}

export function FileSectionGroup({ title, sections }: { title: string; sections: FileSection[] }) {
  return (
    <Card>
      <CardHeader className="pb-3 border-b border-slate-100">
        <CardTitle className="text-lg flex items-center gap-2">
          <FileText className="h-5 w-5 text-slate-500" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-4 space-y-5">
        {sections.map((section) => (
          <div key={section.title} className="space-y-2">
            <div className="text-sm font-semibold text-slate-800">{section.title}</div>
            {section.items.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-200 bg-white p-3 text-sm text-slate-500">
                {section.emptyText || 'Not uploaded.'}
              </div>
            ) : (
              <div className="space-y-2">
                {section.items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2"
                  >
                    <div className="min-w-0">
                      <div className="text-sm text-slate-900 truncate">{item.label}</div>
                      {item.meta ? <div className="text-xs text-slate-500 truncate">{item.meta}</div> : null}
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
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

