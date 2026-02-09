import type { ProductionCorrectionItem, ProductionCycle, ProofreadingDecision } from '@/types/production'

export function hasActiveProductionCycle(cycles: ProductionCycle[]): boolean {
  return cycles.some((cycle) => ['draft', 'awaiting_author', 'author_corrections_submitted', 'in_layout_revision'].includes(cycle.status))
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
