import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { AlertTriangle, ArrowLeft, Inbox, Loader2, RotateCcw, Search } from 'lucide-react'
import SiteHeader from '@/components/layout/SiteHeader'
import QueryProvider from '@/components/providers/QueryProvider'
import { Badge } from '@/components/ui/badge'
import { Button, buttonVariants } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
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
  author?: { id: string; full_name?: string; email?: string; affiliation?: string } | null
  owner?: { id: string; full_name?: string; email?: string } | null
  journal?: { title?: string; slug?: string } | null
  intake_priority?: 'high' | 'normal'
  intake_elapsed_hours?: number | null
  is_overdue?: boolean
  pre_check_status: string
  intake_actionable?: boolean
  waiting_resubmit?: boolean
  waiting_resubmit_at?: string | null
  waiting_resubmit_reason?: string | null
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
    return <Badge variant="secondary">入口审查</Badge>
  }
  if (normalized === 'awaiting_resubmit') {
    return (
      <Badge variant="outline" className="border-slate-300 bg-slate-100 text-slate-600">
        等待作者修回
      </Badge>
    )
  }
  if (!normalized) {
    return <Badge variant="secondary">入口审查</Badge>
  }
  return <Badge variant="outline">{normalized}</Badge>
}

function renderPriority(row: Manuscript) {
  if (row.waiting_resubmit) {
    return (
      <Badge variant="outline" className="border-slate-300 bg-slate-100 text-slate-600">
        等待作者
      </Badge>
    )
  }
  if (row.intake_priority === 'high' || row.is_overdue) {
    const hours = typeof row.intake_elapsed_hours === 'number' ? `（${row.intake_elapsed_hours}h）` : ''
    return (
      <Badge variant="destructive" className="gap-1">
        <AlertTriangle className="h-3.5 w-3.5" />
        高优先级{hours}
      </Badge>
    )
  }
  return <Badge variant="outline">正常</Badge>
}

