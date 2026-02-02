import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { vi, beforeEach, afterEach, describe, it, expect } from 'vitest'
import ReviewerDashboard from '@/components/ReviewerDashboard'

const createSignedUrl = vi.fn().mockResolvedValue({
  data: { signedUrl: 'https://example.com/test.pdf' },
  error: null,
})

vi.mock('@/lib/supabase', () => ({
  supabase: {
    storage: {
      from: vi.fn(() => ({
        createSignedUrl,
      })),
    },
  },
}))

vi.mock('@/services/auth', () => ({
  authService: {
    getSession: vi.fn().mockResolvedValue({
      user: { id: 'user-1' },
      access_token: 'token',
    }),
    getAccessToken: vi.fn().mockResolvedValue('token'),
  },
}))

describe('ReviewerDashboard', () => {
  beforeEach(() => {
    createSignedUrl.mockClear()
    globalThis.fetch = vi.fn().mockResolvedValue({
      json: vi.fn().mockResolvedValue({
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
    }) as any
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('opens preview modal and requests signed url', async () => {
    render(<ReviewerDashboard />)

    const openButton = await screen.findByRole('button', { name: /read full text/i })
    fireEvent.click(openButton)

    await waitFor(() => {
      expect(createSignedUrl).toHaveBeenCalledWith('manuscripts/ms-1.pdf', 60 * 5)
    })

    expect(await screen.findByTitle('PDF Preview')).toBeInTheDocument()
  })
})
