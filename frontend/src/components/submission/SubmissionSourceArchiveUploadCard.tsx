import { Loader2 } from 'lucide-react'

import { InlineNotice } from '@/components/ui/inline-notice'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

type SubmissionSourceArchiveUploadCardProps = {
  isUploadingSourceArchive: boolean
  sourceArchivePath: string | null
  sourceArchiveFileName: string | null
  sourceArchiveUploadError: string | null
  inputResetKey: number
  onSourceArchiveChange: (event: React.ChangeEvent<HTMLInputElement>) => void
  onClearSourceArchive?: () => void
}

export function SubmissionSourceArchiveUploadCard(props: SubmissionSourceArchiveUploadCardProps) {
  const canClear = Boolean(props.sourceArchivePath || props.sourceArchiveFileName)

  return (
    <div className="rounded-lg border border-border/80 bg-card p-5">
      <div className="mb-2 flex items-center justify-between gap-3">
        <label htmlFor="submission-source-archive-file" className="block text-sm font-semibold text-foreground">
          LaTeX Source ZIP (.zip)
        </label>
        {canClear && props.onClearSourceArchive ? (
          <Button type="button" variant="ghost" size="sm" onClick={props.onClearSourceArchive}>
            Remove LaTeX ZIP
          </Button>
        ) : null}
      </div>
      <Input
        key={props.inputResetKey}
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
