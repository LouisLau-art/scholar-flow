'use client'

import { useEffect, useMemo, useState } from 'react'
import { Check, Loader2, UserPlus } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { EditorApi } from '@/services/editorApi'

type AcademicEditor = {
  id: string
  email?: string
  full_name?: string
}

export function BindingAcademicEditorDropdown({
  manuscriptId,
  currentAcademicEditor,
  onBound,
  disabled = false,
}: {
  manuscriptId: string
  currentAcademicEditor?: { id: string; full_name?: string | null; email?: string | null } | null
  onBound?: () => void
  disabled?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [savingId, setSavingId] = useState<string | null>(null)
  const [candidates, setCandidates] = useState<AcademicEditor[]>([])

  useEffect(() => {
    if (!open) return
    let alive = true
    const delayMs = q.trim() ? 300 : 0
    const timer = window.setTimeout(async () => {
      try {
        setLoading(true)
        const res = await EditorApi.listAcademicEditors(manuscriptId, q.trim())
        if (!alive) return
        if (!res?.success) {
          throw new Error(res?.detail || res?.message || 'Failed to load academic editors')
        }
        setCandidates((res.data || []) as AcademicEditor[])
      } catch (e) {
        if (!alive) return
        toast.error(e instanceof Error ? e.message : 'Failed to load academic editors')
      } finally {
        if (alive) setLoading(false)
      }
    }, delayMs)

    return () => {
      alive = false
      window.clearTimeout(timer)
    }
  }, [open, q, manuscriptId])

  const currentId = String(currentAcademicEditor?.id || '').trim()
  const pinned = useMemo(() => {
    if (!currentId) return candidates
    const top: AcademicEditor[] = []
    const rest: AcademicEditor[] = []
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
        {currentId ? 'Change' : 'Bind'}
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Bind Academic Editor</DialogTitle>
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
                  <div className="p-6 text-sm text-muted-foreground">No academic editors found.</div>
                ) : (
                  <ul className="divide-y divide-border/60">
                    {pinned.map((item) => {
                      const itemId = String(item.id || '')
                      const isCurrent = itemId === currentId
                      const isSaving = savingId === itemId
                      return (
                        <li key={itemId} className="p-3 flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="truncate font-medium text-foreground">{item.full_name || item.email || itemId}</div>
                            {item.email ? <div className="truncate text-xs text-muted-foreground">{item.email}</div> : null}
                          </div>
                          <Button
                            size="sm"
                            variant={isCurrent ? 'secondary' : 'default'}
                            disabled={isSaving}
                            onClick={async () => {
                              if (!itemId || isCurrent) return
                              try {
                                setSavingId(itemId)
                                const res = await EditorApi.bindAcademicEditor(manuscriptId, {
                                  academic_editor_id: itemId,
                                  source: 'manuscript_detail',
                                })
                                if (!res?.success) {
                                  throw new Error(res?.detail || res?.message || 'Failed to bind academic editor')
                                }
                                toast.success('Academic Editor updated')
                                setOpen(false)
                                onBound?.()
                              } catch (e) {
                                toast.error(e instanceof Error ? e.message : 'Failed to bind academic editor')
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
