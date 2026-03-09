import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ReviewerInviteSummaryCard, ReviewerManagementCard } from '@/app/(admin)/editor/manuscript/[id]/detail-sections'

describe('Reviewer summary cards', () => {
  it('shows loading state before deferred context is loaded', () => {
    render(<ReviewerInviteSummaryCard reviewerInvites={[]} deferredLoaded={false} deferredLoading />)

    expect(screen.getByText('Reviewer summary loading...')).toBeInTheDocument()
    expect(screen.queryByText('No reviewers assigned yet.')).not.toBeInTheDocument()
  })

  it('shows snapshot counts after deferred context has loaded', () => {
    render(
      <ReviewerInviteSummaryCard
        reviewerInvites={[
          { id: 'ra-1', reviewer_name: 'A', status: 'selected' },
          { id: 'ra-2', reviewer_name: 'B', status: 'invited', invited_at: '2026-03-05T00:00:00Z' },
          { id: 'ra-3', reviewer_name: 'C', status: 'accepted', accepted_at: '2026-03-06T00:00:00Z' },
          { id: 'ra-4', reviewer_name: 'D', status: 'declined', declined_at: '2026-03-07T00:00:00Z' },
        ]}
        deferredLoaded
        deferredLoading={false}
      />
    )

    expect(screen.getByText('Selected')).toBeInTheDocument()
    expect(screen.getByText('Invited')).toBeInTheDocument()
    expect(screen.getByText('Accepted')).toBeInTheDocument()
    expect(screen.getByText('Declined')).toBeInTheDocument()
    expect(screen.getByText('4 total reviewer records')).toBeInTheDocument()
  })

  it('renders reviewer management table with outreach actions', () => {
    const onRetry = vi.fn()
    const onSendTemplateEmail = vi.fn()
    const onTemplateChange = vi.fn()
    const onOpenHistory = vi.fn()

    render(
      <ReviewerManagementCard
        reviewerInvites={[
          {
            id: 'ra-1',
            reviewer_id: 'reviewer-1',
            reviewer_name: 'Reviewer User',
            reviewer_email: 'reviewer@example.com',
            status: 'accepted',
            accepted_at: '2026-03-06T00:00:00Z',
            due_at: '2026-03-12T00:00:00Z',
            latest_email_status: 'sent',
            latest_email_at: '2026-03-05T00:00:00Z',
            added_by_name: 'Selector User',
            added_via: 'editor_selection',
            invited_by_name: 'Inviter User',
            invited_via: 'template_invitation',
            email_events: [
              {
                status: 'sent',
                event_type: 'invitation',
                created_at: '2026-03-05T00:00:00Z',
              },
            ],
          },
        ]}
        deferredLoaded
        deferredLoading={false}
        onRetry={onRetry}
        canManageReviewerOutreach
        sendingAssignmentId={null}
        emailTemplateOptions={[
          { template_key: 'reviewer-invite', display_name: 'Invitation', scene: 'reviewer_assignment', event_type: 'invitation' },
        ]}
        selectedTemplateByAssignment={{ 'ra-1': 'reviewer-invite' }}
        onTemplateChange={onTemplateChange}
        onSendTemplateEmail={onSendTemplateEmail}
        onOpenHistory={onOpenHistory}
      />
    )

    expect(screen.getByText('Reviewer Management')).toBeInTheDocument()
    expect(screen.getByText('Reviewer User')).toBeInTheDocument()
    expect(screen.getByText('Invite Status')).toBeInTheDocument()
    expect(screen.getByText('Review Status')).toBeInTheDocument()
    expect(screen.getByText(/Delivery:/i)).toBeInTheDocument()
    expect(screen.getByText(/Delivery: sent/i)).toBeInTheDocument()
    expect(screen.getByText(/Selected by Selector User via Editor shortlist/i)).toBeInTheDocument()
    expect(screen.getByText(/Invited by Inviter User via Invitation template/i)).toBeInTheDocument()
    expect(screen.getByText(/Invitation sent/i)).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('reviewer-history-ra-1'))
    expect(onOpenHistory).toHaveBeenCalledTimes(1)
  })

  it('shows retry action when deferred context fails', () => {
    const onRetry = vi.fn()
    render(
      <ReviewerManagementCard
        reviewerInvites={[]}
        deferredLoaded={false}
        deferredLoading={false}
        loadError="Deferred detail context loading timed out."
        onRetry={onRetry}
      />
    )

    expect(screen.getByText('Deferred detail context loading timed out.')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('reviewer-management-retry'))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})
