import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, FileText, Inbox, Loader2, RotateCcw } from 'lucide-react'
import SiteHeader from '@/components/layout/SiteHeader'
import QueryProvider from '@/components/providers/QueryProvider'
import { Badge } from '@/components/ui/badge'
import { Button, buttonVariants } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { editorService } from '@/services/editorService'
import { AssignAEModal } from '@/components/AssignAEModal'
import { getAssistantEditors } from '@/services/assistantEditorsCache'

interface Manuscript {
  id: string
  title: string
  status?: string
  created_at?: string
  pre_check_status: string
}

function formatDate(value?: string) {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  return d.toLocaleString('zh-CN', { hour12: false })
}

function renderIntakeStatus(status?: string) {
  const normalized = (status || '').toLowerCase()
  if (normalized === 'intake') {
    return <Badge variant="secondary">intake</Badge>
  }
  if (!normalized) {
    return <Badge variant="secondary">intake</Badge>
  }
  return <Badge variant="outline">{normalized}</Badge>
}

export default function MEIntakePage() {
  const [manuscripts, setManuscripts] = useState<Manuscript[]>([])
  const [loading, setLoading] = useState(true)
  const [assignModalOpen, setAssignModalOpen] = useState(false)
  const [selectedManuscriptId, setSelectedManuscriptId] = useState<string | null>(null)
  const [returnModalOpen, setReturnModalOpen] = useState(false)
  const [returning, setReturning] = useState(false)
  const [returnComment, setReturnComment] = useState('')
  const [returnError, setReturnError] = useState('')
  const [returnTarget, setReturnTarget] = useState<{ id: string; title: string } | null>(null)

  const fetchQueue = async () => {
    setLoading(true)
    try {
      const data = await editorService.getIntakeQueue()
      setManuscripts(data as unknown as Manuscript[])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchQueue()
    // 中文注释：预取 AE 列表，避免首次点击 Assign AE 时才触发网络请求导致卡顿
    void getAssistantEditors().catch(() => {})
  }, [])

  const openAssignModal = (id: string) => {
    setSelectedManuscriptId(id)
    setAssignModalOpen(true)
  }

  const openReturnModal = (target: { id: string; title: string }) => {
    setReturnTarget(target)
    setReturnComment('')
    setReturnError('')
    setReturnModalOpen(true)
  }

  const closeReturnModal = () => {
    if (returning) return
    setReturnModalOpen(false)
    setReturnTarget(null)
    setReturnComment('')
    setReturnError('')
  }

  const submitReturn = async () => {
    if (!returnTarget) return
    const comment = returnComment.trim()
    if (!comment) {
      setReturnError('请填写退回原因，作者需要据此修订稿件。')
      return
    }
    setReturning(true)
    setReturnError('')
    try {
      await editorService.submitIntakeRevision(returnTarget.id, comment)
      closeReturnModal()
      await fetchQueue()
    } catch (err) {
      setReturnError(err instanceof Error ? err.message : '提交失败，请重试')
    } finally {
      setReturning(false)
    }
  }

  return (
    <QueryProvider>
      <div className="min-h-screen bg-slate-50">
        <SiteHeader />
        <main className="mx-auto w-[96vw] max-w-screen-2xl px-4 py-10 sm:px-6 lg:px-8 space-y-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="mt-1 rounded-xl bg-white p-2 shadow-sm ring-1 ring-slate-200">
                <Inbox className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h1 className="text-3xl font-serif font-bold text-slate-900 tracking-tight">Managing Editor Intake Queue</h1>
                <p className="mt-1 text-slate-500 font-medium">ME 先完成入口技术筛查，再决定退回作者或分配 AE 进入外审准备。</p>
              </div>
            </div>

            <Link href="/dashboard?tab=managing_editor" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
              <ArrowLeft className="h-4 w-4" />
              返回编辑台
            </Link>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full table-fixed">
              <thead className="bg-slate-50/70">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Title</th>
                  <th className="w-48 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Submitted</th>
                  <th className="w-40 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Stage</th>
                  <th className="w-[360px] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-10 text-center text-sm text-slate-500">Loading...</td>
                  </tr>
                ) : manuscripts.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-10 text-center text-sm text-slate-500">No manuscripts in intake.</td>
                  </tr>
                ) : (
                  manuscripts.map((m) => (
                    <tr key={m.id} className="border-t border-slate-100 hover:bg-slate-50/60">
                      <td className="px-4 py-3 text-sm text-slate-900">
                        <div className="line-clamp-2 font-medium">{m.title}</div>
                        <div className="mt-1 font-mono text-[11px] text-slate-500">{m.id}</div>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600">{formatDate(m.created_at)}</td>
                      <td className="px-4 py-3 text-sm text-slate-600">{renderIntakeStatus(m.pre_check_status)}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <Link
                            href={`/editor/manuscript/${m.id}`}
                            target="_blank"
                            className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'gap-1.5')}
                          >
                            <FileText className="h-4 w-4" />
                            查看稿件包
                          </Link>
                          <Button size="sm" onClick={() => openAssignModal(m.id)}>
                            Assign AE
                          </Button>
                          <Button size="sm" variant="destructive" onClick={() => openReturnModal({ id: m.id, title: m.title })}>
                            <RotateCcw className="h-4 w-4" />
                            技术退回
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {selectedManuscriptId && (
            <AssignAEModal
              isOpen={assignModalOpen}
              onClose={() => setAssignModalOpen(false)}
              manuscriptId={selectedManuscriptId}
              onAssignSuccess={fetchQueue}
            />
          )}

          <Dialog open={returnModalOpen} onOpenChange={(open) => (!open ? closeReturnModal() : setReturnModalOpen(true))}>
            <DialogContent className="max-w-xl">
              <DialogHeader>
                <DialogTitle>技术退回作者</DialogTitle>
                <DialogDescription>
                  稿件将从入口审查直接退回作者修订，不进入 AE 外审阶段。请给出可执行的修改意见。
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-3">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="text-xs text-slate-500">Manuscript</div>
                  <div className="mt-1 text-sm font-medium text-slate-900">{returnTarget?.title || '-'}</div>
                </div>
                <div>
                  <div className="mb-2 text-sm font-medium text-slate-700">
                    退回理由 <span className="text-red-600">*</span>
                  </div>
                  <Textarea
                    value={returnComment}
                    onChange={(e) => setReturnComment(e.target.value)}
                    placeholder="例如：参考文献格式不符合期刊规范，伦理声明缺失，请按模板补齐后重投。"
                    className="min-h-[140px]"
                    disabled={returning}
                  />
                  {returnError ? <div className="mt-2 text-xs text-red-600">{returnError}</div> : null}
                </div>
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={closeReturnModal} disabled={returning}>
                  取消
                </Button>
                <Button variant="destructive" onClick={submitReturn} disabled={returning}>
                  {returning ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  确认退回
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </main>
      </div>
    </QueryProvider>
  )
}
