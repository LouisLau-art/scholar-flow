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
      <Card className="border-slate-200 shadow-sm">
        <CardContent className="flex min-h-[520px] items-center justify-center">
          <Loader2 className="h-7 w-7 animate-spin text-slate-500" />
        </CardContent>
      </Card>
    )
  }

  if (!pdfUrl) {
    return (
      <Card className="border-slate-200 shadow-sm">
        <CardContent className="flex min-h-[520px] items-center justify-center text-sm text-slate-500">
          PDF preview is unavailable.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="overflow-hidden border-slate-200 shadow-sm">
      <CardHeader className="border-b border-slate-200 bg-slate-50 py-3">
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
