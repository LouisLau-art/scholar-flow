import React from 'react'
import { Check, ChevronsUpDown, Loader2, X } from 'lucide-react'

import { editorService } from '../services/editorService'
import { getAssistantEditors, peekAssistantEditorsCache, type AssistantEditorOption } from '@/services/assistantEditorsCache'
import { EditorApi } from '@/services/editorApi'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

type InternalStaffOption = { id: string; email?: string | null; full_name?: string | null; roles?: string[] | null }

type PickerOption = {
  id: string
  label: string
  searchText: string
}

interface AssignAEModalProps {
  isOpen: boolean
  onClose: () => void
  manuscriptId: string
  onAssignSuccess: () => void
}

type SearchablePickerProps = {
  label: string
  value: string
  options: PickerOption[]
  placeholder: string
  searchPlaceholder: string
  emptyText: string
  disabled?: boolean
  loading?: boolean
  onChange: (nextId: string) => void
}

function SearchablePicker(props: SearchablePickerProps) {
  const [open, setOpen] = React.useState(false)
  const [query, setQuery] = React.useState('')

  const selected = React.useMemo(
    () => props.options.find((option) => option.id === props.value) || null,
    [props.options, props.value]
  )

  const filtered = React.useMemo(() => {
    const keyword = query.trim().toLowerCase()
    if (!keyword) return props.options
    return props.options.filter((option) => option.searchText.includes(keyword))
  }, [props.options, query])

  React.useEffect(() => {
    if (!open) {
      setQuery('')
    }
  }, [open])

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-foreground">{props.label}</label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={props.disabled}
            className="w-full justify-between"
            onPointerDown={(event) => {
              // 中文注释：Dialog 内组合场景下，手动兜底“再次点击触发器即可收起”。
              if (open) {
                event.preventDefault()
                setOpen(false)
              }
            }}
          >
            <span className={cn('truncate text-left', !selected && 'text-muted-foreground')}>
              {selected?.label || props.placeholder}
            </span>
            {props.loading ? <Loader2 className="h-4 w-4 animate-spin opacity-60" /> : <ChevronsUpDown className="h-4 w-4 opacity-60" />}
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className="w-[var(--radix-popover-trigger-width)] p-2"
          align="start"
          side="top"
          onEscapeKeyDown={() => setOpen(false)}
          onPointerDownOutside={() => setOpen(false)}
          onFocusOutside={() => setOpen(false)}
          onInteractOutside={() => setOpen(false)}
        >
          <div className="mb-2 flex items-center gap-2">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={props.searchPlaceholder}
              autoFocus
            />
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="h-8 w-8 shrink-0"
              onClick={() => setOpen(false)}
              aria-label="收起下拉"
              title="收起"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="max-h-[min(16rem,var(--radix-popover-content-available-height))] overflow-auto rounded-md border border-border/60">
            {filtered.length === 0 ? (
              <div className="px-3 py-2 text-xs text-muted-foreground">{props.emptyText}</div>
            ) : (
              filtered.map((option) => {
                const active = option.id === props.value
                return (
                  <button
                    key={option.id}
                    type="button"
                    className={cn(
                      'flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-muted',
                      active && 'bg-muted/70 font-medium'
                    )}
                    onClick={() => {
                      props.onChange(option.id)
                      setOpen(false)
                    }}
                  >
                    <span className="truncate">{option.label}</span>
                    <Check className={cn('h-4 w-4', active ? 'opacity-100' : 'opacity-0')} />
                  </button>
                )
              })
            )}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}

