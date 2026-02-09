import { describe, expect, it } from 'vitest'
import { hasActiveProductionCycle, sortCyclesByNewest } from '@/lib/production-utils'
import type { ProductionCycle } from '@/types/production'

function cycle(partial: Partial<ProductionCycle>): ProductionCycle {
  return {
    id: partial.id || 'c1',
    manuscript_id: partial.manuscript_id || 'm1',
    cycle_no: partial.cycle_no || 1,
    status: partial.status || 'draft',
    layout_editor_id: partial.layout_editor_id || 'e1',
    proofreader_author_id: partial.proofreader_author_id || 'a1',
    ...partial,
  }
}

describe('production workspace utils', () => {
  it('detects active cycles correctly', () => {
    expect(hasActiveProductionCycle([cycle({ status: 'draft' })])).toBe(true)
    expect(hasActiveProductionCycle([cycle({ status: 'approved_for_publish' })])).toBe(false)
  })

  it('sorts cycles by newest cycle_no', () => {
    const ordered = sortCyclesByNewest([
      cycle({ id: 'c1', cycle_no: 1 }),
      cycle({ id: 'c3', cycle_no: 3 }),
      cycle({ id: 'c2', cycle_no: 2 }),
    ])
    expect(ordered.map((item) => item.id)).toEqual(['c3', 'c2', 'c1'])
  })
})
