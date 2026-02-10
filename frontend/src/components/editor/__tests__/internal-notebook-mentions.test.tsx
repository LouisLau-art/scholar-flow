import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { InternalNotebook } from '@/components/editor/InternalNotebook'
import { EditorApi } from '@/services/editorApi'

vi.mock('@/services/editorApi', () => ({
  EditorApi: {
    getInternalComments: vi.fn(),
    postInternalCommentWithMentions: vi.fn(),
    listInternalStaff: vi.fn(),
  },
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('InternalNotebook mentions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(EditorApi.getInternalComments as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      data: [],
    })
    ;(EditorApi.listInternalStaff as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      data: [
        { id: 'u1', full_name: 'Alice Editor', email: 'alice@example.com' },
        { id: 'u2', full_name: 'Bob Editor', email: 'bob@example.com' },
      ],
    })
    ;(EditorApi.postInternalCommentWithMentions as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      data: {
        id: 'c1',
        manuscript_id: 'm1',
        content: 'Please help',
        created_at: '2026-02-09T10:00:00Z',
        mention_user_ids: ['u1', 'u2'],
        user: { full_name: 'Editor A', email: 'editor@example.com' },
      },
    })
  })

  it('submits mention_user_ids and renders mention chips', async () => {
    render(<InternalNotebook manuscriptId="m1" />)

    await waitFor(() => {
      expect(EditorApi.getInternalComments).toHaveBeenCalledWith('m1')
      expect(EditorApi.listInternalStaff).toHaveBeenCalled()
    })

    fireEvent.click(screen.getByLabelText('Mention Alice Editor'))
    fireEvent.click(screen.getByLabelText('Mention Bob Editor'))

    fireEvent.change(screen.getByPlaceholderText(/Type an internal note/i), { target: { value: 'Please help' } })
    fireEvent.click(screen.getByLabelText('Post internal note'))

    await waitFor(() => {
      expect(EditorApi.postInternalCommentWithMentions).toHaveBeenCalledWith('m1', {
        content: 'Please help',
        mention_user_ids: ['u1', 'u2'],
      })
    })

    expect(screen.getByTestId('notebook-mentions')).toBeInTheDocument()
    expect(screen.getByText('@Alice Editor')).toBeInTheDocument()
    expect(screen.getByText('@Bob Editor')).toBeInTheDocument()
  })
})
