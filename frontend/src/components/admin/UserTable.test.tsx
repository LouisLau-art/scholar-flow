import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { UserTable } from '@/components/admin/UserTable'
import type { User } from '@/types/user'

const makeUsers = (count: number): User[] =>
  Array.from({ length: count }, (_, index) => ({
    id: `user-${index + 1}`,
    email: `user${index + 1}@example.com`,
    full_name: `User ${index + 1}`,
    roles: ['author'],
    created_at: '2026-03-01T00:00:00Z',
    is_verified: true,
  }))

describe('UserTable', () => {
  it('renders richer pagination controls instead of only previous next', () => {
    render(
      <UserTable
        users={makeUsers(25)}
        isLoading={false}
        page={3}
        perPage={25}
        total={260}
        onPageChange={vi.fn()}
        onPerPageChange={vi.fn()}
        onEdit={vi.fn()}
        onResetPassword={vi.fn()}
      />
    )

    expect(screen.getByRole('button', { name: '首页' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '上一页' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '下一页' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '末页' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '1' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '3' })).toBeInTheDocument()
  })

  it('notifies page size changes', () => {
    const onPerPageChange = vi.fn()

    render(
      <UserTable
        users={makeUsers(25)}
        isLoading={false}
        page={1}
        perPage={25}
        total={260}
        onPageChange={vi.fn()}
        onPerPageChange={onPerPageChange}
        onEdit={vi.fn()}
        onResetPassword={vi.fn()}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: '50 / 页' }))

    expect(onPerPageChange).toHaveBeenCalledWith(50)
  })

  it('jumps to target pages using first last and numbered buttons', () => {
    const onPageChange = vi.fn()

    render(
      <UserTable
        users={makeUsers(25)}
        isLoading={false}
        page={3}
        perPage={25}
        total={260}
        onPageChange={onPageChange}
        onPerPageChange={vi.fn()}
        onEdit={vi.fn()}
        onResetPassword={vi.fn()}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: '首页' }))
    fireEvent.click(screen.getByRole('button', { name: '4' }))
    fireEvent.click(screen.getByRole('button', { name: '末页' }))

    expect(onPageChange).toHaveBeenNthCalledWith(1, 1)
    expect(onPageChange).toHaveBeenNthCalledWith(2, 4)
    expect(onPageChange).toHaveBeenNthCalledWith(3, 11)
  })

  it('renders academic editor role badge in user rows', () => {
    render(
      <UserTable
        users={[
          {
            ...makeUsers(1)[0],
            roles: ['academic_editor'],
          },
        ]}
        isLoading={false}
        page={1}
        perPage={25}
        total={1}
        onPageChange={vi.fn()}
        onPerPageChange={vi.fn()}
        onEdit={vi.fn()}
        onResetPassword={vi.fn()}
      />
    )

    expect(screen.getByText('academic_editor')).toBeInTheDocument()
  })
})
