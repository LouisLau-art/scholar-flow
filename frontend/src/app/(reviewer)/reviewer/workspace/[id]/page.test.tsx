import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ReviewerWorkspacePage from './page'

const { replaceMock, routerMock, toastErrorMock } = vi.hoisted(() => ({
  replaceMock: vi.fn(),
  routerMock: {
    replace: vi.fn(),
  },
  toastErrorMock: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'assign-redirect' }),
  useRouter: () => routerMock,
}))

vi.mock('sonner', () => ({
  toast: {
    error: toastErrorMock,
  },
}))

describe('ReviewerWorkspacePage', () => {
  beforeEach(() => {
    replaceMock.mockReset()
    routerMock.replace = replaceMock
    toastErrorMock.mockReset()
    globalThis.fetch = vi.fn(async () => ({
      ok: false,
      json: async () => ({
        detail: {
          code: 'INVITE_ACCEPT_REQUIRED',
          message: 'Please accept invitation first',
        },
      }),
    })) as unknown as typeof fetch
  })

  it('redirects back to invite surface when workspace access requires acceptance', async () => {
    render(<ReviewerWorkspacePage />)

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith('/review/invite?assignment_id=assign-redirect')
    })
  })

  it('renders larger long-form textareas for reviewer comments', async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        success: true,
        data: {
          manuscript: {
            id: 'm-1',
            title: 'Long Review Manuscript',
            abstract: 'Abstract',
            pdf_url: 'https://example.com/manuscript.pdf',
          },
          assignment: {
            id: 'assign-redirect',
            status: 'accepted',
            due_at: null,
            invited_at: null,
            opened_at: null,
            accepted_at: '2026-03-09T00:00:00Z',
            submitted_at: null,
            decline_reason: null,
          },
          review_report: {
            id: null,
            status: 'pending',
            comments_for_author: '',
            confidential_comments_to_editor: '',
            recommendation: 'minor_revision',
            attachments: [],
            submitted_at: null,
          },
          permissions: { can_submit: true, is_read_only: false },
          timeline: [],
        },
      }),
    })) as unknown as typeof fetch

    render(<ReviewerWorkspacePage />)

    const authorBox = await screen.findByLabelText('Comment to Authors')
    const editorBox = await screen.findByLabelText('Private note to Editor (optional)')
    const reviewCommentHeading = await screen.findByRole('heading', { name: 'Review Comment' })
    const timelineHeading = await screen.findByRole('heading', { name: 'Communication Timeline' })

    expect(authorBox).toHaveAttribute('rows', '16')
    expect(authorBox).toHaveClass('resize-y')
    expect(editorBox).toHaveAttribute('rows', '10')
    expect(editorBox).toHaveClass('resize-y')
    expect(
      reviewCommentHeading.compareDocumentPosition(timelineHeading) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy()
  })
})
