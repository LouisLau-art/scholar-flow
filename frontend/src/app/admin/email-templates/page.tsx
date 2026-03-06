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
import { adminEmailTemplateService } from '@/services/admin/emailTemplateService'
import type {
  EmailTemplate,
  EmailTemplateCreatePayload,
  EmailTemplateEventType,
  EmailTemplateUpdatePayload,
} from '@/types/email-template'

type EmailTemplateFormState = {
  template_key: string
  display_name: string
  description: string
  scene: string
  event_type: EmailTemplateEventType
  subject_template: string
  body_html_template: string
  body_text_template: string
  is_active: boolean
}

const EMPTY_FORM: EmailTemplateFormState = {
  template_key: '',
  display_name: '',
  description: '',
  scene: 'reviewer_assignment',
  event_type: 'none',
  subject_template: '',
  body_html_template: '',
  body_text_template: '',
  is_active: true,
}

function formatDate(raw?: string | null): string {
  if (!raw) return '—'
  const parsed = new Date(raw)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleString()
}

function normalizeSnake(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, '_')
    .replace(/_{2,}/g, '_')
    .replace(/^_+|_+$/g, '')
}

function toCreatePayload(form: EmailTemplateFormState): EmailTemplateCreatePayload {
  return {
    template_key: normalizeSnake(form.template_key),
    display_name: form.display_name.trim(),
    description: form.description.trim() || null,
    scene: normalizeSnake(form.scene),
    event_type: form.event_type,
    subject_template: form.subject_template.trim(),
    body_html_template: form.body_html_template.trim(),
    body_text_template: form.body_text_template.trim() || null,
    is_active: form.is_active,
  }
}

