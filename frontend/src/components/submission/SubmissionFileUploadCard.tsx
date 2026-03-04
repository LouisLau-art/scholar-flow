import { Upload, Loader2 } from 'lucide-react'

import { Input } from '@/components/ui/input'

type SubmissionFileUploadCardProps = {
  fileName: string | null
  isUploading: boolean
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void
}

export function SubmissionFileUploadCard(props: SubmissionFileUploadCardProps) {
  return (
    <div
      className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-colors ${
        props.fileName ? 'border-primary bg-primary/10' : 'border-border/80 hover:border-primary'
      }`}
    >
      <div className="mb-3 text-sm font-semibold text-foreground">Upload Manuscript (PDF) (Required)</div>
      <Input
        type="file"
        accept=".pdf,application/pdf"
        onChange={props.onFileChange}
        className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
        disabled={props.isUploading}
        data-testid="submission-file"
      />
      <Upload className={`mb-4 h-12 w-12 ${props.fileName ? 'text-primary' : 'text-muted-foreground'}`} />
      <p className="text-lg font-medium text-foreground">
        {props.fileName || 'Drag and drop your PDF here'}
      </p>
      <p className="mt-2 text-xs text-muted-foreground">This PDF is used for metadata extraction and reviewer/editor preview.</p>
      {props.isUploading ? <Loader2 className="mt-2 h-6 w-6 animate-spin text-primary" /> : null}
    </div>
  )
}
