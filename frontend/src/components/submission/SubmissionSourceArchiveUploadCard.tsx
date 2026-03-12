import { Loader2 } from 'lucide-react'

import { InlineNotice } from '@/components/ui/inline-notice'
import { Input } from '@/components/ui/input'

type SubmissionSourceArchiveUploadCardProps = {
  isUploadingSourceArchive: boolean
  sourceArchivePath: string | null
  sourceArchiveFileName: string | null
  sourceArchiveUploadError: string | null
  onSourceArchiveChange: (event: React.ChangeEvent<HTMLInputElement>) => void
}

export function SubmissionSourceArchiveUploadCard(props: SubmissionSourceArchiveUploadCardProps) {
  return (
    <div className="rounded-lg border border-border/80 bg-card p-5">
      <label htmlFor="submission-source-archive-file" className="mb-2 block text-sm font-semibold text-foreground">
        LaTeX Source ZIP (.zip) (Optional)
      </label>
      <Input
        id="submission-source-archive-file"
        type="file"
        accept=".zip,application/zip,application/x-zip-compressed"
        onChange={props.onSourceArchiveChange}
        disabled={props.isUploadingSourceArchive}
        data-testid="submission-source-archive-file"
        className="block w-full rounded-md border border-border/80 bg-background px-3 py-2 text-sm text-foreground file:mr-3 file:rounded file:border-0 file:bg-primary file:px-3 file:py-1 file:text-sm file:font-medium file:text-primary-foreground hover:file:bg-primary/90"
      />
      <div className="mt-2 text-xs text-foreground/75">Accepted format: `.zip`.</div>
      <div className="mt-1 text-xs text-foreground/65">
        Use this for LaTeX submissions. ZIP is stored for editorial use only and is not used for metadata parsing.
      </div>
      <div className="mt-1 text-xs text-foreground/65">
        Uploading a ZIP source archive will replace any previously uploaded Word manuscript.
      </div>
      {props.isUploadingSourceArchive ? (
        <div className="mt-2 inline-flex items-center gap-2 text-xs text-primary">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Uploading LaTeX source ZIP…
        </div>
      ) : null}
      {!props.isUploadingSourceArchive && props.sourceArchivePath ? (
        <InlineNotice tone="info" size="sm" className="mt-2">
          LaTeX source ZIP uploaded: {props.sourceArchiveFileName || 'file'}
        </InlineNotice>
      ) : null}
      {props.sourceArchiveUploadError ? (
        <InlineNotice tone="danger" size="sm" className="mt-2">
          LaTeX source ZIP upload failed: {props.sourceArchiveUploadError}
        </InlineNotice>
      ) : null}
    </div>
  )
}
