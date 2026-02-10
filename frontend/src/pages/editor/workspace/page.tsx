import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, ClipboardCheck } from 'lucide-react'
import SiteHeader from '@/components/layout/SiteHeader'
import QueryProvider from '@/components/providers/QueryProvider'
import { Button, buttonVariants } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { format } from 'date-fns'

interface Manuscript {
  id: string
  status?: string
  title: string
  created_at?: string | null
  updated_at?: string | null
  pre_check_status: string
  owner?: { id?: string; full_name?: string | null; email?: string | null } | null
  journal?: { title?: string | null; slug?: string | null } | null
}

export default function AEWorkspacePage() {
  const [manuscripts, setManuscripts] = useState<Manuscript[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [activeMs, setActiveMs] = useState<Manuscript | null>(null)
  const [decision, setDecision] = useState<'pass' | 'revision'>('pass')
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
    setDecision('pass')
    setComment('')
    setError('')
    setActiveMs(null)
    setDialogOpen(false)
  }, [])

  const openDialog = useCallback((manuscript: Manuscript, presetDecision: 'pass' | 'revision') => {
    setActiveMs(manuscript)
    setDecision(presetDecision)
    setComment('')
    setError('')
    setDialogOpen(true)
  }, [])

  const handleSubmitCheck = useCallback(async () => {
    if (!activeMs?.id) return
    setError('')
    setSubmitting(true)
    try {
      if (decision === 'revision' && !comment.trim()) {
        setError('技术退回必须填写反馈意见。')
        return
      }
      await editorService.submitTechnicalCheck(activeMs.id, { decision, comment: comment.trim() || undefined })
      resetDialog()
      fetchWorkspace()
    } catch (e) {
      setError(e instanceof Error ? e.message : '提交技术审查失败')
    } finally {
      setSubmitting(false)
    }
  }, [activeMs?.id, comment, decision, fetchWorkspace, resetDialog])

  const dialogDecisionLabel = useMemo(() => {
    return decision === 'pass' ? '发起外审 (进入 under_review)' : '技术退回作者 (进入 minor_revision)'
  }, [decision])

  return (
    <QueryProvider>
      <div className="min-h-screen bg-slate-50">
        <SiteHeader />
        <main className="mx-auto w-[96vw] max-w-screen-2xl px-4 py-10 sm:px-6 lg:px-8 space-y-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="mt-1 rounded-xl bg-white p-2 shadow-sm ring-1 ring-slate-200">
                <ClipboardCheck className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h1 className="text-3xl font-serif font-bold text-slate-900 tracking-tight">Assistant Editor Workspace</h1>
                <p className="mt-1 text-slate-500 font-medium">
                  这里处理 ME 已分配稿件的技术闭环：通过后进入外审，或退回作者补充。
                </p>
              </div>
            </div>

            <Link href="/dashboard?tab=assistant_editor" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
              <ArrowLeft className="h-4 w-4" />
              返回编辑台
            </Link>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <Table>
              <TableHeader className="bg-slate-50/70">
                <TableRow>
                  <TableHead className="min-w-[420px]">Title</TableHead>
                  <TableHead className="min-w-[180px]">Owner</TableHead>
                  <TableHead className="min-w-[160px]">Journal</TableHead>
                  <TableHead className="min-w-[180px]">Submitted</TableHead>
                  <TableHead className="min-w-[120px]">Stage</TableHead>
                  <TableHead className="min-w-[350px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="py-10 text-center text-sm text-slate-500">
                      Loading...
                    </TableCell>
                  </TableRow>
                ) : manuscripts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="py-10 text-center text-sm text-slate-500">
                      No manuscripts assigned.
                    </TableCell>
                  </TableRow>
                ) : (
                  manuscripts.map((m) => (
                    <TableRow key={m.id} className="hover:bg-slate-50/70">
                      <TableCell>
                        <Link
                          href={`/editor/manuscript/${encodeURIComponent(m.id)}?from=workspace`}
                          className="text-sm font-semibold text-slate-900 hover:text-primary hover:underline"
                        >
                          {m.title || 'Untitled Manuscript'}
                        </Link>
                        <div className="mt-1 text-xs font-mono text-slate-500">{m.id}</div>
                      </TableCell>
                      <TableCell className="text-sm text-slate-700">
                        {m.owner?.full_name || m.owner?.email || '—'}
                      </TableCell>
                      <TableCell className="text-sm text-slate-700">{m.journal?.title || '—'}</TableCell>
                      <TableCell className="text-sm text-slate-700">
                        {m.created_at ? format(new Date(m.created_at), 'yyyy/MM/dd HH:mm') : '—'}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{m.pre_check_status || 'technical'}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap items-center gap-2">
                          <Link
                            href={`/editor/manuscript/${encodeURIComponent(m.id)}?from=workspace`}
                            className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}
                          >
                            查看稿件包
                          </Link>
                          <Button size="sm" onClick={() => openDialog(m, 'pass')}>
                            发起外审
                          </Button>
                          <Button variant="destructive" size="sm" onClick={() => openDialog(m, 'revision')}>
                            技术退回
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
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
              <DialogTitle>提交技术审查结果</DialogTitle>
              <DialogDescription>
                当前稿件：{activeMs?.title || '—'}。AE 在此阶段只做技术闭环，结果会进入外审或退回作者。
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3">
              <div>
                <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Decision</div>
                <Select value={decision} onValueChange={(value) => setDecision(value as 'pass' | 'revision')}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pass">发起外审 (under_review)</SelectItem>
                    <SelectItem value="revision">技术退回作者 (minor_revision)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Comment {decision === 'revision' ? '(required)' : '(optional)'}
                </div>
                <Textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder={
                    decision === 'revision'
                      ? '请写明作者需要补充/修正的技术项（必填）'
                      : '可选：补充技术审查备注'
                  }
                  className="min-h-[110px]"
                />
              </div>

              <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
                目标流转：<span className="font-semibold text-slate-800">{dialogDecisionLabel}</span>
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
