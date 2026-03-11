import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { CreateUserDialog } from '@/components/admin/CreateUserDialog'

describe('CreateUserDialog', () => {
  it('点击 Cancel 可关闭弹窗', () => {
    const onClose = vi.fn()
    render(
      <CreateUserDialog
        isOpen
        onClose={onClose}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('点击右上角 Close 可关闭弹窗', () => {
    const onClose = vi.fn()
    render(
      <CreateUserDialog
        isOpen
        onClose={onClose}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('提交进行中仍允许关闭弹窗', async () => {
    const onClose = vi.fn()
    const onConfirm = vi.fn(
      () =>
        new Promise<void>(() => {
          // keep pending to simulate network hang
        })
    )

    render(<CreateUserDialog isOpen onClose={onClose} onConfirm={onConfirm} />)

    fireEvent.change(screen.getByPlaceholderText('colleague@example.com'), {
      target: { value: 'admin@example.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('John Doe'), {
      target: { value: 'Admin User' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Create Account' }))

    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledTimes(1)
    })

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('可选择 Academic Editor 角色创建账号', async () => {
    render(
      <CreateUserDialog
        isOpen
        onClose={vi.fn()}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    )

    fireEvent.click(screen.getByRole('combobox'))

    expect((await screen.findAllByText('Academic Editor')).length).toBeGreaterThan(0)
  })
})
