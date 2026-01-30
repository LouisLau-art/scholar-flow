'use client'

import { useState, useEffect } from 'react'
import { FileText, Send, Loader2 } from 'lucide-react'
import { ApiClient } from '@/lib/api-client'

export default function ReviewerPage({ params }: { params: { token: string } }) {
  /**
   * 审稿人免登录落地页
   * 遵循章程：衬线体标题，slate-900 风格，优雅降级
   */
  const [isLoading, setIsLoading] = useState(true)
  const [manuscript, setManuscript] = useState<any>(null)

  useEffect(() => {
    // 模拟根据 Token 获取稿件元数据
    const loadData = async () => {
      setIsLoading(false)
      // 实际逻辑应调用 ApiClient.getManuscriptByToken(params.token)
    }
    loadData()
  }, [params.token])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <Loader2 className="h-10 w-10 animate-spin text-slate-900" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-12 border-b border-slate-200 pb-6">
          <h1 className="font-serif text-4xl font-bold text-slate-900">
            Review Manuscript
          </h1>
          <p className="mt-2 text-slate-600">Secure, no-login access via token.</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* PDF 预览占位区域 (T023) */}
          <div className="lg:col-span-2 rounded-lg bg-white p-4 shadow-sm ring-1 ring-slate-200 h-[800px] flex items-center justify-center border-2 border-dashed border-slate-200">
            <div className="text-center">
              <FileText className="mx-auto h-12 w-12 text-slate-300" />
              <p className="mt-4 text-slate-500 font-medium">PDF Preview Component Loading...</p>
            </div>
          </div>

          {/* 评审表单 */}
          <aside className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-slate-200 h-fit">
            <h2 className="text-lg font-semibold text-slate-900 mb-6">Your Evaluation</h2>
            <form className="space-y-6">
              <div>
                <label className="block text-sm font-semibold text-slate-900">Score (1-5)</label>
                <select className="mt-1 w-full rounded-md border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-500">
                  <option value="5">5 - Excellent</option>
                  <option value="4">4 - Good</option>
                  <option value="3">3 - Average</option>
                  <option value="2">2 - Poor</option>
                  <option value="1">1 - Terrible</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-900">Review Comments</label>
                <textarea rows={10} className="mt-1 w-full rounded-md border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-500" />
              </div>

              <button className="w-full flex items-center justify-center gap-2 rounded-md bg-slate-900 py-3 text-white hover:bg-slate-800 transition-colors">
                <Send className="h-4 w-4" /> Submit Report
              </button>
            </form>
          </aside>
        </div>
      </div>
    </div>
  )
}
