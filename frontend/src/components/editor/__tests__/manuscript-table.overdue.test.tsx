import { render, screen } from '@testing-library/react'
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

describe('ManuscriptTable overdue markers', () => {
  it('renders overdue badge with overdue task count', () => {
    const rows: ProcessRow[] = [
      {
        id: 'ms-overdue',
        status: 'under_review',
        journals: { title: 'Journal A' },
        created_at: '2026-02-09T00:00:00Z',
        updated_at: '2026-02-09T00:00:00Z',
        is_overdue: true,
        overdue_tasks_count: 2,
      },
    ]

    render(<ManuscriptTable rows={rows} />)

    expect(screen.getByText('Overdue')).toBeInTheDocument()
    expect(screen.getByText('(2)')).toBeInTheDocument()
  })

  it('renders on track label when manuscript has no overdue tasks', () => {
    const rows: ProcessRow[] = [
      {
        id: 'ms-ontime',
        status: 'under_review',
        journals: { title: 'Journal A' },
        created_at: '2026-02-09T00:00:00Z',
        updated_at: '2026-02-09T00:00:00Z',
        is_overdue: false,
        overdue_tasks_count: 0,
      },
    ]

    render(<ManuscriptTable rows={rows} />)

    expect(screen.getByText('On track')).toBeInTheDocument()
  })
})
