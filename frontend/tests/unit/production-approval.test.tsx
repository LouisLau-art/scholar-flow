import { describe, expect, it } from 'vitest'
import { canApproveProductionCycle } from '@/lib/production-utils'

describe('production approval guard', () => {
  it('allows approval only in author_confirmed status', () => {
    expect(canApproveProductionCycle('author_confirmed')).toBe(true)
    expect(canApproveProductionCycle('awaiting_author')).toBe(false)
    expect(canApproveProductionCycle('approved_for_publish')).toBe(false)
    expect(canApproveProductionCycle(undefined)).toBe(false)
  })
})
