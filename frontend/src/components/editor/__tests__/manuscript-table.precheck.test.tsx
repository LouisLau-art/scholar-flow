import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ManuscriptTable, type ProcessRow } from '@/components/editor/ManuscriptTable'

vi.mock('next/link', () => ({
  default: ({ children, href, ...rest }: { children: any; href: string }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}))

vi.mock('@/components/editor/BindingOwnerDropdown', () => ({
  BindingOwnerDropdown: () => <span data-testid="binding-owner-dropdown" />,
}))

vi.mock('@/components/editor/ManuscriptActions', () => ({
  ManuscriptActions: () => <span data-testid="manuscript-actions" />,
}))

describe('ManuscriptTable precheck rendering', () => {
  it('shows precheck stage + role and current assignee for pre_check manuscript', () => {
    const rows: ProcessRow[] = [
      {
        id: 'ms-1',
        status: 'pre_check',
        pre_check_status: 'technical',
        current_role: 'assistant_editor',
        current_assignee: { id: 'ae-1', full_name: 'Alice Editor', email: 'alice@example.com' },
        journals: { title: 'Journal A' },
        created_at: '2026-02-09T01:00:00Z',
        updated_at: '2026-02-09T02:00:00Z',
      },
    ]

    render(<ManuscriptTable rows={rows} />)

    expect(screen.getByText(/Pre-check:\s*technical \(assistant editor\)/i)).toBeInTheDocument()
    expect(screen.getByText('Alice Editor')).toBeInTheDocument()
  })

  it('shows placeholder when row is not in pre_check status', () => {
    const rows: ProcessRow[] = [
      {
        id: 'ms-2',
        status: 'under_review',
        pre_check_status: 'technical',
        current_role: 'assistant_editor',
        journals: { title: 'Journal B' },
        created_at: '2026-02-09T03:00:00Z',
        updated_at: '2026-02-09T04:00:00Z',
      },
    ]

    render(<ManuscriptTable rows={rows} />)

    const row = screen.getByText('ms-2').closest('tr')
    expect(row).not.toBeNull()
    expect(within(row as HTMLTableRowElement).queryByText(/Pre-check:\s*technical \(assistant editor\)/i)).not.toBeInTheDocument()
    expect(within(row as HTMLTableRowElement).getAllByText('—').length).toBeGreaterThan(0)
  })
})
