'use client'

import { Loader2, ExternalLink } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { buttonVariants } from '@/components/ui/button'

interface PDFViewerProps {
  pdfUrl: string | null
  isLoading: boolean
}

export function PDFViewer({ pdfUrl, isLoading }: PDFViewerProps) {
  if (isLoading) {
    return (
      <Card className="border-border shadow-sm">
        <CardContent className="flex min-h-[520px] items-center justify-center">
          <Loader2 className="h-7 w-7 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (!pdfUrl) {
    return (
      <Card className="border-border shadow-sm">
        <CardContent className="flex min-h-[520px] items-center justify-center text-sm text-muted-foreground">
          PDF preview is unavailable.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="overflow-hidden border-border shadow-sm">
      <CardHeader className="border-b border-border bg-muted/40 py-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">Manuscript Preview</CardTitle>
          <a
            href={pdfUrl}
            target="_blank"
            rel="noreferrer"
            className={buttonVariants({ variant: 'outline', size: 'sm', className: 'gap-1.5' })}
          >
            <ExternalLink className="h-4 w-4" />
            Open
          </a>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <iframe
          title="Manuscript PDF"
          src={pdfUrl}
          className="h-[72vh] min-h-[520px] w-full"
        />
      </CardContent>
    </Card>
  )
}
