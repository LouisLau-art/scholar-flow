import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, ClipboardCheck } from 'lucide-react'
import { format } from 'date-fns'

import SiteHeader from '@/components/layout/SiteHeader'
import QueryProvider from '@/components/providers/QueryProvider'
import { Button, buttonVariants } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { editorService } from '@/services/editorService'
import { getStatusLabel } from '@/lib/statusStyles'
import type { TechnicalDecision } from '@/types/precheck'

interface Manuscript {
  id: string
  status?: string
  title: string
  created_at?: string | null
  updated_at?: string | null
  pre_check_status?: string | null
  workspace_bucket?: 'technical' | 'under_review' | 'revision_followup' | 'decision' | 'other'
  owner?: { id?: string; full_name?: string | null; email?: string | null } | null
  journal?: { title?: string | null; slug?: string | null } | null
}

type WorkspaceBucket = 'technical' | 'under_review' | 'revision_followup' | 'decision' | 'other'

type SectionMeta = {
  label: string
  description: string
}

const SECTION_ORDER: WorkspaceBucket[] = ['technical', 'under_review', 'revision_followup', 'decision', 'other']

const SECTION_META: Record<WorkspaceBucket, SectionMeta> = {
  technical: {
    label: '待发起外审',
    description: 'ME 已分配给你的新稿件：完成技术闭环后进入外审。',
  },
  under_review: {
    label: '外审进行中',
    description: '正在邀审/催审/补邀的稿件。',
  },
  revision_followup: {
    label: '修回待跟进',
    description: '作者修回后等待 AE 判断是否二审或继续推进。',
  },
  decision: {
    label: '待决策汇总',
    description: '外审意见已齐，等待 AE 汇总提交学术决策。',
  },
  other: {
    label: '其他在办稿件',
    description: '仍归你分管但不在上述主流程节点的稿件。',
  },
}

function toMillis(value?: string | null): number {
  if (!value) return 0
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? 0 : d.getTime()
}

function fmt(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return format(d, 'yyyy/MM/dd HH:mm')
}

function deriveBucket(m: Manuscript): WorkspaceBucket {
  const explicit = m.workspace_bucket
  if (explicit && SECTION_ORDER.includes(explicit)) return explicit

  const status = String(m.status || '').toLowerCase()
  const pre = String(m.pre_check_status || '').toLowerCase()

  if (status === 'pre_check' && pre === 'technical') return 'technical'
  if (status === 'under_review') return 'under_review'
  if (status === 'resubmitted' || status === 'major_revision' || status === 'minor_revision') return 'revision_followup'
  if (status === 'decision') return 'decision'
  return 'other'
}