export default function MEIntakePage() {
  const [manuscripts, setManuscripts] = useState<Manuscript[]>([])
  const [loading, setLoading] = useState(true)
  const [assignModalOpen, setAssignModalOpen] = useState(false)
  const [selectedManuscriptId, setSelectedManuscriptId] = useState<string | null>(null)
  const [queryInput, setQueryInput] = useState('')
  const [query, setQuery] = useState('')
  const [overdueOnly, setOverdueOnly] = useState(false)
  const [returnModalOpen, setReturnModalOpen] = useState(false)
  const [returning, setReturning] = useState(false)
  const [returnComment, setReturnComment] = useState('')
  const [returnConfirmText, setReturnConfirmText] = useState('')
  const [returnError, setReturnError] = useState('')
  const [returnTarget, setReturnTarget] = useState<{ id: string; title: string } | null>(null)
  const aePrefetchedRef = useRef(false)

  const fetchQueue = useCallback(async () => {
    setLoading(true)
    try {
      const data = await editorService.getIntakeQueue(1, 100, { q: query || undefined, overdueOnly })
      setManuscripts(data as unknown as Manuscript[])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [query, overdueOnly])

  useEffect(() => {
    void fetchQueue()
  }, [fetchQueue])

  useEffect(() => {
    if (aePrefetchedRef.current) return
    aePrefetchedRef.current = true
    // 中文注释：将 AE 预取延后到首屏列表请求之后，避免首屏并发请求拖慢 Intake 列表出现速度。
    setTimeout(() => {
      void getAssistantEditors().catch(() => {})
    }, 600)
  }, [])

  const openAssignModal = (id: string) => {
    setSelectedManuscriptId(id)
    setAssignModalOpen(true)
  }

  const openReturnModal = (target: { id: string; title: string }) => {
    setReturnTarget(target)
    setReturnComment('')
    setReturnConfirmText('')
    setReturnError('')
    setReturnModalOpen(true)
  }

  const closeReturnModal = () => {
    if (returning) return
    setReturnModalOpen(false)
    setReturnTarget(null)
    setReturnComment('')
    setReturnConfirmText('')
    setReturnError('')
  }

  const submitReturn = async () => {
    if (!returnTarget) return
    const comment = returnComment.trim()
    if (!comment) {
      setReturnError('请填写退回原因，作者需要据此修订稿件。')
      return
    }
    if (returnConfirmText.trim() !== '退回') {
      setReturnError('请输入“退回”以确认该高风险操作。')
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

  const applySearch = () => {
    setQuery(queryInput.trim())
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
                <p className="mt-1 text-slate-500 font-medium">
                  ME 先完成入口技术筛查，再决定退回作者或分配 AE 进入外审准备。技术退回稿会以灰态保留，直至作者修回。
                </p>
              </div>
            </div>

            <Link href="/dashboard?tab=managing_editor" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
              <ArrowLeft className="h-4 w-4" />
              返回编辑台
            </Link>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="grid gap-3 md:grid-cols-[1fr_auto_auto] md:items-center">
              <div className="flex gap-2">
                <Input
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') applySearch()
                  }}
                  placeholder="搜索标题 / UUID / 作者 / 期刊"
                />
                <Button variant="outline" onClick={applySearch} className="gap-1.5">
                  <Search className="h-4 w-4" />
                  搜索
                </Button>
              </div>
              <Button variant={overdueOnly ? 'default' : 'outline'} onClick={() => setOverdueOnly((v) => !v)}>
                {overdueOnly ? '仅看高优先级: 开' : '仅看高优先级: 关'}
              </Button>
              {(query || overdueOnly) && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    setQueryInput('')
                    setQuery('')
                    setOverdueOnly(false)
                  }}
                >
                  清空筛选
                </Button>
              )}
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-[1200px] w-full table-auto">
              <thead className="bg-slate-50/70">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Title</th>
                  <th className="w-52 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Journal</th>
                  <th className="w-48 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Author</th>
                  <th className="w-48 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Submitted</th>
                  <th className="w-44 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Priority</th>
                  <th className="w-40 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Stage</th>
                  <th className="w-[300px] px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-sm text-slate-500">Loading...</td>
                  </tr>
                ) : manuscripts.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-sm text-slate-500">No manuscripts in intake.</td>
                  </tr>
                ) : (
                  manuscripts.map((m) => (
                    <tr
                      key={m.id}
                      className={cn(
                        'border-t border-slate-100',
                        m.waiting_resubmit ? 'bg-slate-50/70 text-slate-500' : 'hover:bg-slate-50/60'
                      )}
                    >
                      <td className="px-4 py-3 text-sm text-slate-900">
                        <Link
                          href={`/editor/manuscript/${m.id}?from=intake`}
                          className={cn(
                            'line-clamp-2 font-medium',
                            m.waiting_resubmit
                              ? 'text-slate-500 hover:text-slate-700'
                              : 'text-slate-900 hover:text-primary hover:underline'
                          )}
                        >
                          {m.title}
                        </Link>
                        <div className="mt-1 font-mono text-[11px] text-slate-500">{m.id}</div>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-700">{m.journal?.title || '-'}</td>
                      <td className="px-4 py-3 text-sm text-slate-700">
                        {m.author?.full_name || m.author?.email || m.owner?.full_name || m.owner?.email || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600">{formatDate(m.created_at)}</td>
                      <td className="px-4 py-3 text-sm text-slate-600">{renderPriority(m)}</td>
                      <td className="px-4 py-3 text-sm text-slate-600">{renderIntakeStatus(m.pre_check_status)}</td>
                      <td className="px-4 py-3">
                        {m.intake_actionable === false || m.waiting_resubmit ? (
                          <div className="space-y-1">
                            <Badge variant="outline" className="border-slate-300 bg-slate-100 text-slate-600">
                              等待作者修回（不可操作）
                            </Badge>
                            {m.waiting_resubmit_reason ? (
                              <div className="max-w-[280px] truncate text-xs text-slate-500" title={m.waiting_resubmit_reason}>
                                退回原因：{m.waiting_resubmit_reason}
                              </div>
                            ) : null}
                          </div>
                        ) : (
                          <div className="flex flex-wrap items-center gap-2">
                            <Button size="sm" onClick={() => openAssignModal(m.id)}>
                              通过并分配 AE
                            </Button>
                            <Button size="sm" variant="destructive" onClick={() => openReturnModal({ id: m.id, title: m.title })}>
                              <RotateCcw className="h-4 w-4" />
                              技术退回
                            </Button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
              </table>
            </div>
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
                <div>
                  <div className="mb-2 text-sm font-medium text-slate-700">
                    二次确认 <span className="text-red-600">*</span>
                  </div>
                  <Input
                    value={returnConfirmText}
                    onChange={(e) => setReturnConfirmText(e.target.value)}
                    placeholder='请输入“退回”确认'
                    disabled={returning}
                  />
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
