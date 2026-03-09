import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ReviewerAssignmentSearch } from '@/components/editor/ReviewerAssignmentSearch'

vi.mock('@/services/auth', () => ({
  authService: {
    getAccessToken: vi.fn().mockResolvedValue('token'),
  },
}))

vi.mock('next/dynamic', () => ({
  default: () => {
    return function MockReviewerAssignModal(props: any) {
      if (!props.isOpen) return null
      return (
        <button
          type="button"
          data-testid="mock-assign-modal"
          onClick={() =>
            props.onAssign(['reviewer-1'], {
              overrides: [{ reviewerId: 'reviewer-1', reason: 'Need continuity' }],
            })
          }
        >
          Trigger Assign
        </button>
      )
    }
  },
}))

describe('ReviewerAssignmentSearch', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    fetchMock.mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ success: true }),
    })
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('sends cooldown override payload when modal returns override reasons', async () => {
    render(<ReviewerAssignmentSearch manuscriptId="ms-1" />)

    fireEvent.click(screen.getByRole('button', { name: 'Manage Reviewers' }))
    fireEvent.click(await screen.findByTestId('mock-assign-modal'))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    const [, options] = fetchMock.mock.calls[0]
    expect(options?.method).toBe('POST')
    expect(options?.headers).toMatchObject({
      'Content-Type': 'application/json',
      Authorization: 'Bearer token',
    })
    expect(JSON.parse(String(options?.body))).toMatchObject({
      manuscript_id: 'ms-1',
      reviewer_id: 'reviewer-1',
      override_cooldown: true,
      override_reason: 'Need continuity',
    })
  })
})
