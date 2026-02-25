'use client'

import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { EditorApi } from '@/services/editorApi'
import { AddReviewerModal, ReviewerLibraryFormValues } from '@/components/editor/AddReviewerModal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ExternalLink, Plus, Search, Trash2, Pencil } from 'lucide-react'
import type { User } from '@/types/user'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'

type ReviewerItem = User & {
  title?: string | null
  affiliation?: string | null
  homepage_url?: string | null
  research_interests?: string[]
  is_reviewer_active?: boolean
}

export function ReviewerLibraryList() {
  const [query, setQuery] = useState('')
  const [items, setItems] = useState<ReviewerItem[]>([])
  const [loading, setLoading] = useState(false)

  const [addOpen, setAddOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<ReviewerLibraryFormValues | null>(null)
  const [pendingRemove, setPendingRemove] = useState<ReviewerItem | null>(null)
  const [removingId, setRemovingId] = useState<string | null>(null)

  const refresh = async (q: string) => {
    setLoading(true)
    try {
      const res = await EditorApi.searchReviewerLibrary(q, 100)
      if (!res?.success) throw new Error(res?.detail || res?.message || 'Load failed')
      setItems((res.data || []) as ReviewerItem[])
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to load reviewer library')
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const t = setTimeout(() => void refresh(query.trim()), 250)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query])

  const rows = useMemo(() => items.filter((x) => (x as any).is_reviewer_active !== false), [items])

  const deactivate = async (id: string) => {
    setRemovingId(id)
    const toastId = toast.loading('Removing reviewer...')
    try {
      const res = await EditorApi.deactivateReviewerLibraryItem(id)
      if (!res?.success) throw new Error(res?.detail || res?.message || 'Remove failed')
      toast.success('Reviewer removed', { id: toastId })
      await refresh(query.trim())
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Remove failed', { id: toastId })
    } finally {
      setRemovingId(null)
    }
  }

  return (
    <div className="rounded-xl border border-border bg-card shadow-sm">
      <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <div className="relative w-full sm:w-[360px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search name / email / affiliation / interests..."
              className="pl-9"
            />
          </div>
          <div className="text-xs text-muted-foreground">{loading ? 'Loading…' : `${rows.length} reviewers`}</div>
        </div>
        <Button onClick={() => setAddOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Add to Library
        </Button>
      </div>

      <div className="overflow-x-auto border-t border-border">
        <table className="min-w-[900px] w-full text-sm">
          <thead className="bg-muted/60 text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-semibold">Reviewer</th>
              <th className="px-4 py-3 text-left font-semibold">Affiliation</th>
              <th className="px-4 py-3 text-left font-semibold">Interests</th>
              <th className="px-4 py-3 text-left font-semibold">Homepage</th>
              <th className="px-4 py-3 text-right font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-muted-foreground">
                  No reviewers found.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id} className="border-t border-border/60 hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-foreground">
                      {(r.title ? `${r.title} ` : '') + (r.full_name || 'Unnamed')}
                    </div>
                    <div className="text-xs text-muted-foreground">{r.email}</div>
                  </td>
                  <td className="px-4 py-3 text-foreground">{r.affiliation || '-'}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(r.research_interests || []).slice(0, 6).map((t, idx) => (
                        <span
                          key={`${r.id}-tag-${idx}`}
                          className="rounded bg-muted px-2 py-0.5 text-xs text-foreground"
                        >
                          {t}
                        </span>
                      ))}
                      {(r.research_interests || []).length > 6 && (
                        <span className="text-xs text-muted-foreground">+{(r.research_interests || []).length - 6}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {r.homepage_url ? (
                      <a
                        href={r.homepage_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-primary hover:underline"
                      >
                        Open <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-1"
                        onClick={() =>
                          setEditTarget({
                            id: r.id,
                            email: r.email,
                            full_name: r.full_name || '',
                            title: r.title || 'Dr.',
                            affiliation: r.affiliation || '',
                            homepage_url: r.homepage_url || '',
                            research_interests: r.research_interests || [],
                          })
                        }
                      >
                        <Pencil className="h-3.5 w-3.5" />
                        Edit
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        className="gap-1"
                        onClick={() => setPendingRemove(r)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Remove
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <AddReviewerModal
        open={addOpen}
        onOpenChange={setAddOpen}
        mode="create"
        onSaved={() => refresh(query.trim())}
      />

      <AddReviewerModal
        open={!!editTarget}
        onOpenChange={(next) => !next && setEditTarget(null)}
        mode="edit"
        initial={editTarget || undefined}
        onSaved={() => refresh(query.trim())}
      />

      <Dialog open={!!pendingRemove} onOpenChange={(next) => !next && setPendingRemove(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Remove reviewer?</DialogTitle>
            <DialogDescription>
              This will hide the reviewer from the library (soft delete). Existing assignments remain for audit.
            </DialogDescription>
          </DialogHeader>
          {pendingRemove && (
            <div className="rounded-lg border border-border bg-muted/50 p-3 text-sm">
              <div className="font-medium text-foreground">
                {(pendingRemove.title ? `${pendingRemove.title} ` : '') + (pendingRemove.full_name || 'Unnamed')}
              </div>
              <div className="text-xs text-muted-foreground">{pendingRemove.email}</div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingRemove(null)} disabled={!!removingId}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (!pendingRemove) return
                const id = pendingRemove.id
                setPendingRemove(null)
                await deactivate(id)
              }}
              disabled={!!removingId}
            >
              {removingId ? 'Removing...' : 'Remove'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
