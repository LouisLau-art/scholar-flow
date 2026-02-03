'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { ArrowLeft, DollarSign, CheckCircle2, RotateCcw, FileText } from 'lucide-react'
import SiteHeader from '@/components/layout/SiteHeader'
import { Button, buttonVariants } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export default function FinanceDashboard() {
  /**
   * 财务管理后台
   * 遵循章程：slate-900 风格，原子化组件
   * 落实 Spec：支持确认到账与撤销回滚 (Edge Cases)
   */
  const [invoices, setInvoices] = useState([
    { id: 'inv-001', title: 'Deep Learning in Medicine', amount: 1500, status: 'unpaid' }
  ])

  const router = useRouter()

  const handleBack = () => {
    if (typeof window !== 'undefined' && window.history.length > 1) {
      router.back()
      return
    }
    router.push('/')
  }

  const handleConfirm = (id: string) => {
    setInvoices(invoices.map(inv => inv.id === id ? { ...inv, status: 'paid' } : inv))
  }

  const handleRollback = (id: string) => {
    // 落实 Spec: 财务误操作回滚
    setInvoices(invoices.map(inv => inv.id === id ? { ...inv, status: 'unpaid' } : inv))
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <SiteHeader />
      <div className="mx-auto max-w-5xl p-8">
        <header className="mb-10 border-b border-slate-200 pb-6">
          <div className="flex items-center justify-between gap-4">
            <button
              type="button"
              onClick={handleBack}
              className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }), 'gap-2')}
            >
              <ArrowLeft className="h-4 w-4" />
              返回
            </button>
            <div className="flex items-center gap-2">
              <Link
                href="/"
                className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}
              >
                首页
              </Link>
              <Link
                href="/dashboard"
                className={cn(buttonVariants({ variant: 'default', size: 'sm' }))}
              >
                Dashboard
              </Link>
            </div>
          </div>

          <div className="mt-6">
            <h1 className="flex items-center gap-3 font-serif text-3xl font-bold text-slate-900">
              <DollarSign className="h-8 w-8 text-blue-600" />
              Finance
            </h1>
            <p className="mt-2 text-slate-600">
              说明：MVP 的财务门禁与 <span className="font-medium text-slate-900">Mark Paid</span> 已合并到 Editor Pipeline 的 Approved 阶段；此页保留为演示与后续扩展入口。
            </p>
          </div>
        </header>

        <Card className="overflow-hidden border-slate-200">
          <CardHeader className="border-b border-slate-100">
            <CardTitle className="text-slate-900">Invoices</CardTitle>
            <CardDescription>
              当前为本地演示数据（不与云端 Supabase 同步）。
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-slate-900 text-white">
                  <tr>
                    <th className="px-6 py-4 text-sm font-semibold">Manuscript</th>
                    <th className="px-6 py-4 text-sm font-semibold">Amount</th>
                    <th className="px-6 py-4 text-sm font-semibold">Status</th>
                    <th className="px-6 py-4 text-right text-sm font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  {invoices.map((inv) => (
                    <tr key={inv.id} className="transition-colors hover:bg-slate-50">
                      <td className="px-6 py-4 font-medium text-slate-900">{inv.title}</td>
                      <td className="px-6 py-4 text-slate-600">${inv.amount}</td>
                      <td className="px-6 py-4">
                        <Badge
                          variant="outline"
                          className={cn(
                            'border-transparent',
                            inv.status === 'paid'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-yellow-100 text-yellow-700'
                          )}
                        >
                          {inv.status.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex justify-end gap-2">
                          {inv.status === 'unpaid' ? (
                            <Button
                              type="button"
                              size="sm"
                              className="bg-green-600 text-white hover:bg-green-700"
                              onClick={() => handleConfirm(inv.id)}
                            >
                              <CheckCircle2 className="h-4 w-4" />
                              Confirm
                            </Button>
                          ) : (
                            <Button
                              type="button"
                              size="sm"
                              variant="secondary"
                              onClick={() => handleRollback(inv.id)}
                            >
                              <RotateCcw className="h-4 w-4" />
                              Rollback
                            </Button>
                          )}

                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => window.alert('Invoice PDF is being generated...')}
                          >
                            <FileText className="h-4 w-4" />
                            View Invoice
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
