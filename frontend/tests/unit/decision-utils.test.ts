import { describe, expect, it } from 'vitest'
import { assembleLetter } from '@/lib/decision-utils'

describe('assembleLetter', () => {
  it('builds letter with reviewer comments', () => {
    const text = assembleLetter([
      { id: 'r1', comments_for_author: 'Please add ablation study.' },
      { id: 'r2', comments_for_author: 'English language polishing is needed.' },
    ])

    expect(text).toContain('Reviewer 1:')
    expect(text).toContain('Please add ablation study.')
    expect(text).toContain('Reviewer 2:')
    expect(text).toContain('English language polishing is needed.')
    expect(text).toContain('Best regards,')
  })

  it('uses fallback text when public comments are empty', () => {
    const text = assembleLetter([{ id: 'r1', comments_for_author: '' }])
    expect(text).toContain('(No public comment provided)')
  })
})
