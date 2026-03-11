import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { UserFilters } from '@/components/admin/UserFilters'

describe('UserFilters', () => {
  it('shows academic editor as a role filter option', async () => {
    render(
      <UserFilters
        search=""
        role=""
        includeTestProfiles={false}
        onSearchChange={vi.fn()}
        onRoleChange={vi.fn()}
        onIncludeTestProfilesChange={vi.fn()}
      />
    )

    fireEvent.click(screen.getByRole('combobox', { name: /Filter by role/i }))

    expect(await screen.findByText('Academic Editor')).toBeInTheDocument()
  })
})
