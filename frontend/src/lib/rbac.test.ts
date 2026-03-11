import { describe, expect, it } from 'vitest'

import { deriveEditorCapability } from './rbac'

describe('deriveEditorCapability', () => {
  it('maps bind academic editor capability from allowed actions', () => {
    const capability = deriveEditorCapability({
      allowed_actions: ['manuscript:bind_academic_editor'],
      journal_scope: {
        enforcement_enabled: true,
        is_admin: false,
        allowed_journal_ids: ['journal-1'],
      },
    } as any)

    expect(capability.canBindAcademicEditor).toBe(true)
    expect(capability.canBindOwner).toBe(false)
  })
})
