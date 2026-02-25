import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, BriefcaseBusiness, Loader2, Search } from 'lucide-react'
import { format } from 'date-fns'

import SiteHeader from '@/components/layout/SiteHeader'
import QueryProvider from '@/components/providers/QueryProvider'
import { Button, buttonVariants } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { editorService } from '@/services/editorService'
import { getStatusLabel } from '@/lib/statusStyles'

interface Manuscript {
  id: string
  status?: string
  title: string
  created_at?: string | null
  updated_at?: string | null
  pre_check_status?: string | null
  workspace_bucket?:
    | 'intake'
    | 'technical_followup'
    | 'academic_pending'
    | 'under_review'
    | 'revision_followup'
    | 'decision'
    | 'production'
    | 'precheck_other'
    | 'other'
  owner?: { id?: string; full_name?: string | null; email?: string | null } | null
  assistant_editor?: { id?: string; full_name?: string | null; email?: string | null } | null
  journal?: { title?: string | null; slug?: string | null } | null
}

type WorkspaceBucket =
  | 'intake'
  | 'technical_followup'
  | 'academic_pending'
  | 'under_review'
  | 'revision_followup'
  | 'decision'
  | 'production'
  | 'precheck_other'
  | 'other'

type SectionMeta = {
  label: string
  description: string
}

const SECTION_ORDER: WorkspaceBucket[] = [
  'intake',
  'technical_followup',
  'academic_pending',
  'under_review',
  'revision_followup',
  'decision',
  'production',
  'precheck_other',
  'other',
]
const WORKSPACE_CACHE_TTL_MS = 20_000
const PAGE_SIZE = 80

const workspaceRowsCache = new Map<string, { rows: Manuscript[]; cachedAt: number }>()

