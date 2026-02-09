import { describe, expect, it } from 'vitest'

import { buildProcessScopeEmptyHint, canUseDecisionStage, deriveEditorCapability } from '@/lib/rbac'

describe('rbac visibility helpers', () => {
  it('grants all capabilities for wildcard action', () => {
    const capability = deriveEditorCapability({
      user_id: 'u-1',
      roles: ['admin'],
      normalized_roles: ['admin'],
      allowed_actions: ['*'],
      journal_scope: {
        enforcement_enabled: true,
        allowed_journal_ids: [],
        is_admin: true,
      },
    })

    expect(capability.canViewProcess).toBe(true)
    expect(capability.canBindOwner).toBe(true)
    expect(capability.canSubmitFinalDecision).toBe(true)
  })

  it('maps granular actions correctly', () => {
    const capability = deriveEditorCapability({
      user_id: 'u-2',
      roles: ['managing_editor'],
      normalized_roles: ['managing_editor'],
      allowed_actions: ['process:view', 'manuscript:view_detail', 'decision:record_first'],
      journal_scope: {
        enforcement_enabled: true,
        allowed_journal_ids: ['j-1'],
        is_admin: false,
      },
    })

    expect(capability.canViewProcess).toBe(true)
    expect(capability.canRecordFirstDecision).toBe(true)
    expect(capability.canSubmitFinalDecision).toBe(false)
    expect(capability.canConfirmInvoicePaid).toBe(false)
  })

  it('returns scope hint when enforcement enabled and no assignment', () => {
    const hint = buildProcessScopeEmptyHint({
      user_id: 'u-3',
      roles: ['assistant_editor'],
      normalized_roles: ['assistant_editor'],
      allowed_actions: ['manuscript:view_detail'],
      journal_scope: {
        enforcement_enabled: true,
        allowed_journal_ids: [],
        is_admin: false,
      },
    })
    expect(hint).toContain('no journal')
  })

  it('hides scope hint for admin', () => {
    const hint = buildProcessScopeEmptyHint({
      user_id: 'u-4',
      roles: ['admin'],
      normalized_roles: ['admin'],
      allowed_actions: ['*'],
      journal_scope: {
        enforcement_enabled: true,
        allowed_journal_ids: [],
        is_admin: true,
      },
    })
    expect(hint).toBeNull()
  })

  it('enforces first/final decision stage availability', () => {
    const meCapability = deriveEditorCapability({
      user_id: 'u-5',
      roles: ['managing_editor'],
      normalized_roles: ['managing_editor'],
      allowed_actions: ['decision:record_first'],
      journal_scope: {
        enforcement_enabled: false,
        allowed_journal_ids: [],
        is_admin: false,
      },
    })
    expect(canUseDecisionStage(meCapability, 'first')).toBe(true)
    expect(canUseDecisionStage(meCapability, 'final')).toBe(false)

    const eicCapability = deriveEditorCapability({
      user_id: 'u-6',
      roles: ['editor_in_chief'],
      normalized_roles: ['editor_in_chief'],
      allowed_actions: ['decision:record_first', 'decision:submit_final'],
      journal_scope: {
        enforcement_enabled: false,
        allowed_journal_ids: [],
        is_admin: false,
      },
    })
    expect(canUseDecisionStage(eicCapability, 'first')).toBe(true)
    expect(canUseDecisionStage(eicCapability, 'final')).toBe(true)
  })
})
