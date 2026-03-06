import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ReviewInvitePage from './page'

const { pushMock, searchParamsMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  searchParamsMock: new URLSearchParams('assignment_id=assign-1'),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
  useSearchParams: () => searchParamsMock,
}))

describe('ReviewInvitePage', () => {
  beforeEach(() => {
    pushMock.mockReset()
    globalThis.fetch = vi.fn(async (input: any) => {
      const url = typeof input === 'string' ? input : input?.url

      if (String(url) === '/api/v1/reviewer/assignments/assign-1/invite') {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: {
              assignment: {
                assignment_id: 'assign-1',
                status: 'invited',
                due_at: null,
                decline_reason: null,
                decline_note: null,
                timeline: {
                  invited_at: '2026-03-06T00:00:00Z',
                  opened_at: '2026-03-06T00:05:00Z',
                  accepted_at: null,
                  declined_at: null,
                  submitted_at: null,
                },
              },
              manuscript: {
                id: 'ms-1',
                title: 'Test Manuscript',
                abstract: 'Abstract text',
                journal_title: 'Journal A',
              },
              window: {
                min_due_date: '2026-03-08',
                max_due_date: '2026-03-20',
                default_due_date: '2026-03-12',
              },
              can_open_workspace: false,
            },
          }),
        } as any
      }

      if (String(url) === '/api/v1/reviews/magic/assignments/assign-1/pdf-signed') {
        return {
          ok: true,
          json: async () => ({
            success: true,
            data: {
              signed_url: 'https://example.com/manuscript.pdf',
            },
          }),
        } as any
      }

      return {
        ok: false,
        json: async () => ({ detail: 'Unexpected request' }),
      } as any
    }) as any
  })

  it('renders journal metadata and manuscript PDF preview for invite review surface', async () => {
    render(<ReviewInvitePage />)

    expect(await screen.findByText('Test Manuscript')).toBeInTheDocument()
    expect((await screen.findAllByText('Journal A')).length).toBeGreaterThan(0)

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/reviews/magic/assignments/assign-1/pdf-signed')
    })

    expect(await screen.findByTitle('Manuscript PDF')).toBeInTheDocument()
  })
})