const SECTION_META: Record<WorkspaceBucket, SectionMeta> = {
  intake: {
    label: 'Intake 待分派',
    description: '新投稿待 ME 完成入口审查与 AE 分派。',
  },
  technical_followup: {
    label: 'AE 技术处理中',
    description: '已分配给 AE，等待技术检查结果。',
  },
  academic_pending: {
    label: 'Academic 预审中',
    description: '已送 EIC 预审，ME 关注推进节奏。',
  },
  under_review: {
    label: '外审进行中',
    description: '稿件处于邀审/审稿进行阶段。',
  },
  revision_followup: {
    label: '修回待跟进',
    description: '作者修回或待修回，需 ME 继续跟进流转。',
  },
  decision: {
    label: '决策处理中',
    description: '已进入 decision 流程，跟进 first/final decision。',
  },
  production: {
    label: 'Production 流程',
    description: '录用后出版流程（含 PE 分配与校样周期）。',
  },
  precheck_other: {
    label: 'Pre-check 其他',
    description: '预审中的其他状态，建议检查状态完整性。',
  },
  other: {
    label: '其他在办稿件',
    description: '非终态但不在主分组中的稿件。',
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
  if (status === 'pre_check' && (!pre || pre === 'intake')) return 'intake'
  if (status === 'pre_check' && pre === 'technical') return 'technical_followup'
  if (status === 'pre_check' && pre === 'academic') return 'academic_pending'
  if (status === 'under_review') return 'under_review'
  if (status === 'resubmitted' || status === 'major_revision' || status === 'minor_revision') return 'revision_followup'
  if (status === 'decision' || status === 'decision_done') return 'decision'
  if (status === 'approved' || status === 'layout' || status === 'english_editing' || status === 'proofreading') return 'production'
  return 'other'
}

function buildCacheKey(q: string): string {
  return `q=${encodeURIComponent(String(q || '').trim().toLowerCase())}`
}

export default function ManagingWorkspacePage() {
  const [manuscripts, setManuscripts] = useState<Manuscript[]>([])
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [searchInput, setSearchInput] = useState('')
  const [query, setQuery] = useState('')
  const manuscriptsRef = useRef<Manuscript[]>([])
  const requestIdRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    manuscriptsRef.current = manuscripts
  }, [manuscripts])

  const fetchWorkspace = useCallback(
    async (options?: { preferCache?: boolean; silent?: boolean; forceRefresh?: boolean; queryOverride?: string }) => {
      const effectiveQuery = String(options?.queryOverride ?? query).trim()
      const cacheKey = buildCacheKey(effectiveQuery)
      const cacheItem = workspaceRowsCache.get(cacheKey)
      const now = Date.now()
      const cacheValid = Boolean(cacheItem && now - cacheItem.cachedAt < WORKSPACE_CACHE_TTL_MS)

      if (options?.preferCache && cacheValid && cacheItem) {
        setManuscripts(cacheItem.rows)
      }

      const hasRows = (cacheValid && Boolean(cacheItem?.rows.length)) || manuscriptsRef.current.length > 0
      const blockUi = !options?.silent && !hasRows
      if (blockUi) setLoading(true)
      else setIsRefreshing(true)

      const currentRequestId = ++requestIdRef.current
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      try {
        const data = await editorService.getManagingWorkspace(1, PAGE_SIZE, effectiveQuery, {
          forceRefresh: Boolean(options?.forceRefresh),
          signal: controller.signal,
        })
        if (currentRequestId !== requestIdRef.current) return
        setManuscripts(data as unknown as Manuscript[])
        workspaceRowsCache.set(cacheKey, {
          rows: data as unknown as Manuscript[],
          cachedAt: Date.now(),
        })
      } catch (err) {
        if (controller.signal.aborted || currentRequestId !== requestIdRef.current) return
        console.error(err)
      } finally {
        if (currentRequestId === requestIdRef.current) {
          setLoading(false)
          setIsRefreshing(false)
        }
      }
    },
    [query]
  )

  useEffect(() => {
    void fetchWorkspace({ preferCache: true })
  }, [fetchWorkspace])

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  const groupedSections = useMemo(() => {
    const sorted = [...manuscripts].sort((a, b) => {
      const updatedDiff = toMillis(b.updated_at) - toMillis(a.updated_at)
      if (updatedDiff !== 0) return updatedDiff
      return toMillis(b.created_at) - toMillis(a.created_at)
    })

    const buckets: Record<WorkspaceBucket, Manuscript[]> = {
      intake: [],
      technical_followup: [],
      academic_pending: [],
      under_review: [],
      revision_followup: [],
      decision: [],
      production: [],
      precheck_other: [],
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
      <div className="sf-page-shell">
        <SiteHeader />
        <main className="sf-page-container space-y-6 py-10">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="mt-1 rounded-xl bg-card p-2 shadow-sm ring-1 ring-border">
                <BriefcaseBusiness className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h1 className="text-3xl font-serif font-bold tracking-tight text-foreground">Managing Editor Workspace</h1>
                <p className="mt-1 font-medium text-muted-foreground">
                  展示需要 ME 跟进的全部在办稿件，并按状态分组。
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => void fetchWorkspace({ silent: true, forceRefresh: true })}
                disabled={isRefreshing}
              >
                {isRefreshing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                刷新列表
              </Button>
              <Link href="/dashboard?tab=managing_editor" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
                <ArrowLeft className="h-4 w-4" />
                返回编辑台
              </Link>
            </div>
          </div>

          <form
            className="rounded-xl border border-border bg-card p-4"
            onSubmit={(e) => {
              e.preventDefault()
              const nextQuery = searchInput.trim()
              setQuery(nextQuery)
              void fetchWorkspace({ queryOverride: nextQuery, forceRefresh: true })
            }}
          >
            <div className="flex flex-col gap-3 md:flex-row md:items-center">
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
                <Input
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="pl-9"
                  placeholder="Search by title / manuscript id / owner / AE / journal"
                />
              </div>
              <div className="flex items-center gap-2">
                <Button type="submit">搜索</Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setSearchInput('')
                    setQuery('')
                    void fetchWorkspace({ queryOverride: '', forceRefresh: true })
                  }}
                >
                  清空
                </Button>
              </div>
            </div>
          </form>

          {isRefreshing && !loading ? (
            <div className="flex items-center justify-end gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Syncing latest workspace data…
            </div>
          ) : null}

          {loading ? (
            <div className="rounded-xl border border-border bg-card px-4 py-10 text-center text-sm text-muted-foreground">Loading…</div>
          ) : groupedSections.length === 0 ? (
            <div className="rounded-xl border border-border bg-card px-4 py-10 text-center text-sm text-muted-foreground">
              No manuscripts in current scope.
            </div>
          ) : (
            groupedSections.map((section) => (
              <section key={section.key} className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
                <div className="border-b border-border bg-muted/50 px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-base font-semibold text-foreground">{section.meta.label}</h2>
                    <Badge variant="secondary">{section.items.length}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{section.meta.description}</p>
                </div>

                <Table>
                  <TableHeader className="bg-muted/40">
                    <TableRow>
                      <TableHead className="min-w-96">Title</TableHead>
                      <TableHead className="min-w-44">Status</TableHead>
                      <TableHead className="min-w-44">Updated</TableHead>
                      <TableHead className="min-w-44">Owner</TableHead>
                      <TableHead className="min-w-44">Assistant Editor</TableHead>
                      <TableHead className="min-w-40">Journal</TableHead>
                      <TableHead className="min-w-40">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {section.items.map((m) => {
                      const detailHref = `/editor/manuscript/${encodeURIComponent(m.id)}?from=managing-workspace`
                      return (
                        <TableRow key={m.id} className="hover:bg-muted/50">
                          <TableCell>
                            <Link href={detailHref} className="text-sm font-semibold text-foreground hover:text-primary hover:underline">
                              {m.title || 'Untitled Manuscript'}
                            </Link>
                            <div className="mt-1 text-xs font-mono text-muted-foreground">{m.id}</div>
                          </TableCell>

                          <TableCell>
                            <div className="flex flex-wrap items-center gap-1.5">
                              <Badge variant="outline">{getStatusLabel(m.status || 'unknown')}</Badge>
                              {m.pre_check_status ? <Badge variant="secondary">{m.pre_check_status}</Badge> : null}
                            </div>
                          </TableCell>

                          <TableCell className="text-sm text-foreground">{fmt(m.updated_at || m.created_at)}</TableCell>
                          <TableCell className="text-sm text-foreground">{m.owner?.full_name || m.owner?.email || '—'}</TableCell>
                          <TableCell className="text-sm text-foreground">
                            {m.assistant_editor?.full_name || m.assistant_editor?.email || '—'}
                          </TableCell>
                          <TableCell className="text-sm text-foreground">{m.journal?.title || '—'}</TableCell>

                          <TableCell>
                            <Link href={detailHref} className={cn(buttonVariants({ size: 'sm', variant: 'outline' }))}>
                              Open Detail
                            </Link>
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
      </div>
    </QueryProvider>
  )
}
