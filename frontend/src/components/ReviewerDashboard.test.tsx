import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { vi, beforeEach, afterEach, describe, it, expect } from 'vitest'
import ReviewerDashboard from '@/components/ReviewerDashboard'

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
})
