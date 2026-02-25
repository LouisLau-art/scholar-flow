'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { FileText, Download } from 'lucide-react'
import { UploadReviewFile } from '@/components/editor/UploadReviewFile'
import { UploadCoverLetter } from '@/components/editor/UploadCoverLetter'

export interface FileItem {
  id: string
  label: string
  type: 'pdf' | 'doc' | 'rpt' | 'other'
  badge?: string
  url?: string
  date?: string
}

interface FileHubCardProps {
  manuscriptFiles: FileItem[]
  reviewFiles: FileItem[]
  coverFiles: FileItem[]
  onUploadReviewFile?: () => void
  onUploadCoverLetter?: () => void
  manuscriptId: string
}

function FileRow({ file }: { file: FileItem }) {
  const colorMap = {
    pdf: 'bg-destructive/10 text-destructive',
    doc: 'bg-primary/10 text-primary',
    rpt: 'bg-muted text-muted-foreground',
    other: 'bg-muted text-muted-foreground',
  }
  const colorClass = colorMap[file.type] || colorMap.other

  return (
    <div className="flex items-center justify-between rounded bg-muted/50 p-2 text-sm transition-colors hover:bg-muted">
      <div className="flex items-center gap-3 overflow-hidden">
        <div className={`w-8 h-8 rounded flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${colorClass}`}>
          {(file.badge || file.type.toUpperCase()).slice(0, 4)}
        </div>
        <div className="truncate">
          <div className="truncate font-medium text-foreground">{file.label}</div>
          {file.date && <div className="text-[10px] text-muted-foreground">{file.date}</div>}
        </div>
      </div>
      {file.url ? (
        <a
          href={file.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-primary hover:bg-primary/10 hover:text-primary"
        >
          <Download className="h-3 w-3" /> DL
        </a>
      ) : (
        <span className="px-2 text-xs text-muted-foreground">Missing</span>
      )}
    </div>
  )
}

export function FileHubCard({
  manuscriptFiles,
  reviewFiles,
  coverFiles,
  manuscriptId,
  onUploadReviewFile,
  onUploadCoverLetter,
}: FileHubCardProps) {
  return (
    <Card className="shadow-sm">
      <CardHeader className="py-4 border-b">
        <CardTitle className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-muted-foreground">
          <FileText className="h-4 w-4" />
          Document Repository
        </CardTitle>
      </CardHeader>
      <CardContent className="p-5 grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Manuscript Versions */}
        <div className="rounded-md border border-border p-3">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Manuscript Versions</div>
          <div className="space-y-2">
            {manuscriptFiles.length === 0 && <div className="text-xs italic text-muted-foreground">No files.</div>}
            {manuscriptFiles.map((f) => (
              <FileRow key={f.id} file={f} />
            ))}
          </div>
        </div>

        {/* Supporting Docs */}
        <div className="rounded-md border border-border p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Supporting Documents</div>
            <div className="scale-90 origin-right">
              <UploadCoverLetter manuscriptId={manuscriptId} onUploaded={onUploadCoverLetter || (() => {})} />
            </div>
          </div>
          <div className="space-y-2">
            {coverFiles.map((f) => (
              <FileRow key={f.id} file={f} />
            ))}
            {coverFiles.length === 0 && <div className="text-xs italic text-muted-foreground">No cover letter.</div>}
          </div>
        </div>

        {/* Peer Review Files (Full Width) */}
        <div className="md:col-span-2 rounded-md border border-border bg-muted/50 p-3">
          <div className="flex justify-between items-center mb-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Peer Review Files (Internal)</div>
            <div className="scale-90 origin-right">
              <UploadReviewFile manuscriptId={manuscriptId} onUploaded={onUploadReviewFile || (() => {})} />
            </div>
          </div>
          <div className="space-y-2">
            {reviewFiles.length === 0 && <div className="text-xs italic text-muted-foreground">No review files uploaded.</div>}
            {reviewFiles.map((f) => (
              <FileRow key={f.id} file={f} />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
