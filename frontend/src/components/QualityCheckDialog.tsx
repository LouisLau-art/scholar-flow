'use client'

import { useState } from 'react'
import { Check, X, AlertCircle } from 'lucide-react'

interface QCProps {
  manuscriptId: string
  onClose: () => void
}

export default function QualityCheckDialog({ manuscriptId, onClose }: QCProps) {
  /**
   * 质检对话框组件
   * 遵循章程：Shadcn/UI 风格，配色锁定深蓝
   */
  const [passed, setPassed] = useState<boolean | null>(null)
  const [kpiOwner, setKpiOwner] = useState('')

  const handleSubmit = async () => {
    if (!kpiOwner) return alert('必须指定 KPI 归属人')
    
    // 调用 ApiClient 进行质检提交 (T010 已封装部分逻辑)
    console.log('Submitting QC for', manuscriptId, { passed, kpiOwner })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-2xl ring-1 ring-slate-200">
        <h2 className="font-serif text-2xl font-bold text-slate-900">Quality Check</h2>
        <p className="mt-2 text-slate-500 text-sm">Review the manuscript and assign responsibility.</p>

        <div className="mt-8 space-y-6">
          {/* 通过/拒绝按钮 */}
          <div className="flex gap-4">
            <button 
              onClick={() => setPassed(true)}
              className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-3 border-2 transition-all ${
                passed === true ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-slate-200 text-slate-500'
              }`}
            >
              <Check className="h-5 w-5" /> Pass
            </button>
            <button 
              onClick={() => setPassed(false)}
              className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-3 border-2 transition-all ${
                passed === false ? 'border-red-600 bg-red-50 text-red-700' : 'border-slate-200 text-slate-500'
              }`}
            >
              <X className="h-5 w-5" /> Reject
            </button>
          </div>

          {/* KPI 归属人选择 */}
          <div>
            <label className="block text-sm font-semibold text-slate-900">KPI Owner</label>
            <select 
              value={kpiOwner}
              onChange={(e) => setKpiOwner(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select an editor...</option>
              <option value="louis">Louis Lau</option>
              <option value="admin">System Admin</option>
            </select>
          </div>
        </div>

        <div className="mt-10 flex gap-3">
          <button onClick={onClose} className="flex-1 rounded-md py-2 text-slate-600 hover:bg-slate-100">Cancel</button>
          <button 
            onClick={handleSubmit}
            className="flex-1 rounded-md bg-slate-900 py-2 text-white hover:bg-slate-800 transition-opacity disabled:opacity-50"
            disabled={passed === null || !kpiOwner}
          >
            Submit Review
          </button>
        </div>
      </div>
    </div>
  )
}
