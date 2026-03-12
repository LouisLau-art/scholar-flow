import type {
  ProductionCorrectionItem,
  ProductionCycle,
  ProductionCycleStage,
  ProductionCycleStatus,
  ProofreadingDecision,
} from '@/types/production'

const ACTIVE_PRODUCTION_STAGES: ReadonlySet<ProductionCycleStage> = new Set([
  'received',
  'typesetting',
  'language_editing',
  'ae_internal_proof',
  'author_proofreading',
  'ae_final_review',
  'pdf_preparation',
  'ready_to_publish',
])

const ACTIVE_LEGACY_STATUSES: ReadonlySet<ProductionCycleStatus> = new Set([
  'draft',
  'awaiting_author',
  'author_corrections_submitted',
  'in_layout_revision',
])

export function hasActiveProductionCycle(cycles: ProductionCycle[]): boolean {
  return cycles.some((cycle) => {
    const stage = String(cycle.stage || '').trim()
    if (stage) return ACTIVE_PRODUCTION_STAGES.has(stage)
    return ACTIVE_LEGACY_STATUSES.has(cycle.status)
  })
}

export function canApproveProductionCycle(status: string | null | undefined): boolean {
  return String(status || '').toLowerCase() === 'author_confirmed'
}

export function hasValidCorrections(items: ProductionCorrectionItem[]): boolean {
  return items.some((item) => String(item.suggested_text || '').trim().length > 0)
}

export function canSubmitProofreading(
  decision: ProofreadingDecision,
  items: ProductionCorrectionItem[],
  isReadOnly: boolean
): boolean {
  if (isReadOnly) return false
  if (decision === 'confirm_clean') return true
  return hasValidCorrections(items)
}

export function sortCyclesByNewest(cycles: ProductionCycle[]): ProductionCycle[] {
  return [...cycles].sort((a, b) => Number(b.cycle_no || 0) - Number(a.cycle_no || 0))
}
