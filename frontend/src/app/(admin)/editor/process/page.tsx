'use client'

import Link from 'next/link'
import SiteHeader from '@/components/layout/SiteHeader'
import { ManuscriptsProcessPanel } from '@/components/editor/ManuscriptsProcessPanel'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { ArrowLeft, Table2 } from 'lucide-react'
import { Suspense } from 'react'

export default function ManuscriptsProcessPage() {
  return (
    <div className="sf-page-shell">
      <SiteHeader />
      <main className="sf-page-container space-y-6 py-10">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="mt-1 rounded-xl bg-white p-2 shadow-sm ring-1 ring-slate-200">
              <Table2 className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-bold text-slate-900 tracking-tight">Manuscripts Process</h1>
              <p className="mt-1 text-slate-500 font-medium">统一表格视图管理稿件生命周期（只读监控）</p>
              <p className="mt-1 text-xs text-slate-400">点击稿件 ID 进入详情页执行操作。</p>
            </div>
          </div>
          <Link href="/dashboard" className={cn(buttonVariants({ variant: 'outline' }), 'gap-2')}>
            <ArrowLeft className="h-4 w-4" />
            返回编辑台
          </Link>
        </div>

        <Suspense
          fallback={
            <div className="rounded-xl border border-slate-200 bg-white p-10 text-sm text-slate-500">
              Loading…
            </div>
          }
        >
          <ManuscriptsProcessPanel viewMode="monitor" />
        </Suspense>
      </main>
    </div>
  )
}
