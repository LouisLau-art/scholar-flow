'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2, AlertTriangle } from 'lucide-react'

import { User, UserRole } from '@/types/user'
import { Journal } from '@/types/journal'
import { adminUserService } from '@/services/admin/userService'
import { adminJournalService } from '@/services/admin/journalService'
import { Button } from '@/components/ui/button'
import {
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { SafeDialog, SafeDialogContent } from '@/components/ui/safe-dialog'

interface UserRoleDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (
    userId: string,
    newRoles: UserRole[],
    reason: string,
    scopeJournalIds?: string[]
  ) => Promise<void>
  user: User | null
}

const ROLE_OPTIONS: Array<{ value: UserRole; label: string; helper: string }> = [
  { value: 'author', label: 'Author', helper: '投稿与修回' },
  { value: 'reviewer', label: 'Reviewer', helper: '审稿工作台与意见提交' },
  { value: 'owner', label: 'Owner', helper: '销售/BD/KPI 归属人（可被绑定为稿件 Owner）' },
  { value: 'assistant_editor', label: 'Assistant Editor', helper: '仅可处理分配到自己的稿件' },
  { value: 'production_editor', label: 'Production Editor', helper: '排版与校对协作（仅可处理分配到自己的 Production Cycle）' },
  { value: 'managing_editor', label: 'Managing Editor', helper: 'Intake 与分配（必须绑定期刊）' },
  { value: 'academic_editor', label: 'Academic Editor', helper: '学术预审与 First Decision（必须绑定期刊）' },
  { value: 'editor_in_chief', label: 'Editor-in-Chief', helper: '主编终审与期刊学术把关（必须绑定期刊）' },
  { value: 'admin', label: 'Admin', helper: '全局管理权限' },
]

const SCOPE_REQUIRED_ROLES = new Set<UserRole>(['managing_editor', 'academic_editor', 'editor_in_chief'])

