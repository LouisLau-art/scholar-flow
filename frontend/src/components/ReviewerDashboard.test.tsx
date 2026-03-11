import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { vi, beforeEach, afterEach, describe, it, expect } from 'vitest'
import ReviewerDashboard, { REVIEW_ATTACHMENT_ACCEPT } from '@/components/ReviewerDashboard'

const pushMock = vi.fn()

vi.mock('@/services/auth', () => ({
  authService: {
    getSession: vi.fn().mockResolvedValue({
      user: { id: 'user-1' },
      access_token: 'token',
    }),
    getAccessToken: vi.fn().mockResolvedValue('token'),
  },
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}))

vi.mock('sonner', () => ({
  toast: {
    loading: vi.fn(() => 'toast-id'),
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('ReviewerDashboard', () => {
  beforeEach(() => {
    pushMock.mockReset()
    globalThis.fetch = vi.fn(async (input: any) => {
      const url = typeof input === 'string' ? input : input?.url

      if (String(url).startsWith('/api/v1/reviews/my-tasks')) {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: [
              {
                id: 'assign-1',
                manuscript_id: 'ms-1',
                manuscripts: {
                  title: 'Test Paper',
                  abstract: 'Test abstract',
                  file_path: 'manuscripts/ms-1.pdf',
                },
              },
            ],
          }),
        } as any
      }

      if (String(url).startsWith('/api/v1/reviews/my-history')) {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: [
              {
                assignment_id: 'history-1',
                manuscript_id: 'ms-history-1',
                manuscript_title: 'Archived Review',
                manuscript_abstract: 'Archived abstract',
                assignment_state: 'submitted',
                round_number: 2,
                invited_at: '2026-03-11T08:00:00+00:00',
                accepted_at: '2026-03-11T08:30:00+00:00',
                due_at: '2026-03-18T00:00:00+00:00',
                report_submitted_at: '2026-03-11T09:00:00+00:00',
                comments_for_author: 'Looks solid.',
                confidential_comments_to_editor: 'Keep an eye on the methods section.',
                email_events: [
                  {
                    status: 'sent',
                    event_type: 'invitation',
                    template_name: 'standard_invitation',
                    created_at: '2026-03-11T08:00:00+00:00',
                  },
                ],
              },
            ],
          }),
        } as any
      }

      if (String(url).startsWith('/api/v1/manuscripts/ms-1/pdf-signed')) {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: { signed_url: 'https://example.com/test.pdf' },
          }),
        } as any
      }

      return {
        ok: true,
        json: async () => ({ success: true }),
      } as any
    }) as any
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('allows Word reviewer attachments in the shared accept list', () => {
    expect(REVIEW_ATTACHMENT_ACCEPT).toContain('.pdf')
    expect(REVIEW_ATTACHMENT_ACCEPT).toContain('.doc')
    expect(REVIEW_ATTACHMENT_ACCEPT).toContain('.docx')
    expect(REVIEW_ATTACHMENT_ACCEPT).toContain('application/msword')
    expect(REVIEW_ATTACHMENT_ACCEPT).toContain(
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
  })

  it('opens preview modal and requests signed url', async () => {
    render(<ReviewerDashboard />)

    const openButton = await screen.findByRole('button', { name: /read full text/i })
    fireEvent.click(openButton)

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/v1/manuscripts/ms-1/pdf-signed',
        expect.objectContaining({
          headers: expect.objectContaining({ Authorization: 'Bearer token' }),
        })
      )
    })

    expect(await screen.findByTitle('PDF Preview')).toBeInTheDocument()
  })

  it('opens reviewer workspace using assignment_id when task rows are normalized payloads', async () => {
    globalThis.fetch = vi.fn(async (input: any) => {
      const url = typeof input === 'string' ? input : input?.url

      if (String(url).startsWith('/api/v1/reviews/my-tasks')) {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: [
              {
                assignment_id: 'assign-from-assignment-id',
                manuscript_id: 'ms-2',
                manuscript_title: 'Normalized Task',
                manuscript_abstract: 'Normalized abstract',
                assignment_status: 'accepted',
              },
            ],
          }),
        } as any
      }

      if (String(url) === '/api/v1/reviewer/assignments/assign-from-assignment-id/session') {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: { redirect_url: '/reviewer/workspace/assign-from-assignment-id' },
          }),
        } as any
      }

      return {
        ok: true,
        json: async () => ({ success: true }),
      } as any
    }) as any

    render(<ReviewerDashboard />)

    const startButton = await screen.findByRole('button', { name: /start review/i })
    fireEvent.click(startButton)

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/v1/reviewer/assignments/assign-from-assignment-id/session',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({ Authorization: 'Bearer token' }),
        })
      )
    })

    expect(pushMock).toHaveBeenCalledWith('/reviewer/workspace/assign-from-assignment-id')
  })

  it('uses backend redirect_url when reviewer must return to invite decision page', async () => {
    globalThis.fetch = vi.fn(async (input: any) => {
      const url = typeof input === 'string' ? input : input?.url

      if (String(url).startsWith('/api/v1/reviews/my-tasks')) {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: [
              {
                assignment_id: 'assign-needs-accept',
                manuscript_id: 'ms-3',
                manuscript_title: 'Needs Acceptance',
                manuscript_abstract: 'Reviewer must accept first',
                assignment_status: 'pending',
                accepted_at: null,
              },
            ],
          }),
        } as any
      }

      if (String(url) === '/api/v1/reviewer/assignments/assign-needs-accept/session') {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: { redirect_url: '/review/invite?assignment_id=assign-needs-accept' },
          }),
        } as any
      }

      return {
        ok: true,
        json: async () => ({ success: true }),
      } as any
    }) as any

    render(<ReviewerDashboard />)

    const startButton = await screen.findByRole('button', { name: /start review/i })
    fireEvent.click(startButton)

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith('/review/invite?assignment_id=assign-needs-accept')
    })
  })

  it('does not navigate when session response omits redirect_url', async () => {
    const { toast } = await import('sonner')

    globalThis.fetch = vi.fn(async (input: any) => {
      const url = typeof input === 'string' ? input : input?.url

      if (String(url).startsWith('/api/v1/reviews/my-tasks')) {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: [
              {
                assignment_id: 'assign-missing-redirect',
                manuscript_id: 'ms-4',
                manuscript_title: 'Missing Redirect',
                manuscript_abstract: 'Backend must provide redirect_url',
                assignment_status: 'pending',
              },
            ],
          }),
        } as any
      }

      if (String(url) === '/api/v1/reviewer/assignments/assign-missing-redirect/session') {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: {},
          }),
        } as any
      }

      return {
        ok: true,
        json: async () => ({ success: true }),
      } as any
    }) as any

    render(<ReviewerDashboard />)

    const startButton = await screen.findByRole('button', { name: /start review/i })
    fireEvent.click(startButton)

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to determine next reviewer step.', { id: 'toast-id' })
    })
    expect(pushMock).not.toHaveBeenCalled()
  })

  it('renders reviewer history and shows read-only archived details', async () => {
    render(<ReviewerDashboard />)

    expect(await screen.findByText('My Review History')).toBeInTheDocument()
    expect(await screen.findByText('Archived Review')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /view details/i })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /view details/i }))

    expect(await screen.findByText('Comments for Authors')).toBeInTheDocument()
    expect(screen.getByText('Looks solid.')).toBeInTheDocument()
    expect(screen.getByText('Keep an eye on the methods section.')).toBeInTheDocument()
    expect(screen.getByText('Communication Timeline')).toBeInTheDocument()
    expect(screen.getByText('Invitation email processed')).toBeInTheDocument()
  })

  it('opens submitted review from history through the reviewer session bridge', async () => {
    globalThis.fetch = vi.fn(async (input: any) => {
      const url = typeof input === 'string' ? input : input?.url

      if (String(url).startsWith('/api/v1/reviews/my-tasks')) {
        return {
          ok: true,
          json: async () => ({ success: true, data: [] }),
        } as any
      }

      if (String(url).startsWith('/api/v1/reviews/my-history')) {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: [
              {
                assignment_id: 'history-submitted-1',
                manuscript_id: 'ms-history-submitted',
                manuscript_title: 'Submitted Review History',
                assignment_state: 'submitted',
                report_submitted_at: '2026-03-11T09:00:00+00:00',
              },
            ],
          }),
        } as any
      }

      if (String(url) === '/api/v1/reviewer/assignments/history-submitted-1/session') {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: { redirect_url: '/reviewer/workspace/history-submitted-1' },
          }),
        } as any
      }

      return {
        ok: true,
        json: async () => ({ success: true }),
      } as any
    }) as any

    render(<ReviewerDashboard />)

    const openButton = await screen.findByRole('button', { name: /view submitted review/i })
    fireEvent.click(openButton)

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/v1/reviewer/assignments/history-submitted-1/session',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({ Authorization: 'Bearer token' }),
        })
      )
    })
    expect(pushMock).toHaveBeenCalledWith('/reviewer/workspace/history-submitted-1')
  })
})
