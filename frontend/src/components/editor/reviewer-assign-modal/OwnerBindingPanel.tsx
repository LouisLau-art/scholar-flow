import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

type StaffProfile = {
  id: string
  email?: string | null
  full_name?: string | null
  roles?: string[]
}

type OwnerBindingPanelProps = {
  loadingOwner: boolean
  savingOwner: boolean
  ownerId: string
  ownerSearch: string
  filteredInternalStaff: StaffProfile[]
  currentOwnerLabel: string
  onOwnerSearchChange: (value: string) => void
  onOwnerChange: (ownerId: string) => void
}

export function OwnerBindingPanel(props: OwnerBindingPanelProps) {
  const {
    loadingOwner,
    savingOwner,
    ownerId,
    ownerSearch,
    filteredInternalStaff,
    currentOwnerLabel,
    onOwnerSearchChange,
    onOwnerChange,
  } = props

  return (
    <div className="mb-6 rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="font-semibold text-foreground">Internal Owner / Invited By</div>
          <div className="text-xs text-muted-foreground mt-1">在初审阶段绑定负责人（仅 editor/admin），修改后自动保存并提示。</div>
        </div>
        <div className="text-xs text-muted-foreground">{savingOwner ? 'Saving…' : loadingOwner ? 'Loading…' : ''}</div>
      </div>

      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
        <label htmlFor="reviewer-owner-search" className="sr-only">
          Search internal staff
        </label>
        <input
          id="reviewer-owner-search"
          type="text"
          placeholder="Search internal staff..."
          value={ownerSearch}
          onChange={(e) => onOwnerSearchChange(e.target.value)}
          className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary/30 text-sm"
        />
        <Select value={ownerId || '__unassigned'} onValueChange={onOwnerChange} disabled={savingOwner || loadingOwner}>
          <SelectTrigger className="w-full" data-testid="owner-select">
            <SelectValue placeholder="Unassigned" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__unassigned" disabled>
              Unassigned
            </SelectItem>
            {filteredInternalStaff.map((u) => (
              <SelectItem key={u.id} value={u.id}>
                {(u.full_name || u.email || u.id) as string}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="mt-2 text-xs text-muted-foreground">
        Current: <span className="font-medium text-foreground">{currentOwnerLabel}</span>
      </div>
      {!ownerId && (
        <div className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
          未绑定 Owner：分配时后端会自动绑定为当前操作人（建议你先手动确认归属人）。
        </div>
      )}
    </div>
  )
}
