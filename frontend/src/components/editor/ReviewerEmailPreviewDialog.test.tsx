import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { ReviewerEmailPreviewData } from '@/app/(admin)/editor/manuscript/[id]/types'

import { ReviewerEmailPreviewDialog } from './ReviewerEmailPreviewDialog'

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
  subject: 'Invitation to Review - Journal One',
  html: '<p>Hello reviewer</p>',
  text: 'Hello reviewer',
}

describe('ReviewerEmailPreviewDialog', () => {
  it('renders preview content and override warning when recipient changes', () => {
    const onRecipientEmailChange = vi.fn()
    render(
      <ReviewerEmailPreviewDialog
        open
        loading={false}
        sending={false}
        preview={preview}
        recipientEmail="assistant@example.com"
        onRecipientEmailChange={onRecipientEmailChange}
        onClose={vi.fn()}
        onSend={vi.fn()}
      />
    )

    expect(screen.getByRole('heading', { name: 'Preview Reviewer Email' })).toBeInTheDocument()
    expect(screen.getByDisplayValue('Invitation to Review - Journal One')).toBeInTheDocument()
    expect(screen.getByText(/本次只会发送测试\/预览邮件/i)).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Recipient'), { target: { value: 'owner@example.com' } })
    expect(onRecipientEmailChange).toHaveBeenCalledWith('owner@example.com')
  })
})
