'use client'

import { Suspense, useEffect, useState } from 'react'
import SiteHeader from '@/components/layout/SiteHeader'
import { FileText, CheckCircle, Clock, AlertCircle, Plus, ArrowRight, Loader2, Users, LayoutDashboard, Shield } from 'lucide-react'
import Link from 'next/link'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import ReviewerDashboard from "@/components/ReviewerDashboard"
import EditorDashboard from "@/components/EditorDashboard"
import AdminDashboard from "@/components/AdminDashboard"
import { authService } from '@/services/auth'
import { useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'

function DashboardPageContent() {
  const searchParams = useSearchParams()
  const tabParam = searchParams.get('tab')
  const [stats, setStats] = useState<any>(null)
  const [submissions, setSubmissions] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [roles, setRoles] = useState<string[] | null>(null)
  const [rolesLoading, setRolesLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'author' | 'reviewer' | 'editor' | 'admin'>(() => {
    const tab = tabParam
    if (tab === 'reviewer' || tab === 'editor' || tab === 'admin' || tab === 'author') return tab
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
    { label: 'Total Submissions', value: stats?.total_submissions, icon: FileText, color: 'text-blue-600' },
    { label: 'Published', value: stats?.published, icon: CheckCircle, color: 'text-emerald-600' },
    { label: 'Under Review', value: stats?.under_review, icon: Clock, color: 'text-amber-600' },
    { label: 'Waiting for Author', value: stats?.revision_requested ?? stats?.revision_required, icon: AlertCircle, color: 'text-slate-600' },
  ]

  const canSeeReviewer = Boolean(roles?.includes('reviewer') || roles?.includes('admin'))
  const canSeeEditor = Boolean(roles?.includes('editor') || roles?.includes('admin'))
  const canSeeAdmin = Boolean(roles?.includes('admin'))
  const roleLabel = rolesLoading ? 'loading…' : (roles && roles.length > 0 ? roles.join(', ') : 'author')

  // 支持 /dashboard?tab=reviewer 之类的深链
  useEffect(() => {
    const tab = tabParam
    if (tab === 'reviewer' || tab === 'editor' || tab === 'admin' || tab === 'author') {
      setActiveTab(tab)
    }
  }, [tabParam])

  // 若 URL 指向无权限 tab，则回退到 author
  useEffect(() => {
    if (rolesLoading) return
    if (activeTab === 'admin' && !canSeeAdmin) setActiveTab('author')
    if (activeTab === 'editor' && !canSeeEditor) setActiveTab('author')
    if (activeTab === 'reviewer' && !canSeeReviewer) setActiveTab('author')
  }, [rolesLoading, activeTab, canSeeAdmin, canSeeEditor, canSeeReviewer])

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <SiteHeader />

      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-12 sm:px-6 lg:px-8">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="space-y-10">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
            <div>
              <h1 className="text-3xl font-serif font-bold text-slate-900 tracking-tight">Dashboard</h1>
              <p className="mt-1 text-slate-500 font-medium">Manage your roles and track academic progress.</p>
              <p className="mt-2 text-xs font-mono text-slate-400">roles: {roleLabel}</p>
            </div>

            {rolesLoading ? (
              <div className="rounded-2xl border border-slate-200 bg-white px-6 py-2 text-sm font-semibold text-slate-400">
                Loading roles...
              </div>
            ) : (
              <TabsList className="bg-white p-1 rounded-2xl shadow-sm border border-slate-200">
                <TabsTrigger value="author" className="flex items-center gap-2 rounded-xl px-6 data-[state=active]:bg-slate-900 data-[state=active]:text-white">
                  <LayoutDashboard className="h-4 w-4" /> Author
                </TabsTrigger>
                {canSeeReviewer && (
                  <TabsTrigger value="reviewer" className="flex items-center gap-2 rounded-xl px-6 data-[state=active]:bg-slate-900 data-[state=active]:text-white">
                    <Users className="h-4 w-4" /> Reviewer
                  </TabsTrigger>
                )}
                {canSeeEditor && (
                  <TabsTrigger value="editor" className="flex items-center gap-2 rounded-xl px-6 data-[state=active]:bg-slate-900 data-[state=active]:text-white">
                    <Shield className="h-4 w-4" /> Editor
                  </TabsTrigger>
                )}
                {canSeeAdmin && (
                  <TabsTrigger value="admin" className="flex items-center gap-2 rounded-xl px-6 data-[state=active]:bg-slate-900 data-[state=active]:text-white">
                    <Shield className="h-4 w-4" /> Admin
                  </TabsTrigger>
                )}
              </TabsList>
            )}
          </div>

          <TabsContent value="author" className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {isLoading ? (
              <div className="flex justify-center py-20"><Loader2 className="h-12 w-12 animate-spin text-blue-600" /></div>
            ) : (
              <div className="space-y-12">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                  {statCards.map((card) => (
                    <div key={card.label} className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 flex items-center justify-between">
                      <div>
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">{card.label}</p>
                        <p className="text-3xl font-mono font-bold text-slate-900">{card.value || 0}</p>
                      </div>
                      <card.icon className={`h-10 w-10 ${card.color} opacity-20`} />
                    </div>
                  ))}
                </div>

                <section>
                  <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold text-slate-900">My Submissions</h2>
                    <Link href="/submit" className="text-sm font-bold text-blue-600 hover:underline flex items-center gap-1">
                      <Plus className="h-4 w-4" /> New Submission
                    </Link>
                  </div>
                  <div className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
                    {submissions.length === 0 ? (
                      <div className="p-8 text-slate-500 text-sm">No submissions yet.</div>
                    ) : (
                      <div className="divide-y divide-slate-100">
                        {submissions.map((item) => (
                          <div key={item.id} className="p-6 flex items-center justify-between hover:bg-slate-50 group transition-all">
                            <div className="flex items-center gap-4">
                              <div className="bg-blue-50 p-3 rounded-2xl"><FileText className="h-6 w-6 text-blue-600" /></div>
                              <div>
                                <p className="font-bold text-slate-900">{item.title}</p>
                                <p className="text-sm text-slate-500 font-medium">
                                  Status: {item.status || 'submitted'} • {item.created_at ? new Date(item.created_at).toLocaleDateString() : '—'}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-3">
                              {item.status === 'revision_requested' && (
                                <Link
                                  href={`/submit-revision/${item.id}`}
                                  className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
                                >
                                  Submit Revision
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
                                        const msg = await res.text().catch(() => '')
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
                              <Link href={`/articles/${item.id}`} className="text-slate-300 group-hover:text-blue-600 transition-all">
                                <ArrowRight className="h-5 w-5" />
                              </Link>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </section>
              </div>
            )}
          </TabsContent>

          {canSeeReviewer && (
            <TabsContent value="reviewer" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <ReviewerDashboard />
            </TabsContent>
          )}

          {canSeeEditor && (
            <TabsContent value="editor" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <EditorDashboard />
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
        <div className="min-h-screen bg-slate-50 flex items-center justify-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600" />
        </div>
      }
    >
      <DashboardPageContent />
    </Suspense>
  )
}
