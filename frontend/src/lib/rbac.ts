import type { EditorAction, EditorRbacContext } from '@/types/rbac'

export type EditorCapability = {
  canViewProcess: boolean
  canViewDetail: boolean
  canBindOwner: boolean
  canUpdateInvoiceInfo: boolean
  canConfirmInvoicePaid: boolean
  canRecordFirstDecision: boolean
  canSubmitFinalDecision: boolean
}

function hasAny(actions: Set<string>, candidates: EditorAction[]): boolean {
  if (actions.has('*')) return true
  return candidates.some((item) => actions.has(item))
}

export function deriveEditorCapability(context?: EditorRbacContext | null): EditorCapability {
  const actions = new Set<string>((context?.allowed_actions || []).map((item) => String(item)))
  return {
    canViewProcess: hasAny(actions, ['process:view']),
    canViewDetail: hasAny(actions, ['manuscript:view_detail']),
    canBindOwner: hasAny(actions, ['manuscript:bind_owner']),
    canUpdateInvoiceInfo: hasAny(actions, ['invoice:update_info', 'invoice:override_apc']),
    canConfirmInvoicePaid: hasAny(actions, ['invoice:override_apc']),
    canRecordFirstDecision: hasAny(actions, ['decision:record_first']),
    canSubmitFinalDecision: hasAny(actions, ['decision:submit_final']),
  }
}

export function canUseDecisionStage(
  capability: EditorCapability,
  stage: 'first' | 'final'
): boolean {
  if (stage === 'final') return capability.canSubmitFinalDecision
  return capability.canRecordFirstDecision || capability.canSubmitFinalDecision
}

export function buildProcessScopeEmptyHint(context?: EditorRbacContext | null): string | null {
  if (!context?.journal_scope?.enforcement_enabled) return null
  if (context.journal_scope.is_admin) return null
  const count = (context.journal_scope.allowed_journal_ids || []).length
  if (count > 0) {
    return `Scope enabled: you can access ${count} journal(s).`
  }
  return 'Scope enabled: no journal is assigned to your role yet. Contact admin to bind journal scope.'
}
