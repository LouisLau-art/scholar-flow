import { Loader2 } from 'lucide-react'

import { InlineNotice } from '@/components/ui/inline-notice'
import { Input } from '@/components/ui/input'

type SubmissionWordUploadCardProps = {
  isUploadingWordFile: boolean
  wordFilePath: string | null
  wordFileName: string | null
  wordFileUploadError: string | null
  onWordFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void
}

export function SubmissionWordUploadCard(props: SubmissionWordUploadCardProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <label htmlFor="submission-word-file" className="mb-2 block text-sm font-semibold text-foreground">
        Upload Manuscript (Word) (Required)
      </label>
      <Input
        id="submission-word-file"
        type="file"
        accept=".doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={props.onWordFileChange}
        disabled={props.isUploadingWordFile}
        data-testid="submission-word-file"
        className="block w-full rounded-md border border-border/80 bg-card px-3 py-2 text-sm text-foreground file:mr-3 file:rounded file:border-0 file:bg-muted file:px-3 file:py-1 file:text-sm file:font-medium file:text-foreground hover:file:bg-muted/70"
      />
      <div className="mt-2 text-xs text-muted-foreground">Accepted formats: `.doc`, `.docx`.</div>
      {props.isUploadingWordFile ? (
        <div className="mt-2 inline-flex items-center gap-2 text-xs text-primary">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Uploading Word manuscript…
        </div>
      ) : null}
      {!props.isUploadingWordFile && props.wordFilePath ? (
        <InlineNotice tone="info" size="sm" className="mt-2">
          Word manuscript uploaded: {props.wordFileName || 'file'}
        </InlineNotice>
      ) : null}
      {props.wordFileUploadError ? (
        <InlineNotice tone="danger" size="sm" className="mt-2">
          Word manuscript upload failed: {props.wordFileUploadError}
        </InlineNotice>
      ) : null}
    </div>
  )
}
