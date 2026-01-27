'use client'

import { useEffect, useState } from 'react'
import SiteHeader from '@/components/layout/SiteHeader'
import { FileText, CheckCircle, Clock, AlertCircle, Plus, ArrowRight, Loader2, Users, LayoutDashboard } from 'lucide-react'
import Link from 'next/link'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import ReviewerDashboard from "@/components/ReviewerDashboard"

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch('/api/v1/stats/author')
        const result = await res.json()
        if (result.success) setStats(result.data)
      } catch (err) {
        console.error('Failed to load dashboard:', err)
      } finally {
        setIsLoading(false)
      }
    }
    fetchStats()
  }, [])

  const statCards = [
    { label: 'Total Submissions', value: stats?.total_submissions, icon: FileText, color: 'text-blue-600' },
    { label: 'Published', value: stats?.published, icon: CheckCircle, color: 'text-emerald-600' },
    { label: 'Under Review', value: stats?.under_review, icon: Clock, color: 'text-amber-600' },
    { label: 'Revision Required', value: stats?.revision_required, icon: AlertCircle, color: 'text-rose-600' },
  ]

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <SiteHeader />
      
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-12 sm:px-6 lg:px-8">
        <Tabs defaultValue="author" className="space-y-10">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
            <div>
              <h1 className="text-3xl font-serif font-bold text-slate-900 tracking-tight">Dashboard</h1>
              <p className="mt-1 text-slate-500 font-medium">Manage your roles and track academic progress.</p>
            </div>
            
            <TabsList className="bg-white p-1 rounded-2xl shadow-sm border border-slate-200">
              <TabsTrigger value="author" className="flex items-center gap-2 rounded-xl px-6 data-[state=active]:bg-slate-900 data-[state=active]:text-white">
                <LayoutDashboard className="h-4 w-4" /> Author
              </TabsTrigger>
              <TabsTrigger value="reviewer" className="flex items-center gap-2 rounded-xl px-6 data-[state=active]:bg-slate-900 data-[state=active]:text-white">
                <Users className="h-4 w-4" /> Reviewer
              </TabsTrigger>
            </TabsList>
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
                    <h2 className="text-xl font-bold text-slate-900">Recent Activity</h2>
                    <Link href="/submit" className="text-sm font-bold text-blue-600 hover:underline flex items-center gap-1">
                      <Plus className="h-4 w-4" /> New Submission
                    </Link>
                  </div>
                  <div className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
                    <div className="divide-y divide-slate-100">
                      <div className="p-6 flex items-center justify-between hover:bg-slate-50 cursor-pointer group transition-all">
                        <div className="flex items-center gap-4">
                          <div className="bg-blue-50 p-3 rounded-2xl"><FileText className="h-6 w-6 text-blue-600" /></div>
                          <div>
                            <p className="font-bold text-slate-900">Deep Learning in Academic Workflows</p>
                            <p className="text-sm text-slate-500 font-medium">Submitted to Frontiers in AI • Jan 27, 2026</p>
                          </div>
                        </div>
                        <ArrowRight className="h-5 w-5 text-slate-300 group-hover:text-blue-600 transition-all" />
                      </div>
                    </div>
                  </div>
                </section>
              </div>
            )}
          </TabsContent>

          <TabsContent value="reviewer" className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <ReviewerDashboard />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
