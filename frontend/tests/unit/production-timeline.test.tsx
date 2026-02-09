import { describe, expect, it } from 'vitest'
import { sortCyclesByNewest } from '@/lib/production-utils'

describe('production timeline ordering', () => {
  it('keeps stable descending cycle order', () => {
    const rows = sortCyclesByNewest([
      {
        id: 'c1',
        manuscript_id: 'm1',
        cycle_no: 1,
        status: 'draft',
        layout_editor_id: 'e1',
        proofreader_author_id: 'a1',
      },
      {
        id: 'c2',
        manuscript_id: 'm1',
        cycle_no: 2,
        status: 'awaiting_author',
        layout_editor_id: 'e1',
        proofreader_author_id: 'a1',
      },
    ])

    expect(rows[0].id).toBe('c2')
    expect(rows[1].id).toBe('c1')
  })
})
