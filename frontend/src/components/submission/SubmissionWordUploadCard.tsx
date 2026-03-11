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
    <div className="rounded-lg border border-border/80 bg-card p-5">
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
        className="block w-full rounded-md border border-border/80 bg-background px-3 py-2 text-sm text-foreground file:mr-3 file:rounded file:border-0 file:bg-primary file:px-3 file:py-1 file:text-sm file:font-medium file:text-primary-foreground hover:file:bg-primary/90"
      />
      <div className="mt-2 text-xs text-foreground/75">Accepted formats: `.doc`, `.docx`.</div>
      <div className="mt-1 text-xs text-foreground/65">
        Word metadata is parsed first and becomes the primary source for title and abstract autofill.
      </div>
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
