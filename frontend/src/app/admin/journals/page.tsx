'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Loader2, ShieldAlert, Plus, Pencil, Power, RotateCcw } from 'lucide-react'
import { toast } from 'sonner'

import SiteHeader from '@/components/layout/SiteHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { authService } from '@/services/auth'
import { adminJournalService } from '@/services/admin/journalService'
import type { Journal, JournalCreatePayload, JournalUpdatePayload } from '@/types/journal'

type JournalFormState = {
  title: string
  slug: string
  description: string
  issn: string
  impact_factor: string
  cover_url: string
  is_active: boolean
}

const EMPTY_FORM: JournalFormState = {
  title: '',
  slug: '',
  description: '',
  issn: '',
  impact_factor: '',
  cover_url: '',
  is_active: true,
}

function formatDate(raw?: string | null): string {
  if (!raw) return '—'
  const parsed = new Date(raw)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleString()
}

function normalizeSlug(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, '-')
    .replace(/-{2,}/g, '-')
    .replace(/^-+|-+$/g, '')
}

function toPayload(form: JournalFormState): JournalCreatePayload {
  const impact =
    form.impact_factor.trim() === '' ? null : Number.parseFloat(form.impact_factor.trim())
  return {
    title: form.title.trim(),
    slug: normalizeSlug(form.slug),
    description: form.description.trim() || null,
    issn: form.issn.trim() || null,
    impact_factor: Number.isFinite(impact as number) ? impact : null,
    cover_url: form.cover_url.trim() || null,
    is_active: form.is_active,
  }
}