export default function EmailTemplateManagementPage() {
  const router = useRouter()
  const [verifyingRole, setVerifyingRole] = useState(true)
  const [isAdmin, setIsAdmin] = useState(false)

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [includeInactive, setIncludeInactive] = useState(true)
  const [sceneFilter, setSceneFilter] = useState('')
  const [templates, setTemplates] = useState<EmailTemplate[]>([])

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<EmailTemplate | null>(null)
  const [form, setForm] = useState<EmailTemplateFormState>(EMPTY_FORM)

  const activeCount = useMemo(
    () => templates.filter((item) => item.is_active !== false).length,
    [templates]
  )

  const resetForm = () => {
    setEditingTemplate(null)
    setForm(EMPTY_FORM)
  }

  const loadTemplates = useCallback(async () => {
    setLoading(true)
    try {
      const rows = await adminEmailTemplateService.list({
        includeInactive,
        scene: sceneFilter.trim() || undefined,
      })
      setTemplates(rows)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load email templates'
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }, [includeInactive, sceneFilter])

  useEffect(() => {
    let cancelled = false

    const checkAdminAccess = async () => {
      try {
        const token = await authService.getAccessToken()
        if (!token) {
          router.replace('/login')
          return
        }

        const profileRes = await fetch('/api/v1/user/profile', {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!profileRes.ok) {
          if (profileRes.status === 401) {
            router.replace('/login')
          } else {
            router.replace('/dashboard')
          }
          return
        }

        const profileJson = await profileRes.json().catch(() => null)
        const roles = ((profileJson?.data?.roles || []) as string[]).map((item) =>
          String(item || '').toLowerCase()
        )
        if (!roles.includes('admin')) {
          toast.error('Access denied: admin only.')
          router.replace('/dashboard')
          return
        }
        if (!cancelled) setIsAdmin(true)
      } catch (error) {
        console.error('[EmailTemplateManagement] auth check failed:', error)
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
    loadTemplates()
  }, [isAdmin, loadTemplates])

  const openCreateDialog = () => {
    resetForm()
    setDialogOpen(true)
  }

  const openEditDialog = (template: EmailTemplate) => {
    setEditingTemplate(template)
    setForm({
      template_key: template.template_key || '',
      display_name: template.display_name || '',
      description: template.description || '',
      scene: template.scene || 'reviewer_assignment',
      event_type: template.event_type || 'none',
      subject_template: template.subject_template || '',
      body_html_template: template.body_html_template || '',
      body_text_template: template.body_text_template || '',
      is_active: template.is_active !== false,
    })
    setDialogOpen(true)
  }

  const handleDialogSubmit = async () => {
    const payload = toCreatePayload(form)
    if (!payload.template_key) {
      toast.error('Template key is required')
      return
    }
    if (!payload.display_name) {
      toast.error('Display name is required')
      return
    }
    if (!payload.scene) {
      toast.error('Scene is required')
      return
    }
    if (!payload.subject_template || !payload.body_html_template) {
      toast.error('Subject / HTML template are required')
      return
    }

    setSaving(true)
    try {
      if (editingTemplate?.id) {
        const updatePayload: EmailTemplateUpdatePayload = {
          template_key: payload.template_key,
          display_name: payload.display_name,
          description: payload.description,
          scene: payload.scene,
          event_type: payload.event_type,
          subject_template: payload.subject_template,
          body_html_template: payload.body_html_template,
          body_text_template: payload.body_text_template,
          is_active: payload.is_active,
        }
        await adminEmailTemplateService.update(editingTemplate.id, updatePayload)
        toast.success('Email template updated')
      } else {
        await adminEmailTemplateService.create(payload)
        toast.success('Email template created')
      }
      setDialogOpen(false)
      resetForm()
      await loadTemplates()
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Save failed'
      toast.error(message)
    } finally {
      setSaving(false)
    }
  }

  const handleDeactivate = async (template: EmailTemplate) => {
    if (!template.id) return
    setSaving(true)
    try {
      await adminEmailTemplateService.deactivate(template.id)
      toast.success(`Template "${template.display_name}" deactivated`)
      await loadTemplates()
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Deactivate failed'
      toast.error(message)
    } finally {
      setSaving(false)
    }
  }

  const handleReactivate = async (template: EmailTemplate) => {
    if (!template.id) return
    setSaving(true)
    try {
      await adminEmailTemplateService.update(template.id, { is_active: true })
      toast.success(`Template "${template.display_name}" re-activated`)
      await loadTemplates()
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
        <div className="flex min-h-[50vh] items-center justify-center gap-3 text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          Verifying admin access...
        </div>
      )
    }

    if (!isAdmin) {
      return (
        <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-muted-foreground">
          <ShieldAlert className="h-10 w-10 text-destructive" />
          <p className="text-lg font-semibold text-foreground">Access Denied</p>
          <p className="text-sm">This page is only available to administrators.</p>
          <Button asChild variant="outline">
            <Link href="/dashboard">Back to dashboard</Link>
          </Button>
        </div>
      )
    }

    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">Templates</div>
            <div className="mt-2 text-2xl font-semibold text-foreground">{templates.length}</div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">Active</div>
            <div className="mt-2 text-2xl font-semibold text-foreground">{activeCount}</div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">Variables</div>
            <div className="mt-2 text-sm text-muted-foreground">
              推荐占位符: <code>{'{{ journal_title }}'}</code>, <code>{'{{ reviewer_name }}'}</code>,{' '}
              <code>{'{{ manuscript_title }}'}</code>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4 text-sm text-muted-foreground">
            scene 例子: reviewer_assignment / author_notification / decision
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={openCreateDialog} className="gap-2">
            <Plus className="h-4 w-4" />
            New Template
          </Button>
          <Button variant={includeInactive ? 'secondary' : 'outline'} onClick={() => setIncludeInactive((prev) => !prev)}>
            {includeInactive ? 'Hide Inactive' : 'Show Inactive'}
          </Button>
          <Input
            className="w-full md:w-72"
            placeholder="Filter by scene (e.g. reviewer_assignment)"
            value={sceneFilter}
            onChange={(event) => setSceneFilter(event.target.value)}
          />
          <Button variant="outline" onClick={() => void loadTemplates()} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Refresh'}
          </Button>
        </div>

        <div className="rounded-xl border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Template</TableHead>
                <TableHead>Scene</TableHead>
                <TableHead>Event</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6}>
                    <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading templates...
                    </div>
                  </TableCell>
                </TableRow>
              ) : templates.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6}>
                    <div className="py-6 text-center text-sm text-muted-foreground">
                      No templates found.
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                templates.map((template) => (
                  <TableRow key={template.id}>
                    <TableCell>
                      <div className="font-medium text-foreground">{template.display_name}</div>
                      <div className="font-mono text-xs text-muted-foreground">{template.template_key}</div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{template.scene}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{template.event_type}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={template.is_active ? 'default' : 'outline'}>
                        {template.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{formatDate(template.updated_at)}</TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-2">
                        <Button size="sm" variant="outline" onClick={() => openEditDialog(template)} disabled={saving}>
                          <Pencil className="mr-1.5 h-3.5 w-3.5" />
                          Edit
                        </Button>
                        {template.is_active ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => void handleDeactivate(template)}
                            disabled={saving}
                          >
                            <Power className="mr-1.5 h-3.5 w-3.5" />
                            Deactivate
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => void handleReactivate(template)}
                            disabled={saving}
                          >
                            <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
                            Reactivate
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    )
  })()

  return (
    <div className="min-h-screen bg-muted/30">
      <SiteHeader />
      <main className="mx-auto w-full max-w-7xl px-4 py-8 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Email Template Management</h1>
            <p className="text-sm text-muted-foreground">
              Admin-managed global templates used by editorial email workflows.
            </p>
          </div>
          <Button asChild variant="outline">
            <Link href="/dashboard">Back to dashboard</Link>
          </Button>
        </div>
        {content}
      </main>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingTemplate ? 'Edit Email Template' : 'Create Email Template'}</DialogTitle>
            <DialogDescription>
              Use Jinja placeholders such as <code>{'{{ journal_title }}'}</code> to auto-fill journal data.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="template-key">Template Key</Label>
                <Input
                  id="template-key"
                  value={form.template_key}
                  disabled={saving}
                  onChange={(event) => setForm((prev) => ({ ...prev, template_key: event.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="display-name">Display Name</Label>
                <Input
                  id="display-name"
                  value={form.display_name}
                  disabled={saving}
                  onChange={(event) => setForm((prev) => ({ ...prev, display_name: event.target.value }))}
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="scene">Scene</Label>
                <Input
                  id="scene"
                  value={form.scene}
                  disabled={saving}
                  onChange={(event) => setForm((prev) => ({ ...prev, scene: event.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="event-type">Event Type</Label>
                <select
                  id="event-type"
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={form.event_type}
                  disabled={saving}
                  onChange={(event) =>
                    setForm((prev) => ({
                      ...prev,
                      event_type: event.target.value as EmailTemplateEventType,
                    }))
                  }
                >
                  <option value="none">none</option>
                  <option value="invitation">invitation</option>
                  <option value="reminder">reminder</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="is-active">Status</Label>
                <select
                  id="is-active"
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={form.is_active ? 'active' : 'inactive'}
                  disabled={saving}
                  onChange={(event) =>
                    setForm((prev) => ({ ...prev, is_active: event.target.value === 'active' }))
                  }
                >
                  <option value="active">active</option>
                  <option value="inactive">inactive</option>
                </select>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={form.description}
                disabled={saving}
                rows={2}
                onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="subject-template">Subject Template</Label>
              <Input
                id="subject-template"
                value={form.subject_template}
                disabled={saving}
                onChange={(event) => setForm((prev) => ({ ...prev, subject_template: event.target.value }))}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="html-template">HTML Template</Label>
              <Textarea
                id="html-template"
                className="min-h-[180px]"
                value={form.body_html_template}
                disabled={saving}
                onChange={(event) => setForm((prev) => ({ ...prev, body_html_template: event.target.value }))}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="text-template">Text Template (Optional)</Label>
              <Textarea
                id="text-template"
                className="min-h-[110px]"
                value={form.body_text_template}
                disabled={saving}
                onChange={(event) => setForm((prev) => ({ ...prev, body_text_template: event.target.value }))}
              />
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
            <Button onClick={() => void handleDialogSubmit()} disabled={saving}>
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {editingTemplate ? 'Save Changes' : 'Create Template'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
