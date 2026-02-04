'use client'

import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { EditorApi } from '@/services/editorApi'
import { toast } from 'sonner'
import { Loader2, UserPlus, Check } from 'lucide-react'

type Staff = { id: string; email?: string; full_name?: string }

export function BindingOwnerDropdown({
  manuscriptId,
  currentOwner,
  onBound,
}: {
  manuscriptId: string
  currentOwner?: { id: string; full_name?: string | null; email?: string | null } | null
  onBound?: () => void
}) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [staff, setStaff] = useState<Staff[]>([])
  const [savingId, setSavingId] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    let alive = true
    async function load() {
      try {
        setLoading(true)
        const res = await EditorApi.listInternalStaff(q)
        if (!alive) return
        if (res?.success) setStaff(res.data || [])
      } finally {
        if (alive) setLoading(false)
      }
    }
    load()
    const t = setTimeout(load, 350)
    return () => {
      alive = false
      clearTimeout(t)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, q])

  const currentOwnerId = currentOwner?.id || ''
  const pinned = useMemo(() => {
    if (!currentOwnerId) return staff
    const top: Staff[] = []
    const rest: Staff[] = []
    for (const s of staff) {
      if (s.id === currentOwnerId) top.push(s)
      else rest.push(s)
    }
    return [...top, ...rest]
  }, [staff, currentOwnerId])

  return (
    <>
      <Button size="sm" variant="outline" className="gap-2" onClick={() => setOpen(true)}>
        <UserPlus className="h-4 w-4" />
        {currentOwnerId ? 'Change' : 'Bind'}
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Bind Internal Owner</DialogTitle>
          </DialogHeader>

          <div className="space-y-3">
            <Input placeholder="Search name/email…" value={q} onChange={(e) => setQ(e.target.value)} />

            <div className="rounded-lg border border-slate-200">
              <div className="max-h-80 overflow-auto">
                {loading ? (
                  <div className="p-6 text-sm text-slate-500 flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" /> Loading…
                  </div>
                ) : pinned.length === 0 ? (
                  <div className="p-6 text-sm text-slate-500">No internal staff found.</div>
                ) : (
                  <ul className="divide-y divide-slate-100">
                    {pinned.map((s) => {
                      const isCurrent = s.id === currentOwnerId
                      const isSaving = savingId === s.id
                      return (
                        <li key={s.id} className="p-3 flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="truncate font-medium text-slate-900">
                              {s.full_name || s.email || s.id}
                            </div>
                            {s.email ? <div className="truncate text-xs text-slate-500">{s.email}</div> : null}
                          </div>
                          <Button
                            size="sm"
                            variant={isCurrent ? 'secondary' : 'default'}
                            disabled={isSaving}
                            onClick={async () => {
                              try {
                                setSavingId(s.id)
                                const res = await EditorApi.bindOwner(manuscriptId, s.id)
                                if (!res?.success) {
                                  throw new Error(res?.detail || res?.message || 'Bind failed')
                                }
                                toast.success('Owner updated')
                                setOpen(false)
                                onBound?.()
                              } catch (e) {
                                toast.error(e instanceof Error ? e.message : 'Bind failed')
                              } finally {
                                setSavingId(null)
                              }
                            }}
                            className="gap-2"
                          >
                            {isCurrent ? <Check className="h-4 w-4" /> : null}
                            {isSaving ? 'Saving…' : isCurrent ? 'Current' : 'Select'}
                          </Button>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

