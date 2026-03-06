import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import SetPasswordPage from './page'

const { pushMock, refreshMock, updateUserMock, getSessionMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  refreshMock: vi.fn(),
  updateUserMock: vi.fn(),
  getSessionMock: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: pushMock,
    refresh: refreshMock,
  }),
}))

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      updateUser: updateUserMock,
      getSession: getSessionMock,
    },
  },
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('SetPasswordPage', () => {
  beforeEach(() => {
    pushMock.mockReset()
    refreshMock.mockReset()
    updateUserMock.mockReset()
    getSessionMock.mockReset()
    getSessionMock.mockResolvedValue({
      data: {
        session: {
          user: {
            id: 'reviewer-1',
            email: 'reviewer@example.com',
          },
        },
      },
    })
    updateUserMock.mockResolvedValue({ error: null })
  })

  it('updates password and redirects to dashboard', async () => {
    render(<SetPasswordPage />)

    fireEvent.change(screen.getByLabelText('New password'), {
      target: { value: 'VerySecurePassword123!' },
    })
    fireEvent.change(screen.getByLabelText('Confirm password'), {
      target: { value: 'VerySecurePassword123!' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Set password' }))

    await waitFor(() => {
      expect(updateUserMock).toHaveBeenCalledWith({ password: 'VerySecurePassword123!' })
    })
    expect(pushMock).toHaveBeenCalledWith('/dashboard')
    expect(refreshMock).toHaveBeenCalled()
  })
})
