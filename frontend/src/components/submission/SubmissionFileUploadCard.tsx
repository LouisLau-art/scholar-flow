import { Loader2 } from 'lucide-react'

import { InlineNotice } from '@/components/ui/inline-notice'
import { Input } from '@/components/ui/input'

type SubmissionFileUploadCardProps = {
  fileName: string | null
  isUploading: boolean
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void
}

export function SubmissionFileUploadCard(props: SubmissionFileUploadCardProps) {
  return (
    <div className="rounded-lg border border-border/80 bg-card p-5">
      <label htmlFor="submission-pdf-file" className="mb-2 block text-sm font-semibold text-foreground">
        Upload Manuscript (PDF) (Required)
      </label>
      <Input
        id="submission-pdf-file"
        type="file"
        accept=".pdf,application/pdf"
        onChange={props.onFileChange}
        className="block w-full rounded-md border border-border/80 bg-background px-3 py-2 text-sm text-foreground file:mr-3 file:rounded file:border-0 file:bg-primary file:px-3 file:py-1 file:text-sm file:font-medium file:text-primary-foreground hover:file:bg-primary/90"
        disabled={props.isUploading}
        data-testid="submission-file"
      />
      <div className="mt-2 text-xs text-foreground/75">Accepted format: `.pdf`.</div>
      <div className="mt-1 text-xs text-foreground/65">
        PDF remains required for review-ready output, but metadata autofill falls back to PDF only when Word parsing is unavailable.
      </div>
      {props.isUploading ? (
        <div className="mt-2 inline-flex items-center gap-2 text-xs text-primary">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Uploading manuscript PDF…
        </div>
      ) : null}
      {!props.isUploading && props.fileName ? (
        <InlineNotice tone="info" size="sm" className="mt-2">
          Manuscript PDF uploaded: {props.fileName}
        </InlineNotice>
      ) : null}
    </div>
  )
}
