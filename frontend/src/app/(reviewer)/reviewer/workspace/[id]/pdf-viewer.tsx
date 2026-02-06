'use client'

import { Loader2 } from 'lucide-react'

interface PDFViewerProps {
  pdfUrl: string | null
  isLoading: boolean
}

export function PDFViewer({ pdfUrl, isLoading }: PDFViewerProps) {
  if (isLoading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center rounded-lg border border-slate-200 bg-white">
        <Loader2 className="h-7 w-7 animate-spin text-slate-500" />
      </div>
    )
  }

  if (!pdfUrl) {
    return (
      <div className="flex min-h-[420px] items-center justify-center rounded-lg border border-slate-200 bg-white text-sm text-slate-500">
        PDF preview is unavailable.
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <iframe
        title="Manuscript PDF"
        src={pdfUrl}
        className="h-[65vh] min-h-[420px] w-full lg:h-[calc(100vh-180px)]"
      />
    </div>
  )
}
