import { describe, expect, it } from 'vitest'
import { canSubmitProofreading } from '@/lib/production-utils'

describe('author proofreading submit guard', () => {
  it('allows confirm_clean when writable', () => {
    const ok = canSubmitProofreading('confirm_clean', [], false)
    expect(ok).toBe(true)
  })

  it('requires at least one suggested_text for submit_corrections', () => {
    expect(canSubmitProofreading('submit_corrections', [{ suggested_text: '' }], false)).toBe(false)
    expect(canSubmitProofreading('submit_corrections', [{ suggested_text: 'Fix typo' }], false)).toBe(true)
  })

  it('blocks all submissions in readonly mode', () => {
    expect(canSubmitProofreading('confirm_clean', [], true)).toBe(false)
    expect(canSubmitProofreading('submit_corrections', [{ suggested_text: 'Fix' }], true)).toBe(false)
  })
})
