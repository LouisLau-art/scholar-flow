'use client'

import { Suspense, useEffect, useMemo, useState } from 'react'
import SiteHeader from '@/components/layout/SiteHeader'
import { FileText, CheckCircle, Clock, AlertCircle, Plus, ArrowRight, Loader2, Users, LayoutDashboard, Shield } from 'lucide-react'
import Link from 'next/link'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import ReviewerDashboard from "@/components/ReviewerDashboard"
import AdminDashboard from "@/components/AdminDashboard"
import { authService } from '@/services/auth'
import { useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { Button, buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type DashboardTab =
  | 'author'
  | 'reviewer'
  | 'managing_editor'
  | 'assistant_editor'
  | 'production_editor'
  | 'editor_in_chief'
  | 'admin'

const DASHBOARD_TABS: DashboardTab[] = [
  'author',
  'reviewer',
  'managing_editor',
  'assistant_editor',
  'production_editor',
  'editor_in_chief',
  'admin',
]

const KNOWN_ROLE_TOKENS = [
  'admin',
  'author',
  'reviewer',
  'managing_editor',
  'assistant_editor',
  'production_editor',
  'editor_in_chief',
] as const

function pickFirstAllowedTab(allowed: Record<DashboardTab, boolean>): DashboardTab {
  const order: DashboardTab[] = [
    'author',
    'reviewer',
    'managing_editor',
    'assistant_editor',
    'production_editor',
    'editor_in_chief',
    'admin',
  ]
  for (const tab of order) {
    if (allowed[tab]) return tab
  }
  return 'author'
}

function parseDashboardTab(raw: string | null): DashboardTab | null {
  if (!raw) return null
  return DASHBOARD_TABS.includes(raw as DashboardTab) ? (raw as DashboardTab) : null
}

function normalizeRoleTokens(input: unknown): string[] {
  if (!Array.isArray(input)) return []
  const out = new Set<string>()
  const known = new Set<string>(KNOWN_ROLE_TOKENS)
  const sortedTokens = [...KNOWN_ROLE_TOKENS].sort((a, b) => b.length - a.length)
  for (const raw of input) {
    const text = String(raw || '').trim().toLowerCase()
    if (!text) continue
    // 标准分隔场景: "author,reviewer" / "author reviewer"
    for (const part of text.split(/[,\s|;/]+/).filter(Boolean)) {
      if (known.has(part)) out.add(part)
    }

    // 异常拼接场景: "managing_editorassistant_editor"
    // 采用“最长 token 优先剥离”，避免 assistant_editor 被误判为 legacy editor。
    let rest = text
    for (const token of sortedTokens) {
      if (!rest.includes(token)) continue
      out.add(token)
      rest = rest.split(token).join(' ')
    }
  }
  return Array.from(out)
}

function RoleWorkspacePanel({
  title,
  description,
  actions,
}: {
  title: string
  description: string
  actions: Array<{ label: string; href: string; helper: string }>
}) {
  return (
    <section className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h2 className="text-2xl font-serif font-bold text-foreground">{title}</h2>
        <p className="mt-1 text-muted-foreground">{description}</p>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {actions.map((item) => (
          <Link
            key={`${title}-${item.href}`}
            href={item.href}
            className="group rounded-2xl border border-border bg-card p-6 shadow-sm transition hover:border-primary/40 hover:shadow-md"
          >
            <div className="flex items-center justify-between">
              <p className="text-base font-semibold text-foreground">{item.label}</p>
              <ArrowRight className="h-4 w-4 text-muted-foreground transition group-hover:translate-x-0.5 group-hover:text-primary" />
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{item.helper}</p>
          </Link>
        ))}
      </div>
    </section>
  )
}

function DashboardPageContent() {
  const searchParams = useSearchParams()
  const tabParam = searchParams?.get('tab') ?? null
  const [stats, setStats] = useState<any>(null)
  const [submissions, setSubmissions] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [roles, setRoles] = useState<string[] | null>(null)
  const [rolesLoading, setRolesLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<DashboardTab>(() => {
    const tab = parseDashboardTab(tabParam)
    if (tab) return tab
    return 'author'
  })

  useEffect(() => {
    async function fetchStats() {
      try {
        const token = await authService.getAccessToken()
        const res = await fetch('/api/v1/stats/author', {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        })
        const result = await res.json()
        if (result.success) setStats(result.data)
      } catch (err) {
        console.error('Failed to load dashboard:', err)
      } finally {
        setIsLoading(false)
      }
    }
    async function fetchSubmissions() {
      try {
        const token = await authService.getAccessToken()
        const res = await fetch('/api/v1/manuscripts/mine', {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        })
        const result = await res.json()
        if (result.success) setSubmissions(result.data || [])
      } catch (err) {
        console.error('Failed to load submissions:', err)
      }
    }
    async function fetchProfile() {
      try {
        const token = await authService.getAccessToken()
        if (!token) return
        const res = await fetch('/api/v1/user/profile', {
          headers: { Authorization: `Bearer ${token}` },
        })
        const result = await res.json()
        if (result.success) setRoles(result.data?.roles || [])
      } catch (err) {
        console.error('Failed to load profile:', err)
      } finally {
        setRolesLoading(false)
      }
    }
    fetchStats()
    fetchSubmissions()
    fetchProfile()
  }, [])

  const statCards = [
    { label: 'Total Submissions', value: stats?.total_submissions, icon: FileText, color: 'text-primary' },
    { label: 'Published', value: stats?.published, icon: CheckCircle, color: 'text-emerald-600' },
    { label: 'Under Review', value: stats?.under_review, icon: Clock, color: 'text-amber-600' },
    { label: 'Waiting for Author', value: stats?.revision_requested ?? stats?.revision_required, icon: AlertCircle, color: 'text-muted-foreground' },
  ]

  const normalizedRoles = useMemo(() => normalizeRoleTokens(roles || []), [roles])
  const roleSet = new Set(normalizedRoles)
  const canSeeAdmin = roleSet.has('admin')
  const canSeeAuthor = canSeeAdmin || roleSet.has('author')
  const canSeeReviewer = canSeeAdmin || roleSet.has('reviewer')
  const canSeeManagingEditor = canSeeAdmin || roleSet.has('managing_editor')
  const canSeeAssistantEditor = canSeeAdmin || roleSet.has('assistant_editor')
  const canSeeProductionEditor = canSeeAdmin || roleSet.has('production_editor')
  const canSeeEditorInChief = canSeeAdmin || roleSet.has('editor_in_chief')
  const allowedTabs: Record<DashboardTab, boolean> = useMemo(
    () => ({
      author: canSeeAuthor,
      reviewer: canSeeReviewer,
      managing_editor: canSeeManagingEditor,
      assistant_editor: canSeeAssistantEditor,
      production_editor: canSeeProductionEditor,
      editor_in_chief: canSeeEditorInChief,
      admin: canSeeAdmin,
    }),
    [
      canSeeAuthor,
      canSeeReviewer,
      canSeeManagingEditor,
      canSeeAssistantEditor,
      canSeeProductionEditor,
      canSeeEditorInChief,
      canSeeAdmin,
    ]
  )
  const roleLabel = rolesLoading ? 'loading…' : (normalizedRoles.length > 0 ? normalizedRoles.join(', ') : 'none')
  const hasAnyTab = Object.values(allowedTabs).some(Boolean)

  // 支持 /dashboard?tab=reviewer 之类的深链
  useEffect(() => {
    const tab = parseDashboardTab(tabParam)
    if (tab) {
      setActiveTab(tab)
    }
  }, [tabParam])

  // 若 URL 指向无权限 tab，则回退到“当前角色可访问的首个 tab”
  useEffect(() => {
    if (rolesLoading) return
    if (!allowedTabs[activeTab]) {
      setActiveTab(pickFirstAllowedTab(allowedTabs))
    }
  }, [
    rolesLoading,
    activeTab,
    allowedTabs,
  ])

  return (
    <div className="sf-page-shell flex flex-col font-sans">
      <SiteHeader />

      <main className="sf-page-container flex-1 py-12">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="space-y-10">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
            <div>
              <h1 className="text-3xl font-serif font-bold text-foreground tracking-tight">Dashboard</h1>
              <p className="mt-1 text-muted-foreground font-medium">Manage your roles and track academic progress.</p>
              <p className="mt-2 text-xs font-mono text-muted-foreground">roles: {roleLabel}</p>
            </div>

            {rolesLoading ? (
              <div className="rounded-2xl border border-border bg-card px-6 py-2 text-sm font-semibold text-muted-foreground">
                Loading roles...
              </div>
            ) : (
              <TabsList className="bg-card p-1 rounded-2xl shadow-sm border border-border flex flex-wrap gap-1 h-auto">
                {canSeeAuthor && (
                  <TabsTrigger value="author" className="flex items-center gap-2 rounded-xl px-6 data-[state=active]:bg-foreground data-[state=active]:text-primary-foreground">
                    <LayoutDashboard className="h-4 w-4" /> Author
                  </TabsTrigger>
                )}
                {canSeeReviewer && (
                  <TabsTrigger value="reviewer" className="flex items-center gap-2 rounded-xl px-6 data-[state=active]:bg-foreground data-[state=active]:text-primary-foreground">
                    <Users className="h-4 w-4" /> Reviewer
                  </TabsTrigger>
                )}
                {canSeeManagingEditor && (
                  <TabsTrigger value="managing_editor" className="flex items-center gap-2 rounded-xl px-6 data-[state=active]:bg-foreground data-[state=active]:text-primary-foreground">
                    <Shield className="h-4 w-4" /> Managing Editor
                  </TabsTrigger>
                )}
                {canSeeAssistantEditor && (
                  <TabsTrigger value="assistant_editor" className="flex items-center gap-2 rounded-xl px-6 data-[state=active]:bg-foreground data-[state=active]:text-primary-foreground">
                    <Shield className="h-4 w-4" /> Assistant Editor
                  </TabsTrigger>
                )}
                {canSeeProductionEditor && (
                  <TabsTrigger value="production_editor" className="flex items-center gap-2 rounded-xl px-6 data-[state=active]:bg-foreground data-[state=active]:text-primary-foreground">
                    <Shield className="h-4 w-4" /> Production Editor
                  </TabsTrigger>
                )}
                {canSeeEditorInChief && (
                  <TabsTrigger value="editor_in_chief" className="flex items-center gap-2 rounded-xl px-6 data-[state=active]:bg-foreground data-[state=active]:text-primary-foreground">
                    <Shield className="h-4 w-4" /> Editor-in-Chief
                  </TabsTrigger>
                )}
                {canSeeAdmin && (
                  <TabsTrigger value="admin" className="flex items-center gap-2 rounded-xl px-6 data-[state=active]:bg-foreground data-[state=active]:text-primary-foreground">
                    <Shield className="h-4 w-4" /> Admin
                  </TabsTrigger>
                )}
              </TabsList>
            )}
          </div>

          {!rolesLoading && !hasAnyTab && (
            <TabsContent value={activeTab} className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
                当前账号未分配可访问的 Dashboard 角色，请联系管理员在 User Management 中补齐角色。
              </div>
            </TabsContent>
          )}

          {canSeeAuthor && (
            <TabsContent value="author" className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
              {isLoading ? (
                <div className="flex justify-center py-20"><Loader2 className="h-12 w-12 animate-spin text-primary" /></div>
              ) : (
                <div className="space-y-12">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    {statCards.map((card) => (
                      <div key={card.label} className="bg-card p-8 rounded-3xl shadow-sm border border-border/60 flex items-center justify-between">
                        <div>
                          <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-1">{card.label}</p>
                          <p className="text-3xl font-mono font-bold text-foreground">{card.value || 0}</p>
                        </div>
                        <card.icon className={`h-10 w-10 ${card.color} opacity-20`} />
                      </div>
                    ))}
                  </div>

                  <section>
                    <div className="flex justify-between items-center mb-6">
                      <h2 className="text-xl font-bold text-foreground">My Submissions</h2>
                      <Link href="/submit" className="text-sm font-bold text-primary hover:underline flex items-center gap-1">
                        <Plus className="h-4 w-4" /> New Submission
                      </Link>
                    </div>
                    <div className="bg-card rounded-3xl shadow-sm border border-border/60 overflow-hidden">
                      {submissions.length === 0 ? (
                        <div className="p-8 text-muted-foreground text-sm">No submissions yet.</div>
                      ) : (
                        <div className="divide-y divide-border/60">
                          {submissions.map((item) => {
                            const itemStatus = String(item?.status || '').toLowerCase()
                            const detailHref =
                              itemStatus === 'published'
                                ? `/articles/${item.id}`
                                : `/dashboard/author/manuscripts/${item.id}`
                            return (
                            <div key={item.id} className="p-6 flex items-center justify-between hover:bg-muted/40 group transition-all">
                              <div className="flex items-center gap-4">
                                <div className="bg-primary/10 p-3 rounded-2xl"><FileText className="h-6 w-6 text-primary" /></div>
                                <div>
                                  <p className="font-bold text-foreground">{item.title}</p>
                                  <p className="text-sm text-muted-foreground font-medium">
                                    Status: {item.status || 'pre_check'} • {item.created_at ? new Date(item.created_at).toLocaleDateString() : '—'}
                                  </p>
                                </div>
                              </div>
                              <div className="flex items-center gap-3">
                                {['major_revision', 'minor_revision', 'revision_requested'].includes(item.status) && (
                                  <Link
                                    href={`/submit-revision/${item.id}`}
                                    className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
                                  >
                                    Submit Revision
                                  </Link>
                                )}
                                {item?.proofreading_task?.action_required && (
                                  <Link
                                    href={String(item?.proofreading_task?.url || `/proofreading/${item.id}`)}
                                    className={cn(buttonVariants({ size: 'sm' }))}
                                  >
                                    Proofreading
                                  </Link>
                                )}
                                {item.status === 'approved' && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={async (e) => {
                                      e.preventDefault()
                                      const toastId = toast.loading('Generating invoice…')
                                      try {
                                        const token = await authService.getAccessToken()
                                        if (!token) {
                                          toast.error('Please sign in again.', { id: toastId })
                                          return
                                        }
                                        const res = await fetch(`/api/v1/manuscripts/${encodeURIComponent(item.id)}/invoice`, {
                                          headers: { Authorization: `Bearer ${token}` },
                                        })
                                        if (!res.ok) {
                                          let msg = ''
                                          try {
                                            const j = await res.json()
                                            msg = (j?.detail || j?.message || '').toString()
                                          } catch {
                                            msg = await res.text().catch(() => '')
                                          }
                                          toast.error(msg || 'Invoice not available.', { id: toastId })
                                          return
                                        }
                                        const blob = await res.blob()
                                        const url = window.URL.createObjectURL(blob)
                                        window.open(url, '_blank')
                                        toast.success('Invoice ready.', { id: toastId })
                                      } catch (err) {
                                        toast.error('Failed to download invoice.', { id: toastId })
                                      }
                                    }}
                                  >
                                    Download Invoice
                                  </Button>
                                )}
                                <Link href={detailHref} className="text-muted-foreground group-hover:text-primary transition-all">
                                  <ArrowRight className="h-5 w-5" />
                                </Link>
                              </div>
                            </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  </section>
                </div>
              )}
            </TabsContent>
          )}

          {canSeeReviewer && (
            <TabsContent value="reviewer" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <ReviewerDashboard />
            </TabsContent>
          )}

          {canSeeManagingEditor && (
            <TabsContent value="managing_editor">
              <RoleWorkspacePanel
                title="Managing Editor Workspace"
                description="Handle intake routing, reviewer assignment coordination, and process oversight."
                actions={[
                  { label: 'ME Workspace', href: '/editor/managing-workspace', helper: 'Track all ME follow-up manuscripts grouped by status.' },
                  { label: 'Intake Queue', href: '/editor/intake', helper: 'Assign Assistant Editor for newly submitted manuscripts.' },
                  { label: 'Manuscripts Process', href: '/editor/process', helper: 'Track full pipeline status and filter by journal.' },
                  { label: 'Reviewer Library', href: '/editor/reviewers', helper: 'Manage reviewer pool and candidate metadata.' },
                  { label: 'Analytics Dashboard', href: '/editor/analytics', helper: 'Review throughput and SLA indicators.' },
                ]}
              />
            </TabsContent>
          )}

          {canSeeAssistantEditor && (
            <TabsContent value="assistant_editor">
              <RoleWorkspacePanel
                title="Assistant Editor Workspace"
                description="Track your assigned manuscripts across technical handoff, peer review, and revision follow-up."
                actions={[
                  { label: 'AE Workspace', href: '/editor/workspace', helper: 'Focus on your in-flight manuscripts with status-based actions.' },
                  { label: 'Manuscripts Process', href: '/editor/process', helper: 'Inspect lifecycle updates (sorted by most recently updated).' },
                ]}
              />
            </TabsContent>
          )}

          {canSeeProductionEditor && (
            <TabsContent value="production_editor">
              <RoleWorkspacePanel
                title="Production Editor Workspace"
                description="Manage galley proofs, author corrections, and approve production cycles for publish gates."
                actions={[
                  { label: 'Production Queue', href: '/editor/production', helper: 'See production cycles assigned to you (layout_editor_id / collaborators).' },
                ]}
              />
            </TabsContent>
          )}

          {canSeeEditorInChief && (
            <TabsContent value="editor_in_chief">
              <RoleWorkspacePanel
                title="Editor-in-Chief Workspace"
                description="Perform academic checks and final editorial governance."
                actions={[
                  { label: 'Academic Queue', href: '/editor/academic', helper: 'Review AE outcomes and route to next stage.' },
                  { label: 'Manuscripts Process', href: '/editor/process', helper: 'Monitor decision-stage manuscripts.' },
                  { label: 'Analytics Dashboard', href: '/editor/analytics', helper: 'Track decision velocity and acceptance trends.' },
                ]}
              />
            </TabsContent>
          )}

          {canSeeAdmin && (
            <TabsContent value="admin" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <AdminDashboard />
            </TabsContent>
          )}
        </Tabs>
      </main>
    </div>
  )
}

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-muted/40 flex items-center justify-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
        </div>
      }
    >
      <DashboardPageContent />
    </Suspense>
  )
}
