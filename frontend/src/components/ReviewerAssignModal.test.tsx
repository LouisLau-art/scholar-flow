import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import ReviewerAssignModal from '@/components/ReviewerAssignModal'

vi.mock('@/services/auth', () => ({
  authService: {
    getAccessToken: vi.fn().mockResolvedValue('token'),
  },
}))

describe('ReviewerAssignModal AI Recommendations', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn((url: any) => {
      if (String(url).includes('/api/v1/editor/available-reviewers')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: [] }),
        }) as any
      }
      if (String(url).includes('/api/v1/matchmaking/analyze')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              data: {
                insufficient_data: false,
                message: null,
                recommendations: [
                  {
                    reviewer_id: 'r-1',
                    name: 'Expert',
                    email: 'expert@example.com',
                    match_score: 0.9,
                  },
                ],
              },
            }),
        }) as any
      }
      return Promise.reject(new Error(`unexpected url ${url}`))
    }) as any
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('runs AI analysis and invites from recommendation list', async () => {
    const onAssign = vi.fn()
    const onClose = vi.fn()

    render(
      <ReviewerAssignModal
        isOpen={true}
        onClose={onClose}
        onAssign={onAssign}
        manuscriptId="ms-1"
      />
    )

    const analyzeBtn = await screen.findByTestId('ai-analyze')
    fireEvent.click(analyzeBtn)

    expect(await screen.findByTestId('ai-recommendations')).toBeInTheDocument()

    const inviteBtn = await screen.findByTestId('ai-invite-r-1')
    fireEvent.click(inviteBtn)

    const assignBtn = await screen.findByTestId('reviewer-assign')
    fireEvent.click(assignBtn)

    await waitFor(() => {
      expect(onAssign).toHaveBeenCalledWith(['r-1'])
      expect(onClose).toHaveBeenCalled()
    })
  })
})

