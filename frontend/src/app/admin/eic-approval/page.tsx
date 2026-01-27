'use client'

import { useState } from 'react'
import { ShieldCheck, Globe, AlertTriangle } from 'lucide-react'

export default function EICApprovalPage() {
  /**
   * 主编 (Editor-in-Chief) 终审管理界面
   * 遵循章程：视觉锁定深蓝系，大标题衬线体
   */
  const [pendingItems, setPendingItems] = useState([
    { id: 'm-001', title: 'Advances in Quantum Computing', financeConfirmed: true }
  ])

  const handlePublish = (id: string) => {
    // 调用 ApiClient 进行最终发布 (T028 后端逻辑校验)
    console.log('Publishing manuscript', id)
    setPendingItems(pendingItems.filter(item => item.id !== id))
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-4xl">
        <header className="mb-12">
          <h1 className="font-serif text-4xl font-bold text-slate-900">Editor-in-Chief Approval</h1>
          <p className="mt-2 text-slate-600 text-lg font-medium">Final authority gate before publication.</p>
        </header>

        <div className="space-y-6">
          {pendingItems.map(item => (
            <div key={item.id} className="bg-white p-8 rounded-xl shadow-sm ring-1 ring-slate-200 flex items-center justify-between">
              <div className="flex gap-6 items-center">
                <div className="bg-blue-50 p-4 rounded-full">
                  <ShieldCheck className="h-8 w-8 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-slate-900">{item.title}</h3>
                  <div className="mt-2 flex items-center gap-4">
                    <span className="text-xs font-bold text-green-600 bg-green-50 px-2 py-1 rounded">PAYMENT CONFIRMED</span>
                    <span className="text-xs text-slate-400">ID: {item.id}</span>
                  </div>
                </div>
              </div>

              <button 
                onClick={() => handlePublish(item.id)}
                className="flex items-center gap-2 bg-slate-900 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-all shadow-lg hover:shadow-blue-500/20"
              >
                <Globe className="h-5 w-5" /> GO LIVE
              </button>
            </div>
          ))}

          {pendingItems.length === 0 && (
            <div className="text-center py-20 bg-white rounded-xl border-2 border-dashed border-slate-200 text-slate-400">
              <p className="text-lg">No manuscripts awaiting final approval.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
