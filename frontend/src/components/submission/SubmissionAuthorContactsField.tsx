import { Button } from '@/components/ui/button'
import { InlineNotice } from '@/components/ui/inline-notice'
import { Input } from '@/components/ui/input'
import type { SubmissionAuthorContact } from './submission-form-utils'

type SubmissionAuthorContactsFieldProps = {
  submissionEmail: string
  authorContacts: SubmissionAuthorContact[]
  showSubmissionEmailError: boolean
  showAuthorContactsError: boolean
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
  onMoveAuthorContact: (authorId: string, direction: 'up' | 'down') => void
  onSelectCorrespondingAuthor: (authorId: string) => void
}

export function SubmissionAuthorContactsField(props: SubmissionAuthorContactsFieldProps) {
  return (
    <div className="space-y-4 rounded-md border border-border/70 bg-muted/30 p-4" data-testid="submission-author-contacts">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Author Contacts</h3>
          <p className="mt-1 text-xs text-foreground/70">
            Add all manuscript authors here. Authors do not need ScholarFlow accounts. Keep exactly one corresponding author.
          </p>
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={props.onAddAuthorContact}
          data-testid="submission-add-author"
        >
          Add Author
        </Button>
      </div>

      <div>
        <label htmlFor="submission-email" className="mb-2 block text-sm font-semibold text-foreground">
          Submission Email
        </label>
        <Input
          id="submission-email"
          type="email"
          value={props.submissionEmail}
          onChange={(event) => props.onSubmissionEmailChange(event.target.value)}
          onBlur={props.onSubmissionEmailBlur}
          className="w-full rounded-md border border-border/80 bg-background px-4 py-2 text-foreground placeholder:text-foreground/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="submission-contact@example.com"
          data-testid="submission-email"
        />
        <p className="mt-2 text-xs text-foreground/65">
          This address can belong to a student or assistant submitting on behalf of the authors. It does not need to match any listed author email.
        </p>
        {props.showSubmissionEmailError ? (
          <InlineNotice tone="danger" size="sm" className="mt-2" data-testid="submission-email-error">
            Please provide a valid submission email address.
          </InlineNotice>
        ) : null}
      </div>

      <div className="space-y-4">
        {props.authorContacts.map((author, index) => {
          const deleteDisabled = props.authorContacts.length === 1
          return (
            <div
              key={author.id}
              className="space-y-4 rounded-md border border-border/60 bg-background/70 p-4"
              data-testid={`submission-author-card-${index}`}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h4 className="text-sm font-semibold text-foreground">Author {index + 1}</h4>
                  <p className="mt-1 text-xs text-foreground/65">
                    {author.isCorresponding ? 'Corresponding author' : 'Co-author'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={index === 0}
                    onClick={() => props.onMoveAuthorContact(author.id, 'up')}
                    data-testid={`submission-move-author-up-${index}`}
                  >
                    Move Up
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={index === props.authorContacts.length - 1}
                    onClick={() => props.onMoveAuthorContact(author.id, 'down')}
                    data-testid={`submission-move-author-down-${index}`}
                  >
                    Move Down
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={deleteDisabled}
                    onClick={() => props.onRemoveAuthorContact(author.id)}
                    data-testid={`submission-remove-author-${index}`}
                  >
                    Remove
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <label
                    htmlFor={`submission-author-name-${index}`}
                    className="mb-2 block text-sm font-semibold text-foreground"
                  >
                    Name
                  </label>
                  <Input
                    id={`submission-author-name-${index}`}
                    type="text"
                    value={author.name}
                    onChange={(event) => props.onAuthorContactChange(author.id, 'name', event.target.value)}
                    onBlur={props.onAuthorContactsBlur}
                    className="w-full rounded-md border border-border/80 bg-background px-4 py-2 text-foreground placeholder:text-foreground/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g., Alice Zhang"
                    data-testid={`submission-author-name-${index}`}
                  />
                </div>

                <div>
                  <label
                    htmlFor={`submission-author-email-${index}`}
                    className="mb-2 block text-sm font-semibold text-foreground"
                  >
                    Email
                  </label>
                  <Input
                    id={`submission-author-email-${index}`}
                    type="email"
                    value={author.email}
                    onChange={(event) => props.onAuthorContactChange(author.id, 'email', event.target.value)}
                    onBlur={props.onAuthorContactsBlur}
                    className="w-full rounded-md border border-border/80 bg-background px-4 py-2 text-foreground placeholder:text-foreground/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="author@example.com"
                    data-testid={`submission-author-email-${index}`}
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor={`submission-author-affiliation-${index}`}
                  className="mb-2 block text-sm font-semibold text-foreground"
                >
                  Affiliation
                </label>
                <Input
                  id={`submission-author-affiliation-${index}`}
                  type="text"
                  value={author.affiliation}
                  onChange={(event) => props.onAuthorContactChange(author.id, 'affiliation', event.target.value)}
                  onBlur={props.onAuthorContactsBlur}
                  className="w-full rounded-md border border-border/80 bg-background px-4 py-2 text-foreground placeholder:text-foreground/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="e.g., Central China Normal University"
                  data-testid={`submission-author-affiliation-${index}`}
                />
              </div>

              <label className="flex cursor-pointer items-center gap-3 text-sm text-foreground/90">
                <input
                  type="radio"
                  name="submission-corresponding-author"
                  checked={author.isCorresponding}
                  onChange={() => props.onSelectCorrespondingAuthor(author.id)}
                  onBlur={props.onAuthorContactsBlur}
                  className="h-4 w-4 border-border text-primary focus:ring-primary"
                  data-testid={`submission-author-corresponding-${index}`}
                />
                <span>Set as corresponding author</span>
              </label>
            </div>
          )
        })}
      </div>

      {props.showAuthorContactsError ? (
        <InlineNotice tone="danger" size="sm" data-testid="submission-author-contacts-error">
          Every author must include name, email, and affiliation. Keep exactly one corresponding author.
        </InlineNotice>
      ) : null}
    </div>
  )
}
