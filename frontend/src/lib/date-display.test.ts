import { describe, expect, it } from 'vitest'

import { formatDateLocal, formatDateTimeLocal } from '@/lib/date-display'

describe('date-display', () => {
  it('formats dates with a fixed Asia/Shanghai timezone', () => {
    expect(formatDateLocal('2026-03-10T23:30:00Z')).toBe('2026/03/11')
  })

  it('formats date-times with a fixed Asia/Shanghai timezone', () => {
    expect(formatDateTimeLocal('2026-03-10T23:30:00Z')).toBe('2026/03/11 07:30')
  })
})
