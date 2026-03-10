import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { DatePicker } from '@/components/ui/date-picker'

vi.mock('@/components/ui/calendar', () => ({
  Calendar: ({ onSelect }: { onSelect?: (date?: Date) => void }) => (
    <button type="button" onClick={() => onSelect?.(new Date(2026, 2, 17))}>
      Mock Calendar Day
    </button>
  ),
}))

describe('DatePicker', () => {
  it('supports closing by clicking the trigger again', () => {
    const handleChange = vi.fn()

    render(<DatePicker value="2026-03-17" onChange={handleChange} />)

    const trigger = screen.getByRole('button', { name: '2026-03-17' })
    fireEvent.click(trigger)
    expect(screen.getByRole('button', { name: 'Mock Calendar Day' })).toBeInTheDocument()

    fireEvent.click(trigger)
    expect(screen.queryByRole('button', { name: 'Mock Calendar Day' })).not.toBeInTheDocument()
  })

  it('closes after selecting a date', () => {
    const handleChange = vi.fn()

    render(<DatePicker value="2026-03-17" onChange={handleChange} />)

    fireEvent.click(screen.getByRole('button', { name: '2026-03-17' }))
    fireEvent.click(screen.getByRole('button', { name: 'Mock Calendar Day' }))

    expect(handleChange).toHaveBeenCalledWith('2026-03-17')
    expect(screen.queryByRole('button', { name: 'Mock Calendar Day' })).not.toBeInTheDocument()
  })
})
