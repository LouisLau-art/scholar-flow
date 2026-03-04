import { Loader2 } from 'lucide-react'

import LoginPrompt from '@/components/LoginPrompt'
import { InlineNotice } from '@/components/ui/inline-notice'
import { Button } from '@/components/ui/button'

type SubmissionFinalizePanelProps = {
  userEmail: string | null
  uploadError: string | null
  parseError: string | null
  isSubmitting: boolean
  submitDisabled: boolean
  showValidationHint: boolean
  onFinalize: () => void
}

export function SubmissionFinalizePanel(props: SubmissionFinalizePanelProps) {
  return (
    <div className="space-y-3">
      {!props.userEmail ? <LoginPrompt /> : null}
      {props.uploadError ? (
        <InlineNotice tone="danger" size="sm">
          Upload failed: {props.uploadError}
        </InlineNotice>
      ) : null}
      {props.parseError ? (
        <InlineNotice tone="warning" size="sm">
          Parsing failed: {props.parseError}
        </InlineNotice>
      ) : null}
      <Button
        onClick={props.onFinalize}
        disabled={props.submitDisabled}
        className="flex w-full items-center justify-center rounded-md bg-foreground py-3 font-semibold text-white shadow-md transition-all hover:bg-foreground/90 disabled:cursor-not-allowed disabled:opacity-50"
        data-testid="submission-finalize"
      >
        {props.isSubmitting ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Finalize Submission'}
      </Button>
      {props.userEmail && props.showValidationHint ? (
        <p className="text-center text-xs text-muted-foreground" data-testid="submission-validation-hint">
          Complete journal + metadata + required confirmations, then upload required PDF/Word/Cover Letter files.
          Optional URLs must start with http(s).
        </p>
      ) : null}
      {props.userEmail ? (
        <p className="text-center text-xs text-muted-foreground" data-testid="submission-user">
          Logged in as: {props.userEmail}
        </p>
      ) : null}
    </div>
  )
}
