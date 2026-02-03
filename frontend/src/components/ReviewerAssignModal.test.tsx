import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { within } from '@testing-library/react'
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
      if (String(url).includes('/api/v1/manuscripts/articles/')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              data: {
                id: 'ms-1',
                owner_id: 'u-owner',
              },
            }),
        }) as any
      }
      if (String(url).includes('/api/v1/editor/internal-staff')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              data: [
                { id: 'u-owner', full_name: 'Owner User', email: 'owner@test.com', roles: ['editor'] },
              ],
            }),
        }) as any
      }
      if (String(url).includes('/api/v1/reviews/assignments/')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: [
              {
                id: 'a-1',
                status: 'pending',
                due_at: null,
                round_number: 1,
                reviewer_id: 'r-assigned',
                reviewer_name: 'Assigned Reviewer',
                reviewer_email: 'assigned@test.com',
              },
            ],
          }),
        }) as any
      }
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
      if (String(url).includes('/api/v1/admin/users')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: [
              { id: 'r-assigned', full_name: 'Assigned Reviewer', email: 'assigned@test.com' },
              { id: 'r-manual', full_name: 'Manual Reviewer', email: 'manual@test.com' }
            ],
            total: 1,
            page: 1,
            per_page: 100
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

    const ownerSelect = (await screen.findByTestId('owner-select')) as HTMLSelectElement
    await waitFor(() => {
      expect(ownerSelect.value).toBe('u-owner')
    })

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

  it('allows manual search and assignment', async () => {
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

    const ownerSelect = (await screen.findByTestId('owner-select')) as HTMLSelectElement
    await waitFor(() => {
      expect(ownerSelect.value).toBe('u-owner')
    })

    // Initial load fetches reviewers
    expect(await screen.findByText('Manual Reviewer')).toBeInTheDocument()

    // Search (updates state, triggers fetch)
    const searchInput = screen.getByTestId('reviewer-search')
    fireEvent.change(searchInput, { target: { value: 'Manual' } })

    // Select manual reviewer
    const reviewerRow = await screen.findByText('Manual Reviewer')
    fireEvent.click(reviewerRow)

    const assignBtn = await screen.findByTestId('reviewer-assign')
    fireEvent.click(assignBtn)

    await waitFor(() => {
      expect(onAssign).toHaveBeenCalledWith(['r-manual'])
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('pins assigned reviewers and shows as selected', async () => {
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

    const list = await screen.findByTestId('reviewer-list')
    const firstRow = list.firstChild as HTMLElement
    expect(firstRow).toBeTruthy()

    // 置顶：第一个就是已分配 reviewer
    expect(firstRow.getAttribute('data-testid')).toBe('reviewer-row-r-assigned')
    expect(within(list).getByText('Assigned Reviewer')).toBeInTheDocument()
    expect(within(list).getByText('Assigned')).toBeInTheDocument()
  })
})
