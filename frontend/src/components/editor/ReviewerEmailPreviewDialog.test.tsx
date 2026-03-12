import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { ReviewerEmailPreviewData } from '@/app/(admin)/editor/manuscript/[id]/types'

import { ReviewerEmailPreviewDialog } from './ReviewerEmailPreviewDialog'

vi.mock('./ReviewerEmailComposeEditor', () => ({
  ReviewerEmailComposeEditor: (props: {
    value: string
    disabled?: boolean
    onChange: (value: string) => void
  }) => (
    <textarea
      data-testid="reviewer-email-compose-editor"
      value={props.value}
      readOnly={Boolean(props.disabled)}
      onChange={(event) => props.onChange(event.target.value)}
    />
  ),
}))

const preview: ReviewerEmailPreviewData = {
  assignment_id: 'assignment-1',
  template_key: 'reviewer_invitation_standard',
  template_display_name: '审稿邀请信（标准）',
  event_type: 'invitation',
  reviewer_email: 'reviewer@example.com',
  reviewer_name: 'Reviewer X',
  recipient_email: 'reviewer@example.com',
  recipient_overridden: false,
  journal_title: 'Journal One',
  review_url: 'https://example.com/review/invite?token=abc',
  resolved_recipients: {
    to: ['reviewer@example.com'],
    cc: ['office@example.org'],
    bcc: [],
    reply_to: ['office@example.org'],
  },
  subject: 'Invitation to Review - Journal One',
  html: '<p>Hello <a href="https://example.com/review/invite?token=abc">Review Link</a></p>',
  text: 'Hello reviewer',
  reply_to: ['office@example.org'],
  delivery_mode: 'manual',
  can_send: true,
}

describe('ReviewerEmailPreviewDialog', () => {
  it('allows editing envelope and content while keeping plain text derived from current html', () => {
    const onRecipientEmailChange = vi.fn()
    const onCcChange = vi.fn()
    const onReplyToChange = vi.fn()
    const onSend = vi.fn()

    function Wrapper() {
      const [recipient, setRecipient] = useState('assistant@example.com')
      const [cc, setCc] = useState('office@example.org')
      const [replyTo, setReplyTo] = useState('office@example.org')
      const [subject, setSubject] = useState(preview.subject)
      const [html, setHtml] = useState(preview.html)

      return (
        <ReviewerEmailPreviewDialog
          open
          loading={false}
          sending={false}
          preview={preview}
          recipientEmail={recipient}
          ccValue={cc}
          replyToValue={replyTo}
          subjectValue={subject}
          htmlValue={html}
          onSubjectChange={setSubject}
          onHtmlChange={setHtml}
          onRecipientEmailChange={(value) => {
            setRecipient(value)
            onRecipientEmailChange(value)
          }}
          onCcChange={(value) => {
            setCc(value)
            onCcChange(value)
          }}
          onReplyToChange={(value) => {
            setReplyTo(value)
            onReplyToChange(value)
          }}
          onClose={vi.fn()}
          onSend={onSend}
        />
      )
    }

    render(
      <Wrapper />
    )

    expect(screen.getByRole('heading', { name: 'Preview Reviewer Email' })).toBeInTheDocument()
    expect(screen.getByDisplayValue('Invitation to Review - Journal One')).toBeInTheDocument()
    expect(screen.getByText(/本次只会发送测试\/预览邮件/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Plain Text')).toHaveValue(
      'Hello Review Link (https://example.com/review/invite?token=abc)'
    )
    expect(screen.getByLabelText('Plain Text')).toHaveAttribute('readonly')

    fireEvent.change(screen.getByLabelText('Subject'), { target: { value: 'Custom subject' } })
    expect(screen.getByDisplayValue('Custom subject')).toBeInTheDocument()

    fireEvent.change(screen.getByTestId('reviewer-email-compose-editor'), {
      target: { value: '<p>Updated <strong>body</strong> <a href="https://example.com/next">Go</a></p>' },
    })
    expect(screen.getByLabelText('Plain Text')).toHaveValue('Updated body Go (https://example.com/next)')

    fireEvent.change(screen.getByLabelText('Recipient'), { target: { value: 'owner@example.com' } })
    expect(onRecipientEmailChange).toHaveBeenCalledWith('owner@example.com')

    fireEvent.change(screen.getByLabelText('CC'), { target: { value: 'board@example.com, office@example.org' } })
    expect(onCcChange).toHaveBeenCalledWith('board@example.com, office@example.org')

    fireEvent.change(screen.getByLabelText('Reply-To'), { target: { value: 'reply@example.org' } })
    expect(onReplyToChange).toHaveBeenCalledWith('reply@example.org')
  })
})
