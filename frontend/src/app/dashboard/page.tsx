'use client'

import { useEffect, useState } from 'react'
import SiteHeader from '@/components/layout/SiteHeader'
import { FileText, CheckCircle, Clock, AlertCircle, Plus, ArrowRight, Loader2 } from 'lucide-react'
import Link from 'next/link'

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function fetchStats() {
      try {
        // 实际需携带 Token，此处暂模拟
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
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SiteHeader />
      
      <main className="flex-1 mx-auto max-w-7xl w-full px-4 py-12 sm:px-6 lg:px-8">
        <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6 mb-12">
          <div>
            <h1 className="text-3xl font-serif font-bold text-slate-900">Welcome back, Scholar</h1>
            <p className="mt-1 text-slate-500 font-medium">Track your research impact and submission status.</p>
          </div>
          <Link 
            href="/submit" 
            className="flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-xl font-bold shadow-lg hover:bg-blue-500 transition-all"
          >
            <Plus className="h-5 w-5" /> New Submission
          </Link>
        </header>

        {isLoading ? (
          <div className="flex justify-center py-20"><Loader2 className="h-12 w-12 animate-spin text-blue-600" /></div>
        ) : (
          <div className="space-y-12">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {statCards.map((card) => (
                <div key={card.label} className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-1">{card.label}</p>
                    <p className="text-3xl font-mono font-bold text-slate-900">{card.value || 0}</p>
                  </div>
                  <card.icon className={`h-10 w-10 ${card.color} opacity-20`} />
                </div>
              ))}
            </div>

            {/* Recent Activity Mock */}
            <section>
              <h2 className="text-xl font-bold text-slate-900 mb-6">Recent Activity</h2>
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
                  <div className="p-6 flex items-center justify-between hover:bg-slate-50 cursor-pointer group transition-all">
                    <div className="flex items-center gap-4">
                      <div className="bg-green-50 p-3 rounded-2xl"><CheckCircle className="h-6 w-6 text-green-600" /></div>
                      <div>
                        <p className="font-bold text-slate-900">Quantum Encryption Basics</p>
                        <p className="text-sm text-slate-500 font-medium">Published in Science Reports • Jan 25, 2026</p>
                      </div>
                    </div>
                    <ArrowRight className="h-5 w-5 text-slate-300 group-hover:text-blue-600 transition-all" />
                  </div>
                </div>
                <div className="bg-slate-50 p-4 text-center">
                  <button className="text-sm font-bold text-blue-600 hover:underline">View All Submissions</button>
                </div>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  )
}
