'use client'

import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { ClipboardCheck, Users, Gavel } from 'lucide-react'
import { QuickPrecheckModal } from '@/components/editor/QuickPrecheckModal'
import type { ProcessRow } from '@/components/editor/ManuscriptTable'

export function ManuscriptActions({
  row,
  onAssign,
  onDecide,
  onRowUpdated,
  canAssign = true,
  canDecide = true,
  canQuickPrecheck = true,
}: {
  row: ProcessRow
  onAssign?: (row: ProcessRow) => void
  onDecide?: (row: ProcessRow) => void
  onRowUpdated?: (updated: { id: string; status?: string; updated_at?: string }) => void
  canAssign?: boolean
  canDecide?: boolean
  canQuickPrecheck?: boolean
}) {
  const [precheckOpen, setPrecheckOpen] = useState(false)
  const isPrecheck = useMemo(() => (row.status || '').toLowerCase() === 'pre_check', [row.status])
  const quickPrecheckEnabled = isPrecheck && canQuickPrecheck

  return (
    <div className="flex justify-end gap-1">
      <Button
        size="icon"
        variant="ghost"
        className="h-8 w-8"
        title={
          !canQuickPrecheck
            ? 'No permission for pre-check action'
            : quickPrecheckEnabled
            ? 'Quick Pre-check'
            : 'Quick Pre-check (only for Pre-check)'
        }
        onClick={() => setPrecheckOpen(true)}
        disabled={!quickPrecheckEnabled}
        data-testid={`quick-precheck-${row.id}`}
      >
        <ClipboardCheck className="h-4 w-4" />
      </Button>

      <Button
        size="icon"
        variant="ghost"
        className="h-8 w-8"
        title={canAssign ? 'Assign Reviewer' : 'No permission to assign reviewer'}
        onClick={() => onAssign?.(row)}
        disabled={!canAssign}
        data-testid={`assign-${row.id}`}
      >
        <Users className="h-4 w-4" />
      </Button>

      <Button
        size="icon"
        variant="ghost"
        className="h-8 w-8"
        title={canDecide ? 'Decide' : 'No permission to submit decision'}
        onClick={() => onDecide?.(row)}
        disabled={!canDecide}
        data-testid={`decide-${row.id}`}
      >
        <Gavel className="h-4 w-4" />
      </Button>

      <QuickPrecheckModal
        open={precheckOpen}
        onOpenChange={setPrecheckOpen}
        manuscriptId={row.id}
        manuscriptTitle={(row as any).title}
        onUpdated={onRowUpdated}
      />
    </div>
  )
}
