'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { FileText, Download, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { UploadReviewFile } from '@/components/editor/UploadReviewFile'

export interface FileItem {
  id: string
  label: string
  type: 'pdf' | 'doc' | 'rpt' | 'other'
  url?: string
  date?: string
}

interface FileHubCardProps {
  manuscriptFiles: FileItem[]
  reviewFiles: FileItem[]
  coverFiles: FileItem[]
  onUploadReviewFile?: () => void
  manuscriptId: string
}

function FileRow({ file }: { file: FileItem }) {
  const colorMap = {
    pdf: 'bg-red-100 text-red-600',
    doc: 'bg-blue-100 text-blue-600',
    rpt: 'bg-yellow-100 text-yellow-600',
    other: 'bg-slate-100 text-slate-600',
  }
  const colorClass = colorMap[file.type] || colorMap.other

  return (
    <div className="flex justify-between items-center text-sm p-2 bg-slate-50 rounded hover:bg-slate-100 transition-colors">
      <div className="flex items-center gap-3 overflow-hidden">
        <div className={`w-8 h-8 rounded flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${colorClass}`}>
          {file.type.toUpperCase()}
        </div>
        <div className="truncate">
          <div className="font-medium text-slate-700 truncate">{file.label}</div>
          {file.date && <div className="text-[10px] text-slate-400">{file.date}</div>}
        </div>
      </div>
      {file.url ? (
        <a
          href={file.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-800 text-xs font-medium px-2 py-1 rounded hover:bg-blue-50 flex items-center gap-1"
        >
          <Download className="h-3 w-3" /> DL
        </a>
      ) : (
        <span className="text-xs text-slate-400 px-2">Missing</span>
      )}
    </div>
  )
}

export function FileHubCard({ manuscriptFiles, reviewFiles, coverFiles, manuscriptId, onUploadReviewFile }: FileHubCardProps) {
  return (
    <Card className="shadow-sm">
      <CardHeader className="py-4 border-b">
        <CardTitle className="text-sm font-bold uppercase tracking-wide flex items-center gap-2 text-slate-700">
          <FileText className="h-4 w-4" />
          Document Repository
        </CardTitle>
      </CardHeader>
      <CardContent className="p-5 grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Manuscript Versions */}
        <div className="border border-slate-100 rounded-md p-3">
          <div className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Manuscript Versions</div>
          <div className="space-y-2">
            {manuscriptFiles.length === 0 && <div className="text-xs text-slate-400 italic">No files.</div>}
            {manuscriptFiles.map((f) => (
              <FileRow key={f.id} file={f} />
            ))}
          </div>
        </div>

        {/* Supporting Docs */}
        <div className="border border-slate-100 rounded-md p-3">
          <div className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Supporting Documents</div>
          <div className="space-y-2">
            {coverFiles.map((f) => (
              <FileRow key={f.id} file={f} />
            ))}
            {coverFiles.length === 0 && <div className="text-xs text-slate-400 italic">No cover letter.</div>}
          </div>
        </div>

        {/* Peer Review Files (Full Width) */}
        <div className="md:col-span-2 border border-slate-100 rounded-md p-3 bg-slate-50/50">
          <div className="flex justify-between items-center mb-2">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Peer Review Files (Internal)</div>
            <div className="scale-90 origin-right">
                <UploadReviewFile manuscriptId={manuscriptId} onUploaded={onUploadReviewFile || (() => {})} />
            </div>
          </div>
          <div className="space-y-2">
            {reviewFiles.length === 0 && <div className="text-xs text-slate-400 italic">No review files uploaded.</div>}
            {reviewFiles.map((f) => (
              <FileRow key={f.id} file={f} />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
