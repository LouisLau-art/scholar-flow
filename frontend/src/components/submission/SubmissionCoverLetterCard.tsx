import { Loader2 } from 'lucide-react'

import { InlineNotice } from '@/components/ui/inline-notice'
import { Input } from '@/components/ui/input'

type SubmissionCoverLetterCardProps = {
  isUploadingCoverLetter: boolean
  coverLetterPath: string | null
  coverLetterFileName: string | null
  coverLetterUploadError: string | null
  onCoverLetterChange: (event: React.ChangeEvent<HTMLInputElement>) => void
}

export function SubmissionCoverLetterCard(props: SubmissionCoverLetterCardProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <label htmlFor="submission-cover-letter-file" className="mb-2 block text-sm font-semibold text-foreground">
        Cover Letter (Required)
      </label>
      <Input
        id="submission-cover-letter-file"
        type="file"
        accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={props.onCoverLetterChange}
        disabled={props.isUploadingCoverLetter}
        data-testid="submission-cover-letter-file"
        className="block w-full rounded-md border border-border/80 bg-card px-3 py-2 text-sm text-foreground file:mr-3 file:rounded file:border-0 file:bg-muted file:px-3 file:py-1 file:text-sm file:font-medium file:text-foreground hover:file:bg-muted/70"
      />
      <div className="mt-2 text-xs text-muted-foreground">Accepted formats: `.pdf`, `.doc`, `.docx`.</div>
      {props.isUploadingCoverLetter ? (
        <div className="mt-2 inline-flex items-center gap-2 text-xs text-primary">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Uploading cover letter…
        </div>
      ) : null}
      {!props.isUploadingCoverLetter && props.coverLetterPath ? (
        <InlineNotice tone="info" size="sm" className="mt-2">
          Cover letter uploaded: {props.coverLetterFileName || 'file'}
        </InlineNotice>
      ) : null}
      {props.coverLetterUploadError ? (
        <InlineNotice tone="danger" size="sm" className="mt-2">
          Cover letter upload failed: {props.coverLetterUploadError}
        </InlineNotice>
      ) : null}
    </div>
  )
}
