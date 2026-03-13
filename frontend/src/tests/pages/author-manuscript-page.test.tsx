import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AuthorManuscriptReviewsPage from '@/app/dashboard/author/manuscripts/[id]/page'
import { authService } from '@/services/auth'

vi.mock('@/services/auth', () => ({
  authService: {
    getAccessToken: vi.fn(),
  },
}))

vi.mock('@/components/layout/SiteHeader', () => ({
  default: () => <div data-testid="site-header">header</div>,
}))

describe('AuthorManuscriptReviewsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders submission email and corresponding authors from author context', async () => {
    ;(authService.getAccessToken as unknown as ReturnType<typeof vi.fn>).mockResolvedValue('token')

    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        success: true,
        data: {
          manuscript: {
            id: 'test-id',
            title: 'Author Context Manuscript',
            status: 'major_revision',
            status_label: 'Major Revision',
            created_at: '2026-03-13T12:00:00Z',
            updated_at: '2026-03-13T12:30:00Z',
            submission_email: 'delegate@example.com',
            author_contacts: [
              {
                name: 'Lead Author',
                email: 'lead.author@example.com',
                is_corresponding: true,
              },
              {
                name: 'Co Author',
                email: 'co.author@example.com',
                is_corresponding: false,
              },
            ],
          },
          files: {
            current_pdf_signed_url: null,
            word_manuscripts: [],
          },
          proofreading_task: null,
          timeline: [],
        },
      }),
    }))
    vi.stubGlobal('fetch', fetchMock)

    render(<AuthorManuscriptReviewsPage />)

    await waitFor(() => {
      expect(screen.getByText('Author Context Manuscript')).toBeInTheDocument()
    })

    expect(screen.getByText('Submission Email')).toBeInTheDocument()
    expect(screen.getByText('delegate@example.com')).toBeInTheDocument()
    expect(screen.getByText('Corresponding Author(s)')).toBeInTheDocument()
    expect(screen.getByText('Lead Author')).toBeInTheDocument()
    expect(screen.getByText('Corresponding Author Email(s)')).toBeInTheDocument()
    expect(screen.getByText('lead.author@example.com')).toBeInTheDocument()
  })
})