export function UserRoleDialog({ isOpen, onClose, onConfirm, user }: UserRoleDialogProps) {
  const [selectedRoles, setSelectedRoles] = useState<UserRole[]>(['author'])
  const [selectedJournalIds, setSelectedJournalIds] = useState<string[]>([])
  const [journals, setJournals] = useState<Journal[]>([])
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [loadingScopeData, setLoadingScopeData] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const scopeRequired = useMemo(
    () => selectedRoles.some((role) => SCOPE_REQUIRED_ROLES.has(role)),
    [selectedRoles]
  )

  const handleRequestClose = useCallback(() => {
    setError(null)
    setIsSubmitting(false)
    onClose()
  }, [onClose])

  useEffect(() => {
    if (!isOpen || !user) return

    const roles = (user.roles || []).filter(Boolean) as UserRole[]
    setSelectedRoles(roles.length > 0 ? roles : ['author'])
    setReason('')
    setError(null)

    const loadScopeData = async () => {
      setLoadingScopeData(true)
      try {
        const [journalRows, scopeRows] = await Promise.all([
          adminJournalService.list(false),
          adminUserService.listJournalScopes({ userId: user.id, isActive: true }),
        ])
        setJournals(journalRows || [])

        const journalIdSet = new Set<string>()
        for (const row of scopeRows || []) {
          if (row.role === 'managing_editor' || row.role === 'academic_editor' || row.role === 'editor_in_chief') {
            journalIdSet.add(String(row.journal_id))
          }
        }
        setSelectedJournalIds(Array.from(journalIdSet))
      } catch (e) {
        console.error('[UserRoleDialog] load scope data failed:', e)
        setJournals([])
        setSelectedJournalIds([])
        setError(e instanceof Error ? e.message : 'Failed to load journals/scopes')
      } finally {
        setLoadingScopeData(false)
      }
    }

    loadScopeData()
  }, [isOpen, user])

  if (!user || !isOpen) return null

  const toggleRole = (role: UserRole) => {
    setSelectedRoles((prev) => {
      if (prev.includes(role)) {
        return prev.filter((r) => r !== role)
      }
      return [...prev, role]
    })
  }

  const toggleJournal = (journalId: string) => {
    setSelectedJournalIds((prev) => {
      if (prev.includes(journalId)) {
        return prev.filter((id) => id !== journalId)
      }
      return [...prev, journalId]
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (selectedRoles.length === 0) {
      setError('Please select at least one role.')
      return
    }
    if (reason.trim().length < 10) {
      setError('Reason must be at least 10 characters long.')
      return
    }
    if (scopeRequired && selectedJournalIds.length === 0) {
      setError('Managing Editor / Editor-in-Chief must bind at least one journal.')
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      await onConfirm(
        user.id,
        selectedRoles,
        reason,
        scopeRequired ? selectedJournalIds : undefined
      )
      handleRequestClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update role')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <SafeDialog open={isOpen} onClose={handleRequestClose} closeDisabled={isSubmitting}>
      <SafeDialogContent
        aria-label="Edit User Roles"
        className="max-h-[88vh] max-w-2xl"
        closeDisabled={isSubmitting}
      >
        <DialogHeader className="pr-10 text-left">
          <DialogTitle>Edit User Roles</DialogTitle>
          <DialogDescription className="mt-1">
            Admin can update roles and bind journal scopes for managing roles in one step.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="rounded-md border bg-muted/40 p-3">
            <p className="break-words text-sm text-foreground">
              <span className="font-semibold">User:</span> {user.full_name} ({user.email})
            </p>
          </div>

          <div className="space-y-2">
            <Label>Roles (Multi-select)</Label>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {ROLE_OPTIONS.map((role) => {
                const checked = selectedRoles.includes(role.value)
                return (
                  <Button
                    key={role.value}
                    type="button"
                    variant={checked ? 'default' : 'outline'}
                    className="h-auto min-w-0 items-start justify-start whitespace-normal break-words px-3 py-2 text-left"
                    onClick={() => toggleRole(role.value)}
                  >
                    <span className="block min-w-0">
                      <span className="block font-medium">{role.label}</span>
                      <span className="block break-words text-xs opacity-80">{role.helper}</span>
                    </span>
                  </Button>
                )
              })}
            </div>
          </div>

          {scopeRequired && (
            <div className="space-y-2">
              <Label>Journal Scope (Required for ME/Academic/EIC)</Label>
              {loadingScopeData ? (
                <div className="flex items-center gap-2 rounded-md border p-3 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading journals...
                </div>
              ) : journals.length === 0 ? (
                <div className="rounded-md border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive">
                  No active journals found. Please create journals first.
                </div>
              ) : (
                <div className="rounded-md border p-2">
                  <div className="mb-2 flex flex-wrap gap-2">
                    {selectedJournalIds.length === 0 ? (
                      <Badge variant="outline">No journal selected</Badge>
                    ) : (
                      selectedJournalIds.map((id) => {
                        const journal = journals.find((item) => item.id === id)
                        return (
                          <Badge key={id} variant="secondary" className="max-w-full whitespace-normal break-all">
                            {journal?.title || id}
                          </Badge>
                        )
                      })
                    )}
                  </div>
                  <div className="grid max-h-48 grid-cols-1 gap-2 overflow-auto sm:grid-cols-2">
                    {journals.map((journal) => {
                      const checked = selectedJournalIds.includes(journal.id)
                      return (
                        <Button
                          key={journal.id}
                          type="button"
                          size="sm"
                          variant={checked ? 'default' : 'outline'}
                          className="h-auto min-w-0 justify-start whitespace-normal break-words text-left"
                          onClick={() => toggleJournal(journal.id)}
                        >
                          {journal.title}
                        </Button>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="space-y-2">
            <Label>
              Reason <span className="text-destructive">*</span>
            </Label>
            <Textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              placeholder="Explain why this role/scope change is required..."
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4" />
              {error}
            </div>
          )}

          <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end sm:space-x-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleRequestClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || loadingScopeData}>
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Confirm
            </Button>
          </div>
        </form>
      </SafeDialogContent>
    </SafeDialog>
  )
}
