import { InlineNotice } from '@/components/ui/inline-notice'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import type { Journal } from '@/types/journal'
import { SubmissionAuthorContactsField } from './SubmissionAuthorContactsField'
import type { SubmissionAuthorContact } from './submission-form-utils'

type MetadataState = {
  title: string
  abstract: string
}

type TouchedState = {
  title: boolean
  abstract: boolean
  submissionEmail: boolean
  authorContacts: boolean
  datasetUrl: boolean
  sourceCodeUrl: boolean
  journal: boolean
}

type SubmissionMetadataFormProps = {
  journals: Journal[]
  isLoadingJournals: boolean
  journalLoadError: string | null
  journalId: string
  specialIssue: string
  metadata: MetadataState
  submissionEmail: string
  authorContacts: SubmissionAuthorContact[]
  datasetUrl: string
  sourceCodeUrl: string
  policyConsent: boolean
  ethicsConsent: boolean
  touched: TouchedState
  showTitleError: boolean
  showAbstractError: boolean
  showSubmissionEmailError: boolean
  showAuthorContactsError: boolean
  showDatasetError: boolean
  showSourceCodeError: boolean
  showJournalError: boolean
  showPolicyConsentError: boolean
  showEthicsConsentError: boolean
  onJournalChange: (value: string) => void
  onJournalBlur: () => void
  onSpecialIssueChange: (value: string) => void
  onTitleChange: (value: string) => void
  onTitleBlur: () => void
  onAbstractChange: (value: string) => void
  onAbstractBlur: () => void
  onSubmissionEmailChange: (value: string) => void
  onSubmissionEmailBlur: () => void
  onAuthorContactChange: (
    authorId: string,
    field: keyof Pick<SubmissionAuthorContact, 'name' | 'email' | 'affiliation'>,
    value: string,
  ) => void
  onAuthorContactsBlur: () => void
  onAddAuthorContact: () => void
  onRemoveAuthorContact: (authorId: string) => void
  onSelectCorrespondingAuthor: (authorId: string) => void
  onDatasetUrlChange: (value: string) => void
  onDatasetUrlBlur: () => void
  onSourceCodeUrlChange: (value: string) => void
  onSourceCodeUrlBlur: () => void
  onPolicyConsentChange: (value: boolean) => void
  onEthicsConsentChange: (value: boolean) => void
}

