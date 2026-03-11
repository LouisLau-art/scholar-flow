import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { UserRoleDialog } from '@/components/admin/UserRoleDialog'
import { adminJournalService } from '@/services/admin/journalService'
import { adminUserService } from '@/services/admin/userService'
import type { User } from '@/types/user'

vi.mock('@/services/admin/journalService', () => ({
  adminJournalService: {
    list: vi.fn(),
  },
}))

vi.mock('@/services/admin/userService', () => ({
  adminUserService: {
    listJournalScopes: vi.fn(),
  },
}))

const mockUser: User = {
  id: 'user-1',
  email: 'academic@example.com',
  full_name: 'Academic Editor',
  roles: ['academic_editor'],
  created_at: '2026-03-01T00:00:00Z',
  is_verified: true,
}

describe('UserRoleDialog', () => {
  it('renders academic editor role and requires journal scope for it', async () => {
    vi.mocked(adminJournalService.list).mockResolvedValue([
      { id: 'journal-1', title: 'Journal A' },
    ] as any)
    vi.mocked(adminUserService.listJournalScopes).mockResolvedValue([
      {
        id: 'scope-1',
        user_id: 'user-1',
        journal_id: 'journal-1',
        role: 'academic_editor',
        is_active: true,
        created_at: '2026-03-01T00:00:00Z',
        updated_at: '2026-03-01T00:00:00Z',
      },
    ] as any)

    render(
      <UserRoleDialog
        isOpen
        user={mockUser}
        onClose={vi.fn()}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    )

    expect(screen.getByRole('button', { name: /Academic Editor/i })).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Journal Scope (Required for ME/Academic/EIC)')).toBeInTheDocument()
    })

    expect(screen.getAllByText('Journal A').length).toBeGreaterThan(0)
  })

  it('passes academic editor journal scopes on confirm', async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined)
    vi.mocked(adminJournalService.list).mockResolvedValue([
      { id: 'journal-1', title: 'Journal A' },
    ] as any)
    vi.mocked(adminUserService.listJournalScopes).mockResolvedValue([] as any)

    render(
      <UserRoleDialog
        isOpen
        user={{
          ...mockUser,
          roles: ['author'],
        }}
        onClose={vi.fn()}
        onConfirm={onConfirm}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: /Academic Editor/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Journal A' })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Journal A' }))
    fireEvent.change(screen.getByPlaceholderText('Explain why this role/scope change is required...'), {
      target: { value: 'Bind academic editor scope for this journal.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledWith(
        'user-1',
        expect.arrayContaining(['author', 'academic_editor']),
        'Bind academic editor scope for this journal.',
        ['journal-1']
      )
    })
  })
})