export const AssignAEModal: React.FC<AssignAEModalProps> = ({ isOpen, onClose, manuscriptId, onAssignSuccess }) => {
  const [selectedAE, setSelectedAE] = React.useState('')
  const [selectedOwner, setSelectedOwner] = React.useState('')
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [isLoadingAEs, setIsLoadingAEs] = React.useState(false)
  const [aes, setAes] = React.useState<AssistantEditorOption[]>([])
  const [isLoadingOwners, setIsLoadingOwners] = React.useState(false)
  const [owners, setOwners] = React.useState<InternalStaffOption[]>([])
  const [error, setError] = React.useState<string>('')

  React.useEffect(() => {
    let mounted = true
    if (!isOpen) {
      setSelectedAE('')
      setSelectedOwner('')
      setError('')
      return () => {
        mounted = false
      }
    }

    const cached = peekAssistantEditorsCache()
    if (cached && cached.length) {
      setAes(cached)
    }

    async function loadAEs() {
      const hasCached = Boolean(cached && cached.length)
      setIsLoadingAEs(!hasCached)
      setError('')
      try {
        const rows = await getAssistantEditors()
        if (mounted) setAes(rows)
      } catch (e) {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load assistant editors')
          if (!cached?.length) setAes([])
        }
      } finally {
        if (mounted) setIsLoadingAEs(false)
      }
    }
    void loadAEs()

    async function loadOwners() {
      setIsLoadingOwners(true)
      try {
        const res = await EditorApi.listInternalStaff()
        if (!mounted) return
        if (res?.success) {
          const rows = Array.isArray(res?.data) ? (res.data as InternalStaffOption[]) : []
          rows.sort((a, b) => {
            const aRoles = Array.isArray(a.roles) ? a.roles.map((r) => String(r).toLowerCase()) : []
            const bRoles = Array.isArray(b.roles) ? b.roles.map((r) => String(r).toLowerCase()) : []
            const aOwner = aRoles.includes('owner')
            const bOwner = bRoles.includes('owner')
            if (aOwner !== bOwner) return aOwner ? -1 : 1
            const aName = String(a.full_name || a.email || '').toLowerCase()
            const bName = String(b.full_name || b.email || '').toLowerCase()
            return aName.localeCompare(bName)
          })
          setOwners(rows)
        } else {
          setOwners([])
        }
      } catch {
        if (mounted) setOwners([])
      } finally {
        if (mounted) setIsLoadingOwners(false)
      }
    }
    void loadOwners()

    return () => {
      mounted = false
    }
  }, [isOpen])

  if (!isOpen) return null

  const aeOptions: PickerOption[] = aes.map((ae) => {
    const label = ae.full_name || ae.email || ae.id
    return {
      id: ae.id,
      label,
      searchText: `${label} ${ae.email || ''} ${ae.id}`.toLowerCase(),
    }
  })

  const ownerOptions: PickerOption[] = owners.map((owner) => {
    const label = owner.full_name || owner.email || owner.id
    return {
      id: owner.id,
      label,
      searchText: `${label} ${owner.email || ''} ${owner.id}`.toLowerCase(),
    }
  })

  const selectedAeLabel = aeOptions.find((x) => x.id === selectedAE)?.label || '未选择'
  const selectedOwnerLabel = ownerOptions.find((x) => x.id === selectedOwner)?.label || '留空（默认当前 ME）'

  const handleAssign = async () => {
    if (!selectedAE) return
    setIsSubmitting(true)
    setError('')
    try {
      await editorService.assignAE(manuscriptId, selectedAE, {
        startExternalReview: true,
        bindOwnerIfEmpty: !selectedOwner,
        ownerId: selectedOwner || undefined,
      })
      onAssignSuccess()
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to assign AE')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => (!open ? onClose() : undefined)}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>通过并分配 AE</DialogTitle>
          <DialogDescription>
            先选择 Assistant Editor（必填）。可选指定 Owner。确认后稿件将推进到 <code>under_review</code>。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <SearchablePicker
            label="Assistant Editor（必填）"
            value={selectedAE}
            options={aeOptions}
            placeholder={isLoadingAEs && aeOptions.length === 0 ? '加载 AE 中…' : '请选择 AE'}
            searchPlaceholder="搜索 AE：姓名 / 邮箱 / ID"
            emptyText="没有匹配的 AE"
            disabled={isSubmitting || isLoadingAEs}
            loading={isLoadingAEs}
            onChange={setSelectedAE}
          />

          <details className="rounded-md border border-border/70 bg-muted/30 px-3 py-2">
            <summary className="cursor-pointer text-sm font-medium text-foreground">高级选项：Owner（可选）</summary>
            <div className="mt-3">
              <SearchablePicker
                label="Owner（可选）"
                value={selectedOwner}
                options={ownerOptions}
                placeholder={isLoadingOwners && ownerOptions.length === 0 ? '加载 Owner 中…' : '不指定 Owner'}
                searchPlaceholder="搜索 Owner：姓名 / 邮箱 / ID"
                emptyText="没有匹配的 Owner"
                disabled={isSubmitting || isLoadingOwners}
                loading={isLoadingOwners}
                onChange={setSelectedOwner}
              />
              {selectedOwner ? (
                <div className="mt-2">
                  <Button type="button" variant="ghost" size="sm" onClick={() => setSelectedOwner('')} disabled={isSubmitting}>
                    清空 Owner 选择
                  </Button>
                </div>
              ) : null}
              <div className="mt-2 text-xs text-muted-foreground">
                不指定时，系统将按现有逻辑默认绑定当前 ME（UAT 提速策略）。
              </div>
            </div>
          </details>

          <div className="rounded-md border border-border/70 bg-card px-3 py-2 text-xs text-foreground">
            摘要：AE = <span className="font-medium">{selectedAeLabel}</span>；Owner ={' '}
            <span className="font-medium">{selectedOwnerLabel}</span>；下一状态 ={' '}
            <span className="font-medium">under_review</span>
          </div>

          {error ? <div className="text-xs text-destructive">{error}</div> : null}
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            取消
          </Button>
          <Button onClick={handleAssign} disabled={!selectedAE || isSubmitting || isLoadingAEs}>
            {isSubmitting ? '处理中…' : '分配并进入外审'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