export default function JournalManagementPage() {
  const router = useRouter()
  const [verifyingRole, setVerifyingRole] = useState(true)
  const [isAdmin, setIsAdmin] = useState(false)

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [includeInactive, setIncludeInactive] = useState(false)
  const [journals, setJournals] = useState<Journal[]>([])

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingJournal, setEditingJournal] = useState<Journal | null>(null)
  const [form, setForm] = useState<JournalFormState>(EMPTY_FORM)

  const activeCount = useMemo(
    () => journals.filter((item) => item.is_active !== false).length,
    [journals]
  )

  const resetForm = () => {
    setEditingJournal(null)
    setForm(EMPTY_FORM)
  }

  const loadJournals = useCallback(async () => {
    setLoading(true)
    try {
      const rows = await adminJournalService.list(includeInactive)
      setJournals(rows)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load journals'
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }, [includeInactive])

  useEffect(() => {
    let cancelled = false

    const checkAdminAccess = async () => {
      try {
        const session = await authService.getSession()
        if (!session?.user) {
          router.replace('/login')
          return
        }
        const profile = await authService.getUserProfile()
        const roles = profile?.roles || []
        if (!roles.includes('admin')) {
          toast.error('Access denied: admin only.')
          router.replace('/dashboard')
          return
        }
        if (!cancelled) setIsAdmin(true)
      } catch (error) {
        console.error('[JournalManagement] auth check failed:', error)
        router.replace('/dashboard')
      } finally {
        if (!cancelled) setVerifyingRole(false)
      }
    }

    checkAdminAccess()
    return () => {
      cancelled = true
    }
  }, [router])

  useEffect(() => {
    if (!isAdmin) return
    loadJournals()
  }, [isAdmin, loadJournals])

  const openCreateDialog = () => {
    resetForm()
    setDialogOpen(true)
  }

  const openEditDialog = (journal: Journal) => {
    setEditingJournal(journal)
    setForm({
      title: journal.title || '',
      slug: journal.slug || '',
      description: journal.description || '',
      issn: journal.issn || '',
      impact_factor:
        journal.impact_factor === null || journal.impact_factor === undefined
          ? ''
          : String(journal.impact_factor),
      cover_url: journal.cover_url || '',
      is_active: journal.is_active !== false,
    })
    setDialogOpen(true)
  }

  const handleDialogSubmit = async () => {
    const payload = toPayload(form)
    if (!payload.title) {
      toast.error('Title is required')
      return
    }
    if (!payload.slug) {
      toast.error('Slug is required')
      return
    }

    setSaving(true)
    try {
      if (editingJournal?.id) {
        const updatePayload: JournalUpdatePayload = {
          title: payload.title,
          slug: payload.slug,
          description: payload.description,
          issn: payload.issn,
          impact_factor: payload.impact_factor,
          cover_url: payload.cover_url,
          is_active: payload.is_active,
        }
        await adminJournalService.update(editingJournal.id, updatePayload)
        toast.success('Journal updated')
      } else {
        await adminJournalService.create(payload)
        toast.success('Journal created')
      }
      setDialogOpen(false)
      resetForm()
      await loadJournals()
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Save failed'
      toast.error(message)
    } finally {
      setSaving(false)
    }
  }

  const handleDeactivate = async (journal: Journal) => {
    if (!journal.id) return
    setSaving(true)
    try {
      await adminJournalService.deactivate(journal.id)
      toast.success(`Journal "${journal.title}" deactivated`)
      await loadJournals()
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Deactivate failed'
      toast.error(message)
    } finally {
      setSaving(false)
    }
  }

  const handleReactivate = async (journal: Journal) => {
    if (!journal.id) return
    setSaving(true)
    try {
      await adminJournalService.update(journal.id, { is_active: true })
      toast.success(`Journal "${journal.title}" re-activated`)
      await loadJournals()
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Reactivate failed'
      toast.error(message)
    } finally {
      setSaving(false)
    }
  }

  const content = (() => {
    if (verifyingRole) {
      return (
        <div className="flex min-h-[50vh] items-center justify-center gap-3 text-slate-500">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
          Verifying admin access...
        </div>
      )
    }

    if (!isAdmin) {
      return (
        <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-slate-600">
          <ShieldAlert className="h-10 w-10 text-red-500" />
          <p className="text-lg font-semibold text-slate-900">Access Denied</p>
          <p>Redirecting to dashboard...</p>
        </div>
      )
    }

    return (
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Journal Management</h1>
            <p className="mt-1 text-sm text-slate-500">
              Manage journal catalog used by submission workflow and editorial scope.
            </p>
            <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
              <Badge variant="secondary">Total: {journals.length}</Badge>
              <Badge variant="outline">Active: {activeCount}</Badge>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant={includeInactive ? 'secondary' : 'outline'}
              onClick={() => setIncludeInactive((prev) => !prev)}
              disabled={loading || saving}
            >
              {includeInactive ? 'Showing All' : 'Active Only'}
            </Button>
            <Button variant="outline" onClick={loadJournals} disabled={loading || saving}>
              <RotateCcw className="h-4 w-4" />
              Refresh
            </Button>
            <Button onClick={openCreateDialog} disabled={saving}>
              <Plus className="h-4 w-4" />
              New Journal
            </Button>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Slug</TableHead>
                <TableHead>ISSN</TableHead>
                <TableHead>Impact Factor</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="py-10 text-center text-slate-500">
                    <div className="inline-flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading journals...
                    </div>
                  </TableCell>
                </TableRow>
              ) : journals.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="py-10 text-center text-slate-500">
                    No journals found. Create one to enable journal-bound submissions.
                  </TableCell>
                </TableRow>
              ) : (
                journals.map((journal) => {
                  const isActive = journal.is_active !== false
                  return (
                    <TableRow key={journal.id}>
                      <TableCell className="font-medium text-slate-900">{journal.title}</TableCell>
                      <TableCell className="font-mono text-xs text-slate-600">{journal.slug}</TableCell>
                      <TableCell>{journal.issn || '—'}</TableCell>
                      <TableCell>{journal.impact_factor ?? '—'}</TableCell>
                      <TableCell>
                        <Badge variant={isActive ? 'secondary' : 'outline'}>
                          {isActive ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-slate-500">
                        {formatDate(journal.updated_at || journal.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="inline-flex items-center gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openEditDialog(journal)}
                            disabled={saving}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                            Edit
                          </Button>
                          {isActive ? (
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => handleDeactivate(journal)}
                              disabled={saving}
                            >
                              <Power className="h-3.5 w-3.5" />
                              Deactivate
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => handleReactivate(journal)}
                              disabled={saving}
                            >
                              <RotateCcw className="h-3.5 w-3.5" />
                              Reactivate
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    )
  })()

  return (
    <div className="min-h-screen bg-slate-50">
      <SiteHeader />
      <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-4">
          <Link
            href="/dashboard?tab=admin"
            className="inline-flex items-center text-sm text-slate-600 hover:text-slate-900"
          >
            Back to Admin Dashboard
          </Link>
        </div>
        {content}
      </main>

      <Dialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open)
          if (!open) resetForm()
        }}
      >
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingJournal ? 'Edit Journal' : 'Create Journal'}</DialogTitle>
            <DialogDescription>
              Configure journal metadata used by author submission and editorial routing.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="journal-title">Title</Label>
              <Input
                id="journal-title"
                value={form.title}
                onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                placeholder="Journal of Sustainable AI"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="journal-slug">Slug</Label>
              <Input
                id="journal-slug"
                value={form.slug}
                onChange={(e) => setForm((prev) => ({ ...prev, slug: e.target.value }))}
                placeholder="journal-of-sustainable-ai"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="journal-description">Description</Label>
              <Textarea
                id="journal-description"
                rows={4}
                value={form.description}
                onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
                placeholder="Scope and editorial focus..."
              />
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="grid gap-2">
                <Label htmlFor="journal-issn">ISSN</Label>
                <Input
                  id="journal-issn"
                  value={form.issn}
                  onChange={(e) => setForm((prev) => ({ ...prev, issn: e.target.value }))}
                  placeholder="1234-5678"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="journal-impact">Impact Factor</Label>
                <Input
                  id="journal-impact"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.impact_factor}
                  onChange={(e) => setForm((prev) => ({ ...prev, impact_factor: e.target.value }))}
                  placeholder="3.50"
                />
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="journal-cover">Cover URL</Label>
              <Input
                id="journal-cover"
                value={form.cover_url}
                onChange={(e) => setForm((prev) => ({ ...prev, cover_url: e.target.value }))}
                placeholder="https://..."
              />
            </div>
            <div className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2">
              <div>
                <p className="text-sm font-medium text-slate-900">Active</p>
                <p className="text-xs text-slate-500">Inactive journals won&apos;t show in submission list.</p>
              </div>
              <Button
                type="button"
                size="sm"
                variant={form.is_active ? 'secondary' : 'outline'}
                onClick={() => setForm((prev) => ({ ...prev, is_active: !prev.is_active }))}
              >
                {form.is_active ? 'Enabled' : 'Disabled'}
              </Button>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDialogOpen(false)
                resetForm()
              }}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button onClick={handleDialogSubmit} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : editingJournal ? 'Save Changes' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
