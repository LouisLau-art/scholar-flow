import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ResetPasswordDialog } from '@/components/admin/ResetPasswordDialog'
import type { User } from '@/types/user'

const mockUser: User = {
  id: 'user-1',
  email: 'user@example.com',
  full_name: 'Test User',
  roles: ['author'],
  created_at: '2026-03-06T00:00:00Z',
  is_verified: true,
}

describe('ResetPasswordDialog', () => {
  it('calls onClose when cancel button is clicked', () => {
    const onClose = vi.fn()
    const onConfirm = vi.fn().mockResolvedValue(undefined)

    render(<ResetPasswordDialog isOpen user={mockUser} onClose={onClose} onConfirm={onConfirm} />)

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when top-right close button is clicked', () => {
    const onClose = vi.fn()
    const onConfirm = vi.fn().mockResolvedValue(undefined)

    render(<ResetPasswordDialog isOpen user={mockUser} onClose={onClose} onConfirm={onConfirm} />)

    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
