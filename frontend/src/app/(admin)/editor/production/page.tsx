'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Loader2, Workflow } from 'lucide-react'
import SiteHeader from '@/components/layout/SiteHeader'
import QueryProvider from '@/components/providers/QueryProvider'
import { Badge } from '@/components/ui/badge'
import { Button, buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { EditorApi } from '@/services/editorApi'

type ProductionQueueItem = {
  manuscript: {
    id: string
    title: string
    status?: string | null
    journal?: { id?: string | null; title?: string | null; slug?: string | null } | null
  }
  cycle: {
    id: string
    cycle_no?: number | null
    status?: string | null
    proof_due_at?: string | null
    updated_at?: string | null
  }
  action_url: string
}

function formatDate(value?: string | null) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('zh-CN', { hour12: false })
}

function statusBadge(status?: string | null) {
  const s = String(status || '').toLowerCase()
  if (!s) return <Badge variant="outline">—</Badge>
  if (s === 'awaiting_author') return <Badge variant="secondary">待作者校对</Badge>
  if (s === 'author_corrections_submitted') return <Badge variant="destructive">作者已提交修改</Badge>
  if (s === 'in_layout_revision') return <Badge variant="outline">排版修订中</Badge>
  if (s === 'author_confirmed') return <Badge variant="secondary">作者已确认</Badge>
  if (s === 'draft') return <Badge variant="outline">草稿</Badge>
  return <Badge variant="outline">{s}</Badge>
}

export default function ProductionQueuePage() {
  const [loading, setLoading] = useState(true)
  const [rows, setRows] = useState<ProductionQueueItem[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await EditorApi.listMyProductionQueue(80)
      if (!res?.success) {
        throw new Error(res?.detail || res?.message || 'Failed to load production queue')
      }
      setRows((res?.data || []) as ProductionQueueItem[])
    } catch (e) {
      console.error(e)
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const sorted = useMemo(() => {
    const list = [...rows]
    list.sort((a, b) => {
      const ta = a?.cycle?.updated_at ? new Date(a.cycle.updated_at).getTime() : 0
      const tb = b?.cycle?.updated_at ? new Date(b.cycle.updated_at).getTime() : 0
      return tb - ta
    })
    return list
  }, [rows])

  return (
    <QueryProvider>
      <div className="sf-page-shell">
        <SiteHeader />
        <main className="sf-page-container space-y-6 py-10">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="mt-1 rounded-xl bg-card p-2 shadow-sm ring-1 ring-border">
                <Workflow className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h1 className="text-3xl font-serif font-bold text-foreground tracking-tight">Production Queue</h1>
                <p className="mt-1 text-muted-foreground font-medium">
                  仅展示分配给你（layout_editor_id 或协作者）的活跃生产轮次：清样上传、作者校对与发布前核准。
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => void load()} disabled={loading} className="gap-2">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                刷新
              </Button>
              <Link
                href="/dashboard?tab=production_editor"
                className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}
              >
                <ArrowLeft className="h-4 w-4" />
                返回工作台
              </Link>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
            <div className="grid grid-cols-12 gap-4 border-b border-border/60 bg-muted/40 px-5 py-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <div className="col-span-5">Title</div>
              <div className="col-span-2">Journal</div>
              <div className="col-span-2">Cycle</div>
              <div className="col-span-2">Updated</div>
              <div className="col-span-1 text-right">Action</div>
            </div>

            {loading ? (
              <div className="flex items-center justify-center gap-3 px-5 py-10 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading…
              </div>
            ) : sorted.length === 0 ? (
              <div className="px-5 py-10 text-sm text-muted-foreground">暂无分配到你的生产轮次。</div>
            ) : (
              <div className="divide-y divide-border/60">
                {sorted.map((item) => (
                  <div key={`${item.manuscript.id}-${item.cycle.id}`} className="grid grid-cols-12 gap-4 px-5 py-4">
                    <div className="col-span-5 min-w-0">
                      <p className="truncate text-sm font-semibold text-foreground">{item.manuscript.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground font-mono truncate">{item.manuscript.id}</p>
                    </div>
                    <div className="col-span-2 text-sm text-foreground">
                      {item.manuscript.journal?.title || '—'}
                    </div>
                    <div className="col-span-2 space-y-1">
                      {statusBadge(item.cycle.status)}
                      <p className="text-xs text-muted-foreground">#{item.cycle.cycle_no ?? '—'}</p>
                    </div>
                    <div className="col-span-2 text-sm text-foreground">
                      {formatDate(item.cycle.updated_at)}
                    </div>
                    <div className="col-span-1 flex justify-end">
                      <Link
                        href={item.action_url}
                        className={cn(buttonVariants({ size: 'sm' }), 'px-3')}
                      >
                        Open
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>
      </div>
    </QueryProvider>
  )
}
