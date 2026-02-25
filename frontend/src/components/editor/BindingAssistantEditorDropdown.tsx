'use client'

import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { EditorApi } from '@/services/editorApi'
import { toast } from 'sonner'
import { Loader2, UserPlus, Check } from 'lucide-react'

type AssistantEditor = {
  id: string
  email?: string
  full_name?: string
}

export function BindingAssistantEditorDropdown({
  manuscriptId,
  currentAssistantEditor,
  onAssigned,
  disabled = false,
}: {
  manuscriptId: string
  currentAssistantEditor?: { id: string; full_name?: string | null; email?: string | null } | null
  onAssigned?: () => void
  disabled?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [savingId, setSavingId] = useState<string | null>(null)
  const [candidates, setCandidates] = useState<AssistantEditor[]>([])

  useEffect(() => {
    if (!open) return
    let alive = true
    const delayMs = q.trim() ? 300 : 0
    const timer = window.setTimeout(async () => {
      try {
        setLoading(true)
        const res = await EditorApi.listAssistantEditors(q.trim())
        if (!alive) return
        if (!res?.success) {
          throw new Error(res?.detail || res?.message || 'Failed to load assistant editors')
        }
        setCandidates((res.data || []) as AssistantEditor[])
      } catch (e) {
        if (!alive) return
        toast.error(e instanceof Error ? e.message : 'Failed to load assistant editors')
      } finally {
        if (alive) setLoading(false)
      }
    }, delayMs)

    return () => {
      alive = false
      window.clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, q])

  const currentId = String(currentAssistantEditor?.id || '').trim()
  const pinned = useMemo(() => {
    if (!currentId) return candidates
    const top: AssistantEditor[] = []
    const rest: AssistantEditor[] = []
    for (const item of candidates) {
      if (String(item.id || '') === currentId) top.push(item)
      else rest.push(item)
    }
    return [...top, ...rest]
  }, [candidates, currentId])

  return (
    <>
      <Button size="sm" variant="outline" className="gap-2" onClick={() => setOpen(true)} disabled={disabled}>
        <UserPlus className="h-4 w-4" />
        {currentId ? 'Change' : 'Assign'}
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Assign Assistant Editor</DialogTitle>
          </DialogHeader>

          <div className="space-y-3">
            <Input placeholder="Search name/email…" value={q} onChange={(e) => setQ(e.target.value)} />
            <div className="rounded-lg border border-border">
              <div className="max-h-80 overflow-auto">
                {loading ? (
                  <div className="p-6 text-sm text-muted-foreground flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" /> Loading…
                  </div>
                ) : pinned.length === 0 ? (
                  <div className="p-6 text-sm text-muted-foreground">No assistant editors found.</div>
                ) : (
                  <ul className="divide-y divide-border/60">
                    {pinned.map((ae) => {
                      const aid = String(ae.id || '')
                      const isCurrent = aid === currentId
                      const isSaving = savingId === aid
                      return (
                        <li key={aid} className="p-3 flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="truncate font-medium text-foreground">{ae.full_name || ae.email || aid}</div>
                            {ae.email ? <div className="truncate text-xs text-muted-foreground">{ae.email}</div> : null}
                          </div>
                          <Button
                            size="sm"
                            variant={isCurrent ? 'secondary' : 'default'}
                            disabled={isSaving}
                            onClick={async () => {
                              if (!aid) return
                              if (isCurrent) return
                              try {
                                setSavingId(aid)
                                const res = await EditorApi.assignAE(manuscriptId, { ae_id: aid })
                                if (!res?.message) {
                                  throw new Error(res?.detail || res?.message || 'Failed to assign assistant editor')
                                }
                                toast.success('Assistant Editor updated')
                                setOpen(false)
                                onAssigned?.()
                              } catch (e) {
                                toast.error(e instanceof Error ? e.message : 'Failed to assign assistant editor')
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