export default function AEWorkspacePage() {
  const [manuscripts, setManuscripts] = useState<Manuscript[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [activeMs, setActiveMs] = useState<Manuscript | null>(null)
  const [technicalDecision, setTechnicalDecision] = useState<TechnicalDecision>('pass')
  const [comment, setComment] = useState('')
  const [error, setError] = useState('')

  const fetchWorkspace = useCallback(async () => {
    setLoading(true)
    try {
      const data = await editorService.getAEWorkspace()
      setManuscripts(data as unknown as Manuscript[])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchWorkspace()
  }, [fetchWorkspace])

  const resetDialog = useCallback(() => {
    setTechnicalDecision('pass')
    setComment('')
    setError('')
    setActiveMs(null)
    setDialogOpen(false)
  }, [])

  const openSubmitCheckDialog = useCallback((manuscript: Manuscript) => {
    setTechnicalDecision('pass')
    setActiveMs(manuscript)
    setComment('')
    setError('')
    setDialogOpen(true)
  }, [])

  const handleSubmitCheck = useCallback(async () => {
    if (!activeMs?.id) return
    setError('')
    if (technicalDecision === 'revision' && !comment.trim()) {
      setError('技术退回必须填写说明，方便作者修回。')
      return
    }
    setSubmitting(true)
    try {
      await editorService.submitTechnicalCheck(activeMs.id, {
        decision: technicalDecision,
        comment: comment.trim() || undefined,
      })
      resetDialog()
      fetchWorkspace()
    } catch (e) {
      setError(e instanceof Error ? e.message : '提交技术审查失败')
    } finally {
      setSubmitting(false)
    }
  }, [activeMs?.id, comment, fetchWorkspace, resetDialog, technicalDecision])

  const groupedSections = useMemo(() => {
    const sorted = [...manuscripts].sort((a, b) => {
      const updatedDiff = toMillis(b.updated_at) - toMillis(a.updated_at)
      if (updatedDiff !== 0) return updatedDiff
      return toMillis(b.created_at) - toMillis(a.created_at)
    })

    const buckets: Record<WorkspaceBucket, Manuscript[]> = {
      technical: [],
      under_review: [],
      revision_followup: [],
      decision: [],
      other: [],
    }

    for (const manuscript of sorted) {
      buckets[deriveBucket(manuscript)].push(manuscript)
    }

    return SECTION_ORDER.map((key) => ({
      key,
      meta: SECTION_META[key],
      items: buckets[key],
    })).filter((section) => section.items.length > 0)
  }, [manuscripts])

  return (
    <QueryProvider>
      <div className="min-h-screen bg-slate-50">
        <SiteHeader />
        <main className="mx-auto w-[96vw] max-w-screen-2xl space-y-6 px-4 py-10 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="mt-1 rounded-xl bg-white p-2 shadow-sm ring-1 ring-slate-200">
                <ClipboardCheck className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h1 className="text-3xl font-serif font-bold tracking-tight text-slate-900">Assistant Editor Workspace</h1>
                <p className="mt-1 font-medium text-slate-500">
                  展示你分管的在办稿件：技术发起外审、外审跟进、修回推进与决策汇总。
                </p>
              </div>
            </div>

            <Link href="/dashboard?tab=assistant_editor" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
              <ArrowLeft className="h-4 w-4" />
              返回编辑台
            </Link>
          </div>

          {loading ? (
            <div className="rounded-xl border border-slate-200 bg-white px-4 py-10 text-center text-sm text-slate-500">Loading...</div>
          ) : groupedSections.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-white px-4 py-10 text-center text-sm text-slate-500">
              No manuscripts assigned.
            </div>
          ) : (
            groupedSections.map((section) => (
              <section key={section.key} className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="border-b border-slate-200 bg-slate-50/70 px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-base font-semibold text-slate-900">{section.meta.label}</h2>
                    <Badge variant="secondary">{section.items.length}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{section.meta.description}</p>
                </div>

                <Table>
                  <TableHeader className="bg-slate-50/40">
                    <TableRow>
                      <TableHead className="min-w-[420px]">Title</TableHead>
                      <TableHead className="min-w-[160px]">Status</TableHead>
                      <TableHead className="min-w-[170px]">Updated</TableHead>
                      <TableHead className="min-w-[180px]">Owner</TableHead>
                      <TableHead className="min-w-[160px]">Journal</TableHead>
                      <TableHead className="min-w-[260px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {section.items.map((m) => {
                      const detailHref = `/editor/manuscript/${encodeURIComponent(m.id)}?from=workspace`
                      const bucket = deriveBucket(m)

                      return (
                        <TableRow key={m.id} className="hover:bg-slate-50/70">
                          <TableCell>
                            <Link href={detailHref} className="text-sm font-semibold text-slate-900 hover:text-primary hover:underline">
                              {m.title || 'Untitled Manuscript'}
                            </Link>
                            <div className="mt-1 text-xs font-mono text-slate-500">{m.id}</div>
                          </TableCell>

                          <TableCell>
                            <div className="flex flex-wrap items-center gap-1.5">
                              <Badge variant="outline">{getStatusLabel(m.status || 'unknown')}</Badge>
                              {m.pre_check_status ? <Badge variant="secondary">{m.pre_check_status}</Badge> : null}
                            </div>
                          </TableCell>

                          <TableCell className="text-sm text-slate-700">{fmt(m.updated_at || m.created_at)}</TableCell>
                          <TableCell className="text-sm text-slate-700">{m.owner?.full_name || m.owner?.email || '—'}</TableCell>
                          <TableCell className="text-sm text-slate-700">{m.journal?.title || '—'}</TableCell>

                          <TableCell>
                            <div className="flex flex-wrap items-center gap-2">
                              {bucket === 'technical' ? (
                                <Button size="sm" onClick={() => openSubmitCheckDialog(m)}>
                                  Submit Check
                                </Button>
                              ) : null}

                              <Link
                                href={detailHref}
                                className={cn(buttonVariants({ variant: bucket === 'technical' ? 'outline' : 'secondary', size: 'sm' }))}
                              >
                                {bucket === 'under_review'
                                  ? 'Manage Reviewers'
                                  : bucket === 'revision_followup'
                                    ? 'Review Revision'
                                    : bucket === 'decision'
                                      ? 'Prepare Decision'
                                      : 'Open Details'}
                              </Link>
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </section>
            ))
          )}
        </main>

        <Dialog
          open={dialogOpen}
          onOpenChange={(open) => {
            if (!open) resetDialog()
            else setDialogOpen(true)
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Submit Technical Check</DialogTitle>
              <DialogDescription>
                稿件：{activeMs?.title || '—'}。选择下一步：可直接发起外审、可选送 Academic 预审，或技术退回作者。
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3">
              <div>
                <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Next Step</div>
                <Select value={technicalDecision} onValueChange={(v) => setTechnicalDecision(v as TechnicalDecision)}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择技术检查后的流转" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pass">发起外审（进入 under_review）</SelectItem>
                    <SelectItem value="academic">送 Academic 预审（可选）</SelectItem>
                    <SelectItem value="revision">技术退回作者（需填写说明）</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Comment (optional)</div>
                <Textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder={
                    technicalDecision === 'revision'
                      ? '必填：明确指出作者需要修复的问题（格式、伦理、缺件等）'
                      : technicalDecision === 'academic'
                        ? '可选：补充给 Academic 预审的背景说明'
                        : '可选：补充给后续外审流程的技术备注'
                  }
                  className="min-h-[110px]"
                />
              </div>

              {error ? <div className="text-xs text-rose-600">{error}</div> : null}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={resetDialog} disabled={submitting}>
                Cancel
              </Button>
              <Button onClick={handleSubmitCheck} disabled={submitting || !activeMs?.id}>
                {submitting ? 'Submitting...' : 'Confirm'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </QueryProvider>
  )
}