export function SubmissionMetadataForm(props: SubmissionMetadataFormProps) {
  return (
    <div className="grid grid-cols-1 gap-6">
      <div>
        <label htmlFor="submission-journal-select" className="mb-2 block text-sm font-semibold text-foreground">
          Target Journal
        </label>
        <Select
          value={props.journalId}
          onValueChange={props.onJournalChange}
          disabled={props.isLoadingJournals || props.journals.length === 0}
        >
          <SelectTrigger
            id="submission-journal-select"
            className="w-full border-border/80 bg-background text-foreground data-[placeholder]:text-foreground/70"
            data-testid="submission-journal-select"
            onBlur={props.onJournalBlur}
          >
            <SelectValue
              placeholder={
                props.isLoadingJournals
                  ? 'Loading journals...'
                  : props.journals.length === 0
                    ? 'No active journal available'
                    : 'Select a journal'
              }
            />
          </SelectTrigger>
          <SelectContent>
            {props.journals.map((journal) => (
              <SelectItem key={journal.id} value={journal.id}>
                {journal.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {props.showJournalError ? (
          <InlineNotice tone="danger" size="sm" className="mt-2" data-testid="submission-journal-error">
            Please select a target journal.
          </InlineNotice>
        ) : null}
        {props.journalLoadError ? (
          <InlineNotice tone="warning" size="sm" className="mt-2">
            Journal list load failed: {props.journalLoadError}
          </InlineNotice>
        ) : null}
        {!props.isLoadingJournals && props.journals.length === 0 && !props.journalLoadError ? (
          <InlineNotice tone="warning" size="sm" className="mt-2">
            No active journal found. Please ask admin to configure journals first.
          </InlineNotice>
        ) : null}
      </div>

      <div>
        <label htmlFor="submission-special-issue" className="mb-2 block text-sm font-semibold text-foreground">
          Target Special Issue (Optional)
        </label>
        <Input
          id="submission-special-issue"
          type="text"
          value={props.specialIssue}
          onChange={(event) => props.onSpecialIssueChange(event.target.value)}
          className="w-full rounded-md border border-border/80 bg-background px-4 py-2 text-foreground placeholder:text-foreground/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="e.g., AI for Healthcare 2026"
          data-testid="submission-special-issue"
        />
      </div>

      <div>
        <label htmlFor="submission-title" className="mb-2 block text-sm font-semibold text-foreground">
          Manuscript Title
        </label>
        <Input
          id="submission-title"
          type="text"
          value={props.metadata.title}
          onChange={(event) => props.onTitleChange(event.target.value)}
          onBlur={props.onTitleBlur}
          className="w-full rounded-md border border-border/80 bg-background px-4 py-2 text-foreground placeholder:text-foreground/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="Parsed title will appear here..."
          data-testid="submission-title"
        />
        {props.showTitleError ? (
          <p className="mt-2 text-xs text-destructive" data-testid="submission-title-error">
            Title must be at least 5 characters.
          </p>
        ) : null}
      </div>

      <div>
        <label htmlFor="submission-abstract" className="mb-2 block text-sm font-semibold text-foreground">
          Abstract
        </label>
        <Textarea
          id="submission-abstract"
          rows={6}
          value={props.metadata.abstract}
          onChange={(event) => props.onAbstractChange(event.target.value)}
          onBlur={props.onAbstractBlur}
          className="w-full rounded-md border border-border/80 bg-background px-4 py-2 text-foreground placeholder:text-foreground/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="Parsed abstract will appear here..."
          data-testid="submission-abstract"
        />
        {props.showAbstractError ? (
          <p className="mt-2 text-xs text-destructive" data-testid="submission-abstract-error">
            Abstract must be at least 30 characters.
          </p>
        ) : null}
      </div>

      <SubmissionAuthorContactsField
        submissionEmail={props.submissionEmail}
        authorContacts={props.authorContacts}
        showSubmissionEmailError={props.showSubmissionEmailError}
        showAuthorContactsError={props.showAuthorContactsError}
        onSubmissionEmailChange={props.onSubmissionEmailChange}
        onSubmissionEmailBlur={props.onSubmissionEmailBlur}
        onAuthorContactChange={props.onAuthorContactChange}
        onAuthorContactsBlur={props.onAuthorContactsBlur}
        onAddAuthorContact={props.onAddAuthorContact}
        onRemoveAuthorContact={props.onRemoveAuthorContact}
        onSelectCorrespondingAuthor={props.onSelectCorrespondingAuthor}
      />

      <div>
        <label htmlFor="submission-dataset-url" className="mb-2 block text-sm font-semibold text-foreground">
          Dataset URL (Optional)
        </label>
        <Input
          id="submission-dataset-url"
          type="url"
          value={props.datasetUrl}
          onChange={(event) => props.onDatasetUrlChange(event.target.value)}
          onBlur={props.onDatasetUrlBlur}
          className="w-full rounded-md border border-border/80 bg-background px-4 py-2 text-foreground placeholder:text-foreground/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="https://example.com/dataset"
          data-testid="submission-dataset-url"
        />
        {props.showDatasetError ? (
          <p className="mt-2 text-xs text-destructive" data-testid="submission-dataset-url-error">
            Dataset URL must start with http:// or https://.
          </p>
        ) : null}
      </div>

      <div>
        <label htmlFor="submission-source-url" className="mb-2 block text-sm font-semibold text-foreground">
          Source Code URL (Optional)
        </label>
        <Input
          id="submission-source-url"
          type="url"
          value={props.sourceCodeUrl}
          onChange={(event) => props.onSourceCodeUrlChange(event.target.value)}
          onBlur={props.onSourceCodeUrlBlur}
          className="w-full rounded-md border border-border/80 bg-background px-4 py-2 text-foreground placeholder:text-foreground/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="https://github.com/org/repo"
          data-testid="submission-source-url"
        />
        {props.showSourceCodeError ? (
          <p className="mt-2 text-xs text-destructive" data-testid="submission-source-url-error">
            Source code URL must start with http:// or https://.
          </p>
        ) : null}
      </div>

      <div className="space-y-3 rounded-md border border-border/70 bg-muted/45 p-3">
        <label className="flex cursor-pointer items-start gap-2 text-sm text-foreground/90">
          <input
            type="checkbox"
            checked={props.policyConsent}
            onChange={(event) => props.onPolicyConsentChange(event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-border"
            data-testid="submission-policy-consent"
          />
          <span>
            I confirm this submission follows journal policy, originality requirements, and publication terms.
          </span>
        </label>
        {props.showPolicyConsentError ? (
          <p className="text-xs text-destructive" data-testid="submission-policy-consent-error">
            Please confirm submission policy and publication terms.
          </p>
        ) : null}

        <label className="flex cursor-pointer items-start gap-2 text-sm text-foreground/90">
          <input
            type="checkbox"
            checked={props.ethicsConsent}
            onChange={(event) => props.onEthicsConsentChange(event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-border"
            data-testid="submission-ethics-consent"
          />
          <span>
            I confirm ethics, compliance, data/privacy, and conflict-of-interest declarations are complete and accurate.
          </span>
        </label>
        {props.showEthicsConsentError ? (
          <p className="text-xs text-destructive" data-testid="submission-ethics-consent-error">
            Please confirm ethics and compliance declaration.
          </p>
        ) : null}
      </div>
    </div>
  )
}
